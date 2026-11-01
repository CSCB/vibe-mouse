"""
Vibe Mouse 主面板 / Main Panel (PyQt5)

GUI 模式的桌面主窗口，提供：
- 工具切换（含自动检测开关）
- 当前 Skill 状态与退出
- 切换历史记录（ToolSwitcher）

- 快捷键映射速查

替代原 tkinter 版 gui_client.py，统一技术栈到 PyQt5。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QCheckBox, QFrame, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .config import VibeTool
from .tool_switcher import SwitchReason

# 暗色主题（与 settings_ui 保持一致）
STYLE_BG = "#1e1e2e"
STYLE_SURFACE = "#313244"
STYLE_ACCENT = "#89b4fa"
STYLE_TEXT = "#cdd6f4"
STYLE_MUTED = "#6c7086"
STYLE_SUCCESS = "#a6e3a1"
STYLE_WARNING = "#f9e2af"


class ControlPanel(QWidget):
    """
    GUI 模式主面板。

    通过信号 tool_switch_requested / skill_exit_requested 通知外部（main.py）
    执行实际的切换逻辑（涉及 executor + detector 重置）。
    """

    tool_switch_requested = pyqtSignal(str)   # tool_name
    skill_exit_requested = pyqtSignal()
    auto_detect_toggled = pyqtSignal(bool)    # enabled

    def __init__(self, config, executor, window_detector=None, relay_controller=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.executor = executor
        self.window_detector = window_detector
        self.relay_controller = relay_controller

        self.setWindowTitle("Vibe Mouse 控制面板 / Control Panel")
        self.setStyleSheet(f"background-color: {STYLE_BG}; color: {STYLE_TEXT};")

        self._tool_btn_group = None
        self._skill_layout = None
        self._history_label = None

        self._build_ui()
        self.refresh()

        # 尺寸自适应内容（不同 DPI/字体缩放下工具名、文字都不被裁剪）
        try:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
        except Exception:
            screen = None
        # 宽度：以内容 sizeHint 为准（工具行 7 个单选按钮一行排开），限屏幕宽
        width = max(460, self.sizeHint().width())
        if screen is not None:
            width = min(width, screen.width() - 40)
        self.setFixedWidth(width)
        # 宽度定下后再取高度（自动换行的标签高度与宽度相关）
        height = max(self.sizeHint().height(), 600)
        if screen is not None:
            height = min(height, screen.height() - 60)
        self.setFixedHeight(height)

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 内容区（包进 QScrollArea：小屏/高 DPI 缩放下内容可滚动，不再被裁剪）
        content = QWidget()
        content.setStyleSheet(f"background-color: {STYLE_BG}; color: {STYLE_TEXT};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        # 标题
        title = QLabel("Vibe Mouse")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {STYLE_ACCENT};")
        lay.addWidget(title)

        # ---- 工具切换区 ----
        lay.addWidget(self._section_label("映射工具 / Mapped Tool"))

        tool_row = QHBoxLayout()
        self._tool_btn_group = QButtonGroup(self)
        self._tool_btn_group.setExclusive(True)
        self._tool_btn_group.buttonClicked.connect(self._on_tool_clicked)

        # QButtonGroup 的 id 必须是 int，这里建立 int<->tool_name 映射
        self._tool_id_map = {}  # int -> tool_name
        for idx, tool in enumerate(VibeTool):
            btn = QRadioButton(tool.value)
            btn.setStyleSheet(self._radio_style())
            self._tool_btn_group.addButton(btn, idx)
            self._tool_id_map[idx] = tool.value
            tool_row.addWidget(btn)

        tool_row.addStretch()
        lay.addLayout(tool_row)

        # 自动检测开关
        self._auto_detect_cb = QCheckBox("窗口焦点自动检测 / Auto-detect IDE")
        self._auto_detect_cb.setStyleSheet(f"color: {STYLE_TEXT};")
        self._auto_detect_cb.setChecked(self.config.auto_detect_ide)
        self._auto_detect_cb.toggled.connect(self._on_auto_detect_toggled)
        lay.addWidget(self._auto_detect_cb)

        # ---- 当前 Skill 区 ----
        lay.addWidget(self._section_label("当前 Skill / Active Skill"))
        self._skill_container = QFrame()
        self._skill_container.setStyleSheet(f"background-color: {STYLE_SURFACE}; border-radius: 6px;")
        self._skill_layout = QVBoxLayout(self._skill_container)
        self._skill_layout.setContentsMargins(12, 8, 12, 8)
        lay.addWidget(self._skill_container)

        # ---- 快捷键速查 ----
        lay.addWidget(self._section_label("快捷键映射 / Shortcuts"))
        self._shortcuts_grid = QGridLayout()
        self._shortcuts_grid.setSpacing(4)
        lay.addLayout(self._shortcuts_grid)

        # ---- 设备按键映射（鼠标侧键 / 翻页笔 / 手柄等）----
        lay.addWidget(self._section_label("设备按键映射 / Device Mapping"))
        self._device_grid = QGridLayout()
        self._device_grid.setSpacing(4)
        lay.addLayout(self._device_grid)

        # ---- BLE 继电器（折叠区块）----
        if self.relay_controller is not None:
            from .ble_relay_ui import RelayControlWidget
            self._relay_widget = RelayControlWidget(self.config, self.relay_controller, self.executor)
            lay.addWidget(self._relay_widget)

        # ---- 切换历史 ----
        lay.addWidget(self._section_label("切换历史 / History"))
        self._history_label = QLabel("暂无记录")
        self._history_label.setStyleSheet(
            f"background-color: {STYLE_SURFACE}; color: {STYLE_MUTED}; "
            "border-radius: 6px; padding: 10px;"
        )
        self._history_label.setWordWrap(True)
        self._history_label.setAlignment(Qt.AlignTop)
        lay.addWidget(self._history_label)

        lay.addStretch()

        # 刷新按钮
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新 / Refresh")
        refresh_btn.setStyleSheet(self._btn_style())
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        exit_skill_btn = QPushButton("退出 Skill / Exit Skill")
        exit_skill_btn.setStyleSheet(self._btn_style(accent=True))
        exit_skill_btn.clicked.connect(self.skill_exit_requested.emit)
        btn_row.addWidget(exit_skill_btn)
        lay.addLayout(btn_row)

        root.addWidget(content)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        lbl.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
        return lbl

    def _radio_style(self):
        return f"QRadioButton {{ color: {STYLE_TEXT}; spacing: 4px; }}"

    def _btn_style(self, accent=False):
        bg = STYLE_ACCENT if accent else STYLE_SURFACE
        fg = "#1e1e2e" if accent else STYLE_TEXT
        return (
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {STYLE_WARNING}; }}"
        )

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def _on_tool_clicked(self, button):
        btn_id = self._tool_btn_group.id(button)
        tool_name = self._tool_id_map.get(btn_id)
        if tool_name and tool_name != self.config.current_tool:
            self.tool_switch_requested.emit(tool_name)

    def _on_auto_detect_toggled(self, checked):
        self.config.auto_detect_ide = checked
        self.config.save_config()
        self.auto_detect_toggled.emit(checked)

    # ------------------------------------------------------------------
    # 刷新显示
    # ------------------------------------------------------------------
    def refresh(self):
        """刷新面板所有区块的内容"""
        # 工具选中状态
        for btn in self._tool_btn_group.buttons():
            btn.setChecked(self._tool_id_map.get(self._tool_btn_group.id(btn)) == self.config.current_tool)

        # 当前 Skill
        self._refresh_skill()

        # 快捷键映射
        self._refresh_shortcuts()

        # 设备按键映射
        self._refresh_device_mapping()

        # 切换历史
        self._refresh_history()

    def _refresh_skill(self):
        # 清空
        while self._skill_layout.count():
            item = self._skill_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        skill = self.executor.active_skill
        if skill:
            lbl = QLabel(f"● {skill.name}")
            lbl.setStyleSheet(f"color: {STYLE_SUCCESS}; font-weight: bold; font-size: 13px; border: none;")
            self._skill_layout.addWidget(lbl)

            # skill 列表（可启用的）
            if self.executor.skill_engine:
                avail = [s.name for s in self.executor.skill_engine.list_skills() if s.enabled]
                if avail:
                    hint = QLabel(f"可用: {', '.join(avail)}")
                    hint.setStyleSheet(f"color: {STYLE_MUTED}; font-size: 11px; border: none;")
                    self._skill_layout.addWidget(hint)
        else:
            lbl = QLabel("无激活 Skill / No active skill")
            lbl.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
            self._skill_layout.addWidget(lbl)

            if self.executor.skill_engine:
                avail = [s.name for s in self.executor.skill_engine.list_skills() if s.enabled]
                if avail:
                    hint = QLabel(f"可用: {', '.join(avail)}")
                    hint.setStyleSheet(f"color: {STYLE_ACCENT}; font-size: 11px; border: none;")
                    self._skill_layout.addWidget(hint)

    def _refresh_shortcuts(self):
        # 清空
        while self._shortcuts_grid.count():
            item = self._shortcuts_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        shortcuts = self.config.get_current_shortcuts()
        row = 0
        for action, keys in shortcuts.items():
            label = QLabel(action)
            label.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
            combo = QLabel(" + ".join(keys))
            combo.setStyleSheet(f"color: {STYLE_TEXT}; font-family: Consolas; border: none;")
            self._shortcuts_grid.addWidget(label, row, 0)
            self._shortcuts_grid.addWidget(combo, row, 1)
            row += 1

    def _refresh_device_mapping(self):
        """刷新设备按键映射：鼠标侧键 / 中键双击 / 翻页笔键盘 / 手柄等"""
        while self._device_grid.count():
            item = self._device_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        mouse_labels = {
            "left": "鼠标 左键 (Left)",
            "right": "鼠标 右键 (Right)",
            "middle": "鼠标 中键 (Middle)",
            "middle_double": "鼠标 中键双击 (Middle ×2)",
            "button6": "鼠标 侧键6 (button6)",
            "button7": "鼠标 侧键7 (button7)",
            "button8": "鼠标 侧键1 (Forward/button8)",
            "button9": "鼠标 侧键2 (Back/button9)",
        }

        rows = []

        # 鼠标映射
        mouse_mapping = self.config.device_mappings.get("mouse_default", {})
        for key, action in mouse_mapping.items():
            label = mouse_labels.get(key, f"鼠标 {key}")
            rows.append((label, action))

        # 键盘 / 翻页笔映射
        kb_mapping = getattr(self.config, "keyboard_mappings", {}) or {}
        for key, action in kb_mapping.items():
            rows.append((f"键盘/翻页笔 {key}", action))

        # 其他设备（手柄 / 蓝牙 / HID 等）
        for dev_id, mapping in self.config.device_mappings.items():
            if dev_id == "mouse_default":
                continue
            for key, action in mapping.items():
                rows.append((f"{dev_id} · {key}", action))

        if not rows:
            lbl = QLabel("未配置设备映射 / No device mapping")
            lbl.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
            self._device_grid.addWidget(lbl, 0, 0)
            return

        for r, (key_label, action) in enumerate(rows):
            k = QLabel(key_label)
            k.setStyleSheet(f"color: {STYLE_MUTED}; border: none;")
            a = QLabel(action)
            a.setStyleSheet(f"color: {STYLE_TEXT}; font-family: Consolas; border: none;")
            self._device_grid.addWidget(k, r, 0)
            self._device_grid.addWidget(a, r, 1)

    def _refresh_history(self):
        switcher = getattr(self.executor, "tool_switcher", None)
        if not switcher:
            self._history_label.setText("未启用切换记录器")
            return

        history = switcher.get_history_summary()
        if not history:
            self._history_label.setText("暂无记录 / No history")
            return

        lines = []
        for h in reversed(history[-8:]):
            arrow = f"{h['from']} → {h['to']}"
            tag = h.get("reason", "")
            t = h.get("time", "")
            lines.append(f"{t}  {arrow}  ({tag})")

        self._history_label.setText("\n".join(lines))
        self._history_label.setStyleSheet(
            f"background-color: {STYLE_SURFACE}; color: {STYLE_TEXT}; "
            "border-radius: 6px; padding: 10px; font-family: Consolas;"
        )
