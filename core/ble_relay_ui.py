"""
BLE 继电器控制面板组件 / BLE Relay Control Widget (PyQt5)

嵌入 ControlPanel 的折叠区块：
- 扫描 / 连接 / 断开（设备下拉列表）
- 3 通道 checkable 开关（点击统一走 executor.execute_action("relay:on_1")）
- 设备状态帧反向同步按钮 check 态；AT 回复（PIN PASS 等）显示

线程模型：controller 回调在 asyncio 线程触发，
统一经 pyqtSignal 跨线程 marshal 到 UI 主线程。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QToolButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .feedback import FeedbackTiming, RELAY_MODE_PRESETS

# 与 panel_ui 一致的暗色主题
STYLE_BG = "#1e1e2e"
STYLE_SURFACE = "#313244"
STYLE_ACCENT = "#89b4fa"
STYLE_TEXT = "#cdd6f4"
STYLE_MUTED = "#6c7086"
STYLE_SUCCESS = "#a6e3a1"
STYLE_WARNING = "#f9e2af"
STYLE_ERROR = "#f38ba8"


class RelayControlWidget(QWidget):
    """
    BLE 继电器控制区块（可折叠）。

    信号仅用于内部跨线程 marshal（controller 回调线程 → UI 线程）。
    """

    # 内部信号桥（asyncio 线程 emit → 主线程 slot）
    _scan_finished = pyqtSignal(list)        # [(name, address)]
    _connection_changed = pyqtSignal(str)     # 状态文本
    _status_updated = pyqtSignal(dict)        # {channel: bool}
    _raw_msg = pyqtSignal(str)                # AT 回复

    _TEST_MS = 5000                           # 模拟 coding 时长

    def __init__(self, config, relay_controller, executor=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.relay = relay_controller
        self.executor = executor

        self._devices = []          # [(name, address)]
        self._syncing_channels = False

        self._build_ui()

        # 接入 controller 回调（订阅列表 + 信号 marshal 到主线程）
        if self.relay is not None:
            self.relay.on_scan_result.append(lambda devs: self._scan_finished.emit(devs))
            self.relay.on_connection_change.append(lambda s: self._connection_changed.emit(s))
            self.relay.on_status_update.append(lambda d: self._status_updated.emit(d))
            self.relay.on_raw_msg.append(lambda m: self._raw_msg.emit(m))

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # ---- 折叠头 ----
        header_row = QHBoxLayout()
        self._toggle_btn = QToolButton()
        self._toggle_btn.setText("▸ BLE 继电器")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet(
            f"QToolButton {{ color: {STYLE_ACCENT}; border: none; "
            "font-weight: bold; font-size: 13px; }"
            f"QToolButton:hover {{ color: {STYLE_WARNING}; }}"
        )
        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._toggle_btn.clicked.connect(self._on_toggle_expanded)
        header_row.addWidget(self._toggle_btn)

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
        header_row.addWidget(self._status_dot)

        self._status_text = QLabel("未连接")
        self._status_text.setStyleSheet(f"color: {STYLE_MUTED}; border: none; font-size: 11px;")
        header_row.addWidget(self._status_text)
        header_row.addStretch()
        root.addLayout(header_row)

        # ---- 折叠体 ----
        self._body = QFrame()
        self._body.setStyleSheet(f"background-color: {STYLE_SURFACE}; border-radius: 6px;")
        body = QVBoxLayout(self._body)
        body.setContentsMargins(10, 8, 10, 8)
        body.setSpacing(6)

        # 行1：扫描 / 设备下拉 / 连接
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self._scan_btn = QPushButton("扫描")
        self._scan_btn.setStyleSheet(self._btn_style())
        self._scan_btn.setFixedWidth(56)
        self._scan_btn.clicked.connect(self._on_scan)
        row1.addWidget(self._scan_btn)

        self._device_combo = QComboBox()
        self._device_combo.setStyleSheet(
            f"QComboBox {{ background-color: {STYLE_BG}; color: {STYLE_TEXT}; "
            "border: none; border-radius: 6px; padding: 5px 8px; }"
        )
        self._device_combo.setMinimumWidth(150)
        row1.addWidget(self._device_combo, 1)

        self._connect_btn = QPushButton("连接")
        self._connect_btn.setStyleSheet(self._btn_style(accent=True))
        self._connect_btn.setFixedWidth(56)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        row1.addWidget(self._connect_btn)
        body.addLayout(row1)

        # 行2：通道开关
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self._channel_btns = {}
        for ch in range(1, int(self._relay_cfg().get("channels", 3)) + 1):
            btn = QPushButton(f"通道 {ch}")
            btn.setCheckable(True)
            btn.setStyleSheet(self._channel_style())
            btn.clicked.connect(lambda checked, c=ch: self._on_channel_clicked(c, checked))
            self._channel_btns[ch] = btn
            row2.addWidget(btn, 1)
        body.addLayout(row2)

        # 行2.5：通知模式选择（两灯 / 三灯预设）
        row_mode = QHBoxLayout()
        row_mode.setSpacing(6)
        mode_label = QLabel("通知模式")
        mode_label.setStyleSheet(f"color: {STYLE_MUTED}; border: none; font-size: 12px;")
        row_mode.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.setStyleSheet(
            f"QComboBox {{ background-color: {STYLE_BG}; color: {STYLE_TEXT}; "
            "border: none; border-radius: 6px; padding: 5px 8px; }"
        )
        for key, preset in RELAY_MODE_PRESETS.items():
            self._mode_combo.addItem(preset["label"], userData=key)
        # 恢复上次选中的模式（先设初始值再连信号，避免初始化误触发切换）
        stored_mode = self._feedback_relay_cfg().get("mode", "lights_2")
        idx = self._mode_combo.findData(stored_mode)
        self._mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row_mode.addWidget(self._mode_combo, 1)
        body.addLayout(row_mode)

        # 行3：模拟 AI 通知测试（提交 → coding 中 → 完成）
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        self._test_btn = QPushButton("模拟 AI 通知")
        self._test_btn.setStyleSheet(self._btn_style(accent=True))
        self._test_btn.setCursor(Qt.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test_notify)
        row3.addWidget(self._test_btn)

        self._test_label = QLabel("一键演练: 提交 → coding 中 → 完成通知")
        self._test_label.setStyleSheet(f"color: {STYLE_MUTED}; border: none; font-size: 11px;")
        row3.addWidget(self._test_label, 1)
        body.addLayout(row3)

        # 行4：设备回复
        self._msg_label = QLabel("")
        self._msg_label.setStyleSheet(f"color: {STYLE_MUTED}; border: none; font-size: 11px;")
        self._msg_label.setWordWrap(True)
        body.addWidget(self._msg_label)

        root.addWidget(self._body)

        # 内部信号 → 槽
        self._scan_finished.connect(self._on_scan_finished)
        self._connection_changed.connect(self._on_connection_changed)
        self._status_updated.connect(self._on_status_updated)
        self._raw_msg.connect(self._on_raw_msg)

        # 初始折叠态（记忆）
        expanded = bool(self._relay_cfg().get("ui_expanded", False))
        self._toggle_btn.setChecked(expanded)
        self._apply_expanded(expanded)

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def _relay_cfg(self):
        return getattr(self.config, "ble_relay", {}) or {}

    def _feedback_relay_cfg(self):
        """feedback.hardware.relay 动作表（Config 加载时已保证结构完整）"""
        feedback = getattr(self.config, "feedback", None) or {}
        return feedback.setdefault("hardware", {}).setdefault("relay", {})

    def _btn_style(self, accent=False):
        bg = STYLE_ACCENT if accent else STYLE_BG
        fg = "#1e1e2e" if accent else STYLE_TEXT
        return (
            f"QPushButton {{ background-color: {bg}; color: {fg}; border: none; "
            "border-radius: 6px; padding: 5px 8px; font-size: 12px; } "
            "QPushButton:hover { background-color: " + STYLE_WARNING + "; } "
            "QPushButton:disabled { color: " + STYLE_MUTED + "; }"
        )

    def _channel_style(self):
        return (
            f"QPushButton {{ background-color: {STYLE_BG}; color: {STYLE_TEXT}; "
            "border: none; border-radius: 6px; padding: 6px 4px; font-size: 12px; } "
            f"QPushButton:checked {{ background-color: {STYLE_SUCCESS}; color: {STYLE_BG}; "
            "font-weight: bold; } "
            f"QPushButton:hover {{ background-color: {STYLE_WARNING}; }}"
        )

    # ------------------------------------------------------------------
    # 事件处理（UI 线程）
    # ------------------------------------------------------------------
    def _on_toggle_expanded(self, checked):
        self._apply_expanded(checked)
        self._relay_cfg()["ui_expanded"] = checked
        try:
            self.config.save_config()
        except Exception:
            pass

    def _apply_expanded(self, expanded):
        self._body.setVisible(expanded)
        self._toggle_btn.setText("▾ BLE 继电器" if expanded else "▸ BLE 继电器")

    def _on_scan(self):
        if self.relay is None:
            return
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("扫描中")
        self.relay.scan()

    def _on_connect_clicked(self):
        if self.relay is None:
            return
        if self.relay.is_connected:
            self.relay.disconnect()
            return
        idx = self._device_combo.currentIndex()
        if idx < 0 or idx >= len(self._devices):
            self._msg_label.setText("请先扫描并选择设备")
            return
        _, address = self._devices[idx]
        self._connect_btn.setEnabled(False)
        self.relay.connect(address)

    def _on_channel_clicked(self, channel, checked):
        if self.relay is None or not self.relay.is_connected:
            # 未连接：回弹按钮状态
            btn = self._channel_btns.get(channel)
            if btn:
                btn.blockSignals(True)
                btn.setChecked(not checked)
                btn.blockSignals(False)
            self._msg_label.setText("继电器未连接")
            return
        # 统一走 executor 动作路径（与按键/语音一致）
        action = f"relay:{'on' if checked else 'off'}_{channel}"
        if self.executor is not None:
            self.executor.execute_action(action)
        else:
            self.relay.set_channel(channel, checked)

    def _on_mode_changed(self, index):
        """切换通知模式：整表应用预设动作 → 持久化 → 清灯（避免旧模式滞留状态）"""
        key = self._mode_combo.itemData(index)
        preset = RELAY_MODE_PRESETS.get(key)
        if not preset:
            return

        relay_cfg = self._feedback_relay_cfg()
        for event_key in ("on_submit", "on_done", "on_error"):
            relay_cfg[event_key] = dict(preset[event_key])
        relay_cfg["mode"] = key
        try:
            self.config.save_config()
        except Exception:
            pass

        # 全通道断电复位，清除上一模式可能遗留的亮灯状态
        if self.relay is not None and self.relay.is_connected:
            for ch in range(1, int(self._relay_cfg().get("channels", 3)) + 1):
                self.relay.set_channel(ch, False)

        self._test_label.setText(f"已切换: {preset['label']}")

    def _on_test_notify(self):
        """
        模拟一次完整的 AI 通知流程（不真正调用 IDE/模型）：

        点击 → 触发 on_submit 动作表（结果灯复位等）→ 按钮显示 "coding中..."
        → 3 秒后走真实完成管道 _notify_trae_done（蜂鸣 + 桌宠动画 + on_done 动作表）
        """
        if self.executor is None:
            self._test_label.setText("执行器不可用，无法模拟")
            return
        if self.relay is None or not self.relay.is_connected:
            self._test_label.setText("继电器未连接，无法测试硬件通知")
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("coding中...")
        self._test_label.setText(f"模拟 coding 中…{self._TEST_MS // 1000} 秒后触发完成通知")

        # 提交阶段：走真实反馈管道（on_submit 动作表 + 开始音频 niulai）
        self.executor.feedback.trigger_single(
            "relay", FeedbackTiming.ON_RECEIVED, "ai_submit")
        self.executor.feedback.trigger_single(
            "audio", FeedbackTiming.ON_RECEIVED, "ai_submit")

        QTimer.singleShot(self._TEST_MS, self._finish_test_notify)

    def _finish_test_notify(self):
        """模拟完成：蜂鸣 + 桌宠 done 动画 + on_done 动作表（通道1 常亮 / 通道2 闪烁）"""
        self._test_btn.setEnabled(True)
        self._test_btn.setText("模拟 AI 通知")
        if self.executor is not None:
            self.executor._notify_trae_done()
        self._test_label.setText("已完成: on_done 通知已触发（蜂鸣 + 继电器动作表）")

    # ------------------------------------------------------------------
    # controller 信号槽（UI 线程）
    # ------------------------------------------------------------------
    def _on_scan_finished(self, devices):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("扫描")
        self._devices = devices
        self._device_combo.clear()
        for name, address in devices:
            self._device_combo.addItem(f"{name}", userData=address)
        if not devices:
            self._msg_label.setText("未发现设备")

    def _on_connection_changed(self, text):
        self._status_text.setText(text)
        low = text.lower()
        if low.startswith("connected"):
            color = STYLE_SUCCESS
            self._connect_btn.setText("断开")
        elif low.startswith("disconnected") or low.startswith("connection failed"):
            color = STYLE_ERROR
            self._connect_btn.setText("连接")
        else:
            color = STYLE_WARNING  # Scanning / Connecting / Authenticating...
        self._status_dot.setStyleSheet(f"color: {color}; border: none;")
        self._connect_btn.setEnabled(True)

    def _on_status_updated(self, status):
        # 状态帧 START..@ → 反向同步通道按钮（clicked 信号不受 setChecked 影响）
        for ch, btn in self._channel_btns.items():
            if ch in status:
                btn.setChecked(bool(status[ch]))
        # 摘要：显示每个通道通断
        parts = [f"通道{ch}:{'开' if on else '关'}" for ch, on in sorted(status.items())]
        if parts:
            self._status_text.setText(" ".join(parts))

    def _on_raw_msg(self, msg):
        self._msg_label.setText(f"设备回复: {msg}")
