"""
硬件反馈管理器 / Hardware Feedback Manager

当用户触发操作或任务完成时，通过多种方式给用户即时反馈：
- 软件反馈：系统声音、屏幕浮窗提示、系统托盘通知
- 硬件反馈：LED 指示灯、震动马达、蜂鸣器（需自定义硬件支持）

统一使用 PyQt5 作为 GUI 层（overlay 浮窗通过 Qt 信号槽跨线程渲染）。
"""

import os
import threading
import time
import platform
from enum import Enum
from typing import Dict, Callable, Optional, Any


class FeedbackType(Enum):
    """反馈类型"""
    LED = "led"                          # LED 指示灯
    VIBRATION = "vibration"              # 震动马达
    SOUND = "sound"                      # 系统声音
    NOTIFICATION = "notification"        # 系统托盘通知
    OVERLAY = "overlay"                  # 屏幕角落浮窗提示


class FeedbackTiming(Enum):
    """反馈时机"""
    ON_RECEIVED = "on_received"          # 收到输入时
    ON_SUCCESS = "on_success"            # 执行成功时
    ON_ERROR = "on_error"                # 执行失败时


# BLE 继电器通知模式预设：按接入灯的数量分档，面板下拉选择后整表覆盖动作表
# 动作含义: on=通电 / off=断电 / pulse=通电一段时长后断电 /
#           off_pulse=断电一段时长后复电（掉落）/ none=不动作
#
# 通道编排（123 固定语义，换模式不换接线）:
#   通道1 = 提交提示灯（三灯模式: 提交瞬间亮 1 秒灭；单灯/两灯模式作结果灯/工作灯）
#   通道2 = 工作灯（coding 中常亮，结束熄灭）
#   通道3 = 结果灯（完成常亮，下次提交熄灭）
RELAY_MODE_PRESETS = {
    "lights_1": {
        "label": "单灯模式（完成常亮）",
        # 通道1 接灯: 运行时不亮，完成常亮（下次提交复位），出错长闪
        "on_submit": {"1": "off", "2": "none", "3": "none"},
        "on_done": {"1": "on", "2": "none", "3": "none"},
        "on_error": {"1": "pulse", "2": "none", "3": "none"},
    },
    "lights_2": {
        "label": "两灯模式（工作灯 + 结果灯）",
        # 通道1=工作灯(提交亮) 通道2=结果灯(完成亮，提交时复位)
        "on_submit": {"1": "on", "2": "off", "3": "none"},
        "on_done": {"1": "off", "2": "on", "3": "none"},
        "on_error": {"1": "off", "2": "pulse", "3": "none"},
    },
    "lights_3": {
        "label": "三灯模式（提交提示 + 工作灯 + 结果灯）",
        # 通道1=提交提示灯(亮1秒灭) 通道2=工作灯(提交亮) 通道3=结果灯(完成亮，提交时复位)
        "on_submit": {"1": "pulse", "2": "on", "3": "off"},
        "on_done": {"1": "none", "2": "off", "3": "on"},
        "on_error": {"1": "none", "2": "off", "3": "pulse"},
    },
    "appliance": {
        "label": "电器模式（运行断电 · 结束通电）",
        # 非灯类外设：AI 运行期间通道断电，结束（完成/出错）通电
        # 通道1 接电器；出错时通电 1.5 秒以区分正常完成（常亮）
        "on_submit": {"1": "off", "2": "none", "3": "none"},
        "on_done": {"1": "on", "2": "none", "3": "none"},
        "on_error": {"1": "pulse", "2": "none", "3": "none"},
    },
    "drop": {
        "label": "掉落模式（运行通电 · 结束断电2秒复电）",
        # 通道1 接掉落装置（电磁铁等）：AI 运行全程通电，
        # 结束断电 2 秒（触发掉落）后自动恢复通电待命；
        # 出错时同样掉落复位
        "on_submit": {"1": "on", "2": "none", "3": "none"},
        "on_done": {"1": "off_pulse", "2": "none", "3": "none"},
        "on_error": {"1": "off_pulse", "2": "none", "3": "none"},
    },
}

