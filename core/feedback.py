"""
硬件反馈管理器 / Hardware Feedback Manager

当用户触发操作或任务完成时，通过多种方式给用户即时反馈：
- 软件反馈：系统声音、屏幕浮窗提示、系统托盘通知
- 硬件反馈：LED 指示灯、震动马达、蜂鸣器（需自定义硬件支持）

Software feedback works out of the box.
Hardware feedback requires registering external handlers (e.g., custom mouse LED via serial/HID).
"""

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


# 默认反馈配置：哪些时机触发哪些反馈
DEFAULT_FEEDBACK = {
    "on_received": ["sound", "overlay"],
    "on_success": ["sound"],
    "on_error": ["sound", "notification", "overlay"],
    "hardware": {
        "led_enabled": False,
        "vibration_enabled": False,
        "serial_port": None,
        "serial_baudrate": 9600,
    }
}


class FeedbackManager:
    """
    反馈管理器
    统一管理软件和硬件反馈的输出。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_FEEDBACK.copy()
        self._lock = threading.Lock()
        self._hardware_handlers: Dict[str, Callable] = {}
        self._overlay_active = False
        self._notification_handler: Optional[Callable] = None
        self._last_feedback_time = 0
        self._debounce_interval = 0.15  # 防抖间隔，避免连续触发

    def update_config(self, config: Dict[str, Any]):
        """动态更新反馈配置（Skill 激活/退出时调用）"""
        self.config = config

    # ------------------------------------------------------------------
    # 注册外部处理器
    # ------------------------------------------------------------------
    def register_hardware_handler(self, feedback_type: str, handler: Callable):
        """注册硬件反馈处理器（如自定义鼠标的串口LED控制）"""
        self._hardware_handlers[feedback_type] = handler

    def set_notification_handler(self, handler: Callable):
        """设置系统托盘通知处理器（由 system_tray 注入）"""
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

        enabled_types = self.config.get(timing.value, [])
        if not enabled_types:
            return

        display_msg = message or self._default_message(timing, action_name)

        for ft in enabled_types:
            handler = getattr(self, f"_do_{ft}", None)
            if handler:
                try:
                    handler(timing, action_name, display_msg)
                except Exception as e:
                    print(f"[Feedback] Error triggering {ft}: {e}")

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
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)   # 滴
                elif timing == FeedbackTiming.ON_SUCCESS:
                    winsound.MessageBeep(winsound.MB_OK)              # 叮
                elif timing == FeedbackTiming.ON_ERROR:
                    winsound.MessageBeep(winsound.MB_ICONHAND)        # 嘟
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

    def _do_overlay(self, timing: FeedbackTiming, action_name: str, message: str):
        """屏幕角落浮窗提示（使用 tkinter）"""
        try:
            self._show_tk_overlay(timing, message)
        except Exception as e:
            print(f"[Feedback] Overlay error: {e}")

    def _show_tk_overlay(self, timing: FeedbackTiming, message: str):
        """创建临时 tkinter 浮窗"""
        import tkinter as tk

        color_map = {
            FeedbackTiming.ON_RECEIVED: "#F59E0B",   # 黄
            FeedbackTiming.ON_SUCCESS: "#22C55E",    # 绿
            FeedbackTiming.ON_ERROR: "#EF4444",      # 红
        }
        bg_color = color_map.get(timing, "#333333")

        root = tk.Tk()
        root.overrideredirect(True)          # 无边框
        root.attributes("-topmost", True)    # 置顶
        root.attributes("-alpha", 0.92)      # 透明度

        # 屏幕右下角
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        w, h = 280, 60
        x = screen_w - w - 20
        y = screen_h - h - 60
        root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(root, bg=bg_color, padx=12, pady=8)
        frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            frame, text=message, bg=bg_color, fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="w", justify=tk.LEFT
        )
        label.pack(fill=tk.BOTH, expand=True)

        # 自动关闭
        def close():
            root.destroy()
        root.after(1200, close)

        # 线程中运行 tkinter
        threading.Thread(target=root.mainloop, daemon=True).start()

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

    # ------------------------------------------------------------------
    # 高级：LED 闪烁任务（用于持续状态指示）
    # ------------------------------------------------------------------
    def start_led_blink(self, color: str = "yellow", interval: float = 0.3):
        """启动 LED 持续闪烁（如等待用户确认时）"""
        handler = self._hardware_handlers.get("led")
        if not handler:
            return
        self._led_state = {"color": color, "blink": True, "interval": interval}
        # 实际闪烁由硬件端处理，这里仅记录状态
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