# 默认继电器动作表 = 三灯模式预设（默认时长见下）
_DEFAULT_RELAY = dict(RELAY_MODE_PRESETS["lights_3"])
_DEFAULT_RELAY.update({
    "mode": "lights_3",        # 当前选中的模式（面板下拉记忆）
    "pulse_ms": 500,           # 通用 pulse 时长（on_done 等）
    "submit_pulse_ms": 1000,   # on_submit 的 pulse 时长（三灯模式提交提示灯亮 1 秒）
    "error_pulse_ms": 1500,    # on_error 的 pulse 时长（便于区分出错）
    "drop_gap_ms": 2000,       # off_pulse 的断电时长（掉落模式：断电 2 秒后复电）
})

# 默认反馈配置：哪些时机触发哪些反馈
DEFAULT_FEEDBACK = {
    "on_received": ["sound", "overlay"],
    "on_success": ["sound"],
    "on_error": ["sound", "notification", "overlay"],
    # 桌宠联动（威币猫动画）：工作/完成/动作/录音/Skill 状态动画开关
    "mascot": {
        "enabled": True,
    },
    "hardware": {
        "led_enabled": False,
        "vibration_enabled": False,
        "serial_port": None,
        "serial_baudrate": 9600,
        # BLE 继电器通知动作表：事件 × 通道 → 动作
        # 默认等于三灯模式预设；面板"通知模式"下拉按灯数量一键切换（单灯/两灯/三灯）
        "relay": _DEFAULT_RELAY,
    }
}

# 事件音频：AI 提交/完成时播放项目 music/ 目录下的音频文件
# （ai_submit → niulai 开始提示；ai_done → mama 结束提示）
# 每个事件按候选顺序取第一个存在的文件；本机 Qt/MCI 均无 AAC 解码器，
# 故用 ffmpeg 预转的 WAV 优先（WAV 为 PCM 无需解码，全平台必播）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(_PROJECT_ROOT, "music")
AUDIO_FILES = {
    "ai_submit": ("niulai.wav", "niulai.m4a"),
    "ai_done": ("mama.wav", "mama.m4a"),
}


def _make_audio_signals():
    """
    创建音频信号对象（延迟导入 PyQt5，避免无 GUI 环境报错）。
    QMediaPlayer 须在主线程使用，跨线程经信号槽 marshal。
    """
    from PyQt5.QtCore import QObject, pyqtSignal
    class _AudioSignals(QObject):
        play_file = pyqtSignal(str)  # 音频文件绝对路径
    return _AudioSignals()


def _make_overlay_signals():
    """
    创建 overlay 信号对象（延迟导入 PyQt5，避免无 GUI 环境报错）。
    信号用于跨线程安全地在主线程渲染浮窗。
    """
    from PyQt5.QtCore import QObject, pyqtSignal
    class _OverlaySignals(QObject):
        show_overlay = pyqtSignal(str, str, str)  # timing_value, action_name, message
    return _OverlaySignals()


class FeedbackManager:
    """
    反馈管理器
    统一管理软件和硬件反馈的输出。

    线程安全设计：
    - overlay 浮窗通过 PyQt5 信号槽跨线程渲染（QueuedConnection），
      无论哪个线程调用 trigger，浮窗都在 QApplication 主线程创建。
    - 首次调用 overlay 时延迟导入 PyQt5 并连接信号。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_FEEDBACK.copy()
        self._lock = threading.Lock()
        self._hardware_handlers: Dict[str, Callable] = {}
        self._overlay_active = False
        self._notification_handler: Optional[Callable] = None
        self._last_feedback_time = 0
        self._debounce_interval = 0.15  # 防抖间隔，避免连续触发

        # Overlay 系统（PyQt5 信号槽）
        self._overlay_signals = None    # 延迟初始化
        self._current_overlay = None    # 当前显示的浮窗 QWidget
        self._overlay_lock = threading.Lock()
        self._qt_app_ref = None         # QApplication 引用（防止 GC）

        # 事件音频（niulai/mama，QMediaPlayer 主线程播放）
        self._audio_signals = None      # 延迟初始化
        self._audio_players = {}        # {文件路径: QMediaPlayer}（主线程创建，防 GC）

    def update_config(self, config: Dict[str, Any]):
        """动态更新反馈配置（Skill 激活/退出时调用）"""
        self.config = config

    def set_qt_app(self, app):
        """
        注册 QApplication 引用，并初始化 overlay 信号连接。
        必须在 QApplication 创建后（主线程）调用一次。
        """
        self._qt_app_ref = app
        if self._overlay_signals is None:
            self._overlay_signals = _make_overlay_signals()
            self._overlay_signals.show_overlay.connect(self._on_show_overlay)

    # ------------------------------------------------------------------
    # 注册外部处理器
    # ------------------------------------------------------------------
    def register_hardware_handler(self, feedback_type: str, handler: Callable):
        """注册硬件反馈处理器（如自定义鼠标的串口LED控制）"""
        self._hardware_handlers[feedback_type] = handler

    def set_notification_handler(self, handler: Callable):
        """设置系统托盘通知处理器（由 system_tray / pet_ui 注入）"""
        self._notification_handler = handler

    # ------------------------------------------------------------------
    # 主入口：触发反馈
    # ------------------------------------------------------------------
    def trigger(self, timing: FeedbackTiming, action_name: str = None, message: str = None):
        """
        根据配置触发对应时机的反馈

        Args:
            timing: FeedbackTiming 枚举值
            action_name: 触发的动作名称（可选）
            message: 自定义提示消息（可选）
        """
        now = time.time()
        if now - self._last_feedback_time < self._debounce_interval:
            return
        self._last_feedback_time = now

        display_msg = message or self._default_message(timing, action_name)

        for ft in self.config.get(timing.value, []):
            if ft == "relay":
                # relay 不走时机列表：动作表由下方 _do_relay 统一触发。
                # 旧配置可能残留 "relay" 条目，跳过避免同一动作表执行两次
                # （重复帧还会挤占 BLE 帧间隔，加大丢帧概率）
                continue
            handler = getattr(self, f"_do_{ft}", None)
            if handler:
                try:
                    handler(timing, action_name, display_msg)
                except Exception as e:
                    print(f"[Feedback] Error triggering {ft}: {e}")

        # 继电器通知不走时机列表：由 relay 动作表独立控制
        # （on_done/on_error/on_submit 各通道动作，全 none 即等效禁用；
        #   即使时机列表为空也照常触发）
        self._do_relay(timing, action_name, display_msg)

    def trigger_single(self, feedback_type: str, timing: FeedbackTiming,
                       action_name: str = None, message: str = None):
        """
        只触发单一反馈类型（不走时机列表、不受防抖限制）。

        用于状态类硬件反馈，例如 relay 常亮模式下
        "AI 开始工作=关灯"（由 main.py 的检测回调定向调用）。
        """
        handler = getattr(self, f"_do_{feedback_type}", None)
        if not handler:
            return
        display_msg = message or self._default_message(timing, action_name)
        try:
            handler(timing, action_name, display_msg)
        except Exception as e:
            print(f"[Feedback] Error triggering {feedback_type}: {e}")

    def _default_message(self, timing: FeedbackTiming, action_name: str) -> str:
        if timing == FeedbackTiming.ON_RECEIVED:
            return f"执行: {action_name}" if action_name else "收到输入"
        elif timing == FeedbackTiming.ON_SUCCESS:
            return f"完成: {action_name}" if action_name else "执行完成"
        elif timing == FeedbackTiming.ON_ERROR:
            return f"失败: {action_name}" if action_name else "执行失败"
        return ""

    # ------------------------------------------------------------------
    # 软件反馈实现
    # ------------------------------------------------------------------
    def _do_sound(self, timing: FeedbackTiming, action_name: str, message: str):
        """播放系统声音"""
        system = platform.system()
        if system == "Windows":
            try:
                import winsound
                if timing == FeedbackTiming.ON_RECEIVED:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif timing == FeedbackTiming.ON_SUCCESS:
                    winsound.MessageBeep(winsound.MB_OK)
                elif timing == FeedbackTiming.ON_ERROR:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass
        elif system == "Darwin":  # macOS
            try:
                import os
                if timing == FeedbackTiming.ON_ERROR:
                    os.system("afplay /System/Library/Sounds/Basso.aiff &")
                else:
                    os.system("afplay /System/Library/Sounds/Glass.aiff &")
            except Exception:
                pass
        else:  # Linux
            try:
                import os
                os.system("paplay /usr/share/sounds/freedesktop/stereo/message.oga &")
            except Exception:
                pass

    def _do_notification(self, timing: FeedbackTiming, action_name: str, message: str):
        """系统托盘通知"""
        if self._notification_handler:
            try:
                self._notification_handler(message)
            except Exception as e:
                print(f"[Feedback] Notification error: {e}")

    def _do_audio(self, timing: FeedbackTiming, action_name: str, message: str):
        """
        事件音频：按 action_name 播放 music/ 下的音频文件。
        ai_submit → niulai（开始） / ai_done → mama（结束）。

        QMediaPlayer 须在主线程使用，经信号槽 marshal（与 overlay 同模式）。
        """
        candidates = AUDIO_FILES.get(action_name or "")
        if not candidates:
            return  # 非音频事件（如按钮动作）不播放
        path = None
        for filename in candidates:
            p = os.path.join(AUDIO_DIR, filename)
            if os.path.exists(p):
                path = p
                break
        if path is None:
            print(f"[Feedback] 音频不存在，跳过: {candidates}")
            return
        try:
            if self._audio_signals is None:
                self._init_audio_if_ready()
            if self._audio_signals is not None:
                self._audio_signals.play_file.emit(path)
        except Exception as e:
            print(f"[Feedback] Audio error: {e}")

    def _init_audio_if_ready(self):
        """当 QApplication 已存在时初始化音频信号"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                self._audio_signals = _make_audio_signals()
                self._audio_signals.play_file.connect(self._on_play_file)
        except Exception:
            pass  # 无 PyQt5 环境时静默跳过

    def _on_play_file(self, path):
        """槽：主线程用 QMediaPlayer 播放（复用实例，防 GC）"""
        try:
            from PyQt5.QtCore import QUrl
            from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
            player = self._audio_players.get(path)
            if player is None:
                player = QMediaPlayer()
                self._audio_players[path] = player
            player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            player.play()
        except Exception as e:
            print(f"[Feedback] QMediaPlayer error: {e}")

    def _do_overlay(self, timing: FeedbackTiming, action_name: str, message: str):
        """
        屏幕角落浮窗提示（PyQt5 实现）。

        通过信号槽跨线程调度到主线程渲染，无需额外线程或 Tk 实例。
        """
        try:
            if self._overlay_signals is None:
                # 尝试延迟初始化（仅当 QApplication 已存在时）
                self._init_overlay_if_ready()
            if self._overlay_signals is not None:
                # 发射信号 → 主线程槽函数渲染（线程安全）
                self._overlay_signals.show_overlay.emit(
                    timing.value, action_name or "", message
                )
        except Exception as e:
            print(f"[Feedback] Overlay error: {e}")

    def _init_overlay_if_ready(self):
        """当 QApplication 已存在时初始化 overlay 信号"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                self.set_qt_app(app)
        except Exception:
            pass  # 无 PyQt5 环境时静默跳过

    # ------------------------------------------------------------------
    # Overlay 渲染（在 QApplication 主线程执行）
    # ------------------------------------------------------------------
    def _on_show_overlay(self, timing_str: str, action_name: str, message: str):
        """槽函数：在主线程创建 QWidget 浮窗（由信号触发）"""
        from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont

        # 关闭上一个浮窗
        with self._overlay_lock:
            if self._current_overlay is not None:
                try:
                    self._current_overlay.close()
                    self._current_overlay.deleteLater()
                except Exception:
                    pass
                self._current_overlay = None

        color_map = {
            FeedbackTiming.ON_RECEIVED.value: "#F59E0B",   # 黄
            FeedbackTiming.ON_SUCCESS.value: "#22C55E",    # 绿
            FeedbackTiming.ON_ERROR.value: "#EF4444",      # 红
        }
        bg_color = color_map.get(timing_str, "#333333")

        win = QWidget()
        win.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        win.setAttribute(Qt.WA_TranslucentBackground, False)
        win.setStyleSheet(f"background-color: {bg_color}; border-radius: 8px;")

        layout = QVBoxLayout(win)
        label = QLabel(message)
        label.setStyleSheet("color: white;")
        label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(label)
        layout.setContentsMargins(16, 10, 16, 10)

        # 固定宽度，根据内容调整高度
        win.setFixedWidth(280)
        win.adjustSize()

        # 屏幕右下角定位
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        w, h = win.width(), win.height()
        x = screen.width() - w - 20
        y = screen.height() - h - 60
        win.move(x, y)
        win.show()

        with self._overlay_lock:
            self._current_overlay = win

        # 1.2 秒后自动关闭
        def _close():
            with self._overlay_lock:
                if self._current_overlay is win:
                    self._current_overlay = None
            try:
                win.close()
                win.deleteLater()
            except Exception:
                pass

        QTimer.singleShot(1200, _close)

    # ------------------------------------------------------------------
    # 硬件反馈接口（调用注册的外部处理器）
    # ------------------------------------------------------------------
    def _do_led(self, timing: FeedbackTiming, action_name: str, message: str):
        """LED 指示灯控制"""
        handler = self._hardware_handlers.get("led")
        if not handler:
            return

        color_map = {
            FeedbackTiming.ON_RECEIVED: ("yellow", True),   # 黄色闪烁
            FeedbackTiming.ON_SUCCESS: ("green", False),    # 绿色常亮
            FeedbackTiming.ON_ERROR: ("red", True),         # 红色闪烁
        }
        color, blink = color_map.get(timing, ("white", False))
        try:
            handler(color=color, blink=blink)
        except Exception as e:
            print(f"[Feedback] LED error: {e}")

    def _do_vibration(self, timing: FeedbackTiming, action_name: str, message: str):
        """震动马达控制"""
        handler = self._hardware_handlers.get("vibration")
        if not handler:
            return

        duration_map = {
            FeedbackTiming.ON_RECEIVED: 0.08,
            FeedbackTiming.ON_SUCCESS: 0.2,
            FeedbackTiming.ON_ERROR: 0.4,
        }
        duration = duration_map.get(timing, 0.1)
        try:
            handler(duration=duration)
        except Exception as e:
            print(f"[Feedback] Vibration error: {e}")

    def _do_relay(self, timing: FeedbackTiming, action_name: str, message: str):
        """
        BLE 继电器通知（事件 × 通道动作表）。

        配置形如 feedback.hardware.relay：
            on_submit / on_done / on_error 各自带 {通道号: "on"/"off"/"pulse"/"none"}
        事件发生时逐通道执行动作；全为 none 时等效于禁用。

        handler 由 main.py 注册，签名 (channel, duration_ms, action)，
        action ∈ "pulse" / "on" / "off"。
        """
        handler = self._hardware_handlers.get("relay")
        if not handler:
            return

        relay_cfg = (self.config.get("hardware") or {}).get("relay") or {}

        # 事件 → 动作表。ON_SUCCESS 仅在 AI 完成时触发继电器
        # （switch_tool / Skill 激活等一般性成功不算，避免灯乱亮）
        if timing == FeedbackTiming.ON_SUCCESS:
            if action_name != "ai_done":
                return
            event_key = "on_done"
        elif timing == FeedbackTiming.ON_ERROR:
            event_key = "on_error"
        else:
            event_key = "on_submit"

        actions = relay_cfg.get(event_key) or {}
        if not actions:
            return

        pulse_ms = int(relay_cfg.get("pulse_ms", 500))
        submit_pulse_ms = int(relay_cfg.get("submit_pulse_ms", 1000))
        error_pulse_ms = int(relay_cfg.get("error_pulse_ms", 1500))
        drop_gap_ms = int(relay_cfg.get("drop_gap_ms", 2000))
        if timing == FeedbackTiming.ON_ERROR:
            duration = error_pulse_ms
        elif timing == FeedbackTiming.ON_RECEIVED:
            duration = submit_pulse_ms  # 三灯模式提交提示灯亮 1 秒
        else:
            duration = pulse_ms

        for ch, act in actions.items():
            act = str(act or "none").strip().lower()
            if act in ("none", ""):
                continue  # 该格子不动作
            if act not in ("on", "off", "pulse", "off_pulse"):
                continue
            # off_pulse（掉落）固定用断电时长，其余按时机取时长
            act_duration = drop_gap_ms if act == "off_pulse" else duration
            try:
                print(f"[Feedback] Relay: 通道{ch} {act} ({act_duration}ms)")
                handler(int(ch), act_duration, act)
            except Exception as e:
                print(f"[Feedback] Relay 通道{ch} error: {e}")

    # ------------------------------------------------------------------
    # 高级：LED 闪烁任务（用于持续状态指示）
    # ------------------------------------------------------------------
    def start_led_blink(self, color: str = "yellow", interval: float = 0.3):
        """启动 LED 持续闪烁（如等待用户确认时）"""
        handler = self._hardware_handlers.get("led")
        if not handler:
            return
        self._led_state = {"color": color, "blink": True, "interval": interval}
        try:
            handler(color=color, blink=True, interval=interval)
        except Exception:
            pass

    def stop_led_blink(self, color: str = "off"):
        """停止 LED 闪烁"""
        handler = self._hardware_handlers.get("led")
        if not handler:
            return
        self._led_state = {"color": color, "blink": False}
        try:
            handler(color=color, blink=False)
        except Exception:
            pass
