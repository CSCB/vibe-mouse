from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QGroupBox, QFormLayout, 
                             QTabWidget, QWidget, QLineEdit, QCheckBox,
                             QListWidget, QMessageBox, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class SettingsDialog(QDialog):
    # 设备按键可绑定的动作选项 (显示名, action_id)
    ACTION_OPTIONS = [
        ("inline_edit", "AI 内联生成 (Inline Edit)"),
        ("toggle_chat", "唤醒 AI 聊天 (Toggle Chat)"),
        ("accept_diff", "接受生成代码 (Accept Diff)"),
        ("reject_diff", "拒绝生成代码 (Reject Diff)"),
        ("voice_input", "语音输入 (Voice Input)"),
        ("submit_chat", "发送/提交 (Submit Chat)"),
        ("relay:on_1", "继电器 通道1 开"),
        ("relay:off_1", "继电器 通道1 关"),
        ("relay:toggle_1", "继电器 通道1 切换"),
        ("relay:on_2", "继电器 通道2 开"),
        ("relay:off_2", "继电器 通道2 关"),
        ("relay:toggle_2", "继电器 通道2 切换"),
        ("relay:on_3", "继电器 通道3 开"),
        ("relay:off_3", "继电器 通道3 关"),
        ("relay:toggle_3", "继电器 通道3 切换"),
    ]

    # 八类设备类型元数据：图标 / 名称 / 可配置参数 (key, label, default)
    DEVICE_TYPE_META = {
        "mouse": {"icon": "🖱️", "name": "鼠标", "params": []},
        "keyboard": {"icon": "⌨️", "name": "键盘", "params": [
            {"key": "watched_keys", "label": "监听按键(逗号分隔)", "default": ""},
        ]},
        "gamepad": {"icon": "🎮", "name": "手柄", "params": [
            {"key": "joystick_index", "label": "手柄序号", "default": "0"},
            {"key": "deadzone", "label": "死区", "default": "0.15"},
        ]},
        "bluetooth": {"icon": "🦷", "name": "蓝牙", "params": [
            {"key": "mac_address", "label": "MAC 地址", "default": ""},
            {"key": "mode", "label": "模式(ble/classic)", "default": "ble"},
        ]},
        "ir_remote": {"icon": "📡", "name": "红外遥控", "params": [
            {"key": "mode", "label": "模式(serial/broadlink/lirc)", "default": "serial"},
            {"key": "port", "label": "串口", "default": "COM3"},
            {"key": "baudrate", "label": "波特率", "default": "9600"},
        ]},
        "hid_generic": {"icon": "🔌", "name": "通用 HID", "params": [
            {"key": "vendor_id", "label": "厂商ID", "default": ""},
            {"key": "product_id", "label": "产品ID", "default": ""},
        ]},
        "network": {"icon": "🌐", "name": "网络/IoT", "params": [
            {"key": "protocol", "label": "协议(mqtt/websocket/http)", "default": "mqtt"},
            {"key": "broker", "label": "服务器", "default": "localhost"},
            {"key": "port", "label": "端口", "default": "1883"},
            {"key": "topic", "label": "主题", "default": "vibemouse/input"},
        ]},
        "voice": {"icon": "🎤", "name": "语音", "params": [
            {"key": "mode", "label": "模式(command)", "default": "command"},
            {"key": "language", "label": "语言", "default": "zh-CN"},
            {"key": "use_llm", "label": "使用LLM(true/false)", "default": "false"},
        ]},
    }

    # 手柄可映射按键（input_id -> 显示名），在手柄配置里编辑
    GAMEPAD_KEYS = ["a", "b", "x", "y", "lb", "rb", "back", "start",
                    "up", "down", "left", "right", "lt", "rt"]
    GAMEPAD_KEY_LABELS = {
        "a": "A 键", "b": "B 键", "x": "X 键", "y": "Y 键",
        "lb": "左肩键 (LB)", "rb": "右肩键 (RB)",
        "back": "Back 键", "start": "Start 键",
        "up": "方向键 上", "down": "方向键 下",
        "left": "方向键 左", "right": "方向键 右",
        "lt": "左扳机 (LT)", "rt": "右扳机 (RT)",
    }

    def __init__(self, config, pet_ui):
        super().__init__()
        self.config = config
        self.pet_ui = pet_ui
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Vibe Core Control Center / 核心控制中枢")
        self.resize(900, 440)
        
        # 炫酷的暗黑主题风格，包含 TabWidget 的样式
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                border-radius: 6px;
                background-color: #1e1e2e;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #a6adc8;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #11111b;
            }
            QTabBar::tab:hover:!selected {
                background-color: #45475a;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 15px;
                color: #89b4fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton:pressed { background-color: #74c7ec; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border-radius: 4px;
                border: 1px solid #45475a;
                background-color: #313244;
            }
            QCheckBox::indicator:checked { background-color: #89b4fa; }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(18, 6, 18, 12)

        # Windows 深色标题栏，去掉顶部浅色标题栏（白边）
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20,  # DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 20H1+ / Win11)
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass
        
        # 标题栏
        header_layout = QHBoxLayout()
        title_label = QLabel("Vibe Core Command Center")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #89b4fa; padding-bottom: 10px;")
        header_layout.addWidget(title_label)
        
        mode_label = QLabel("Current Mode: [ Vibe Coding ]")
        mode_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        header_layout.addStretch()
        header_layout.addWidget(mode_label)
        
        main_layout.addLayout(header_layout)

        # 自然语言配置（AI）：用一句话让大模型理解并修改配置
        nl_layout = QHBoxLayout()
        nl_layout.setSpacing(8)
        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("用自然语言配置，如：把鼠标上侧键设为语音输入、启用 LED 反馈")
        self.nl_input.returnPressed.connect(self.on_nl_config)
        nl_btn = QPushButton("AI 配置")
        nl_btn.clicked.connect(self.on_nl_config)
        nl_layout.addWidget(self.nl_input, 1)
        nl_layout.addWidget(nl_btn)
        main_layout.addLayout(nl_layout)

        self.nl_label = QLabel("")
        self.nl_label.setWordWrap(True)
        self.nl_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        main_layout.addWidget(self.nl_label)

        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 标签1：Vibe Coding 输入
        self.tab_coding = self.create_coding_tab()
        self.tabs.addTab(self.tab_coding, "💻 Vibe Coding 输入")

        # 标签2：输出 / 反馈
        self.tab_feedback = self.create_feedback_tab()
        self.tabs.addTab(self.tab_feedback, "📤 输出 / 反馈")

        # 标签3：三方伙伴组件配置（含机器人执行器）
        self.tab_partner = self.create_partner_tab()
        self.tabs.addTab(self.tab_partner, "🤝 Third-Party")

        main_layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply / 应用设置")
        apply_btn.clicked.connect(self.save_settings)
        close_btn = QPushButton("Close / 关闭")
        close_btn.setStyleSheet("background-color: #45475a; color: #cdd6f4;")
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(apply_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def create_coding_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # --- 核心设置组：目标编辑器 ---
        settings_group = QGroupBox("IDE Binding / 目标编辑器绑定")
        form_layout = QFormLayout()
        
        # 自动检测 IDE
        self.auto_detect_cb = QCheckBox("自动根据前台窗口切换工具 (Auto-Detect IDE)")
        self.auto_detect_cb.setChecked(self.config.auto_detect_ide)
        self.auto_detect_cb.stateChanged.connect(self.on_auto_detect_changed)
        form_layout.addRow("", self.auto_detect_cb)

        self.tool_combo = QComboBox()
        from core.config import VibeTool
        for tool in VibeTool:
            self.tool_combo.addItem(tool.value.capitalize(), tool.value)
        
        current_index = self.tool_combo.findData(self.config.current_tool)
        if current_index >= 0:
            self.tool_combo.setCurrentIndex(current_index)
            
        self.tool_combo.currentIndexChanged.connect(self.on_tool_changed)
        self.tool_combo.setDisabled(self.config.auto_detect_ide)
        form_layout.addRow(QLabel("Target IDE:"), self.tool_combo)
        
        # 动态显示当前 IDE 的真实快捷键
        self.shortcut_label = QLabel()
        self.shortcut_label.setStyleSheet("color: #a6adc8; font-size: 12px; margin-top: 5px;")
        if self.config.auto_detect_ide:
            self.shortcut_label.setText("当前 IDE 实际快捷键：\n(将根据前台窗口自动匹配)")
        else:
            self.update_shortcut_display(self.config.current_tool)
        form_layout.addRow("", self.shortcut_label)
        
        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)
        
        # --- 设备按键映射组（鼠标 / 手柄 / 翻页笔等所有设备）---
        mapping_group = QGroupBox("Device Mapping / 设备按键映射")
        mapping_layout = QVBoxLayout()
        mapping_layout.setSpacing(8)

        self.device_mapping_combos = {}  # {device_id: {key: combo}}

        for device_id, mapping in self.config.device_mappings.items():
            if device_id != "mouse_default":
                continue  # 其他设备（手柄等）在其专属配置里编辑映射
            dev_group = QGroupBox(self._device_label(device_id))
            dev_form = QFormLayout()

            keys = self._device_keys(device_id, mapping)
            combos = {}
            for key in keys:
                combo = QComboBox()
                combo.addItem("（未映射）", "")
                for action_id, action_name in self.ACTION_OPTIONS:
                    combo.addItem(action_name, action_id)
                current = mapping.get(key, "")
                idx = combo.findData(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                combos[key] = combo
                dev_form.addRow(QLabel(self._key_label(device_id, key) + ":"), combo)

            self.device_mapping_combos[device_id] = combos
            dev_group.setLayout(dev_form)
            mapping_layout.addWidget(dev_group)

        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)
        
        # --- 设备类型图标（点击进入对应设备设置）---
        device_group = QGroupBox("Device Types / 设备类型（点击进入设置）")
        device_grid = QGridLayout()
        device_grid.setSpacing(8)

        for idx, (dtype, meta) in enumerate(self.DEVICE_TYPE_META.items()):
            btn = QPushButton(f"{meta['icon']} {meta['name']}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=dtype: self.open_device_settings(t))
            device_grid.addWidget(btn, idx // 4, idx % 4)

        device_group.setLayout(device_grid)
        layout.addWidget(device_group)

        # --- AI 大模型桥接配置（主页）---
        llm_group = QGroupBox("LLM Bridge / 大模型桥接配置")
        llm_form = QFormLayout()

        from .token_plan import MODEL_PRESETS

        self.llm_enabled_cb = QCheckBox("启用大模型桥接（关闭时语音仅转文字直接粘贴）")
        self.llm_enabled_cb.setChecked(bool(self.config.token_plan.get("enabled", False)))
        llm_form.addRow("", self.llm_enabled_cb)

        self.llm_api_key_input = QLineEdit()
        self.llm_api_key_input.setEchoMode(QLineEdit.Password)
        self.llm_api_key_input.setPlaceholderText("华为云 MaaS API Key")
        self.llm_api_key_input.setText(self.config.token_plan.get("api_key", ""))
        llm_form.addRow("API Key:", self.llm_api_key_input)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.NoInsert)
        for preset in MODEL_PRESETS:
            self.model_combo.addItem(preset["name"], preset)

        current_model = self.config.token_plan.get("model", "")
        idx = -1
        for i in range(self.model_combo.count()):
            data = self.model_combo.itemData(i)
            if data and data.get("model") == current_model:
                idx = i
                break
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setEditText(current_model)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        llm_form.addRow("模型 (Model):", self.model_combo)

        self.endpoint_input = QLineEdit()
        self.endpoint_input.setText(self.config.token_plan.get("endpoint", ""))
        llm_form.addRow("Endpoint:", self.endpoint_input)

        self.refine_cb = QCheckBox("使用 LLM 优化语音文本（Prompt Refine：纠错 + 润色）")
        self.refine_cb.setChecked(bool(self.config.token_plan.get("refine_voice_text", False)))
        llm_form.addRow("", self.refine_cb)

        hint = QLabel("提示：关闭「LLM 优化」时，语音识别文本将直接作为输入，不再经过大模型纠错。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6c7086; font-size: 12px;")
        llm_form.addRow("", hint)

        llm_group.setLayout(llm_form)
        layout.addWidget(llm_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _device_label(self, device_id):
        """设备 ID -> 显示名"""
        labels = {
            "mouse_default": "鼠标 (Mouse)",
            "xbox": "手柄 (Xbox)",
            "xbox_controller": "手柄 (Xbox)",
        }
        return labels.get(device_id, device_id)

    def _device_keys(self, device_id, mapping):
        """确定某设备需要展示的按键列表（鼠标固定常用键 + 已有自定义键）"""
        if device_id == "mouse_default":
            fixed = ["button8", "button9", "middle", "middle_double"]
            for k in mapping:
                if k not in fixed:
                    fixed.append(k)
            return fixed
        return list(mapping.keys())

    def _key_label(self, device_id, key):
        """按键 ID -> 显示名（鼠标按键友好名，其他设备原样）"""
        if device_id == "mouse_default":
            labels = {
                "button8": "上侧键 (前进/button8)",
                "button9": "下侧键 (后退/button9)",
                "middle": "中键 (Middle)",
                "middle_double": "中键双击 (Middle ×2)",
                "left": "左键 (Left)",
                "right": "右键 (Right)",
                "button6": "侧键6 (button6)",
                "button7": "侧键7 (button7)",
            }
            return labels.get(key, key)
        return key

    @staticmethod
    def _coerce(value):
        """把字符串输入智能转换为 bool / int / float / str"""
        v = value.strip()
        if v == "":
            return ""
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    def open_device_settings(self, device_type):
        """打开某类设备的配置对话框：已有设备列表 + 添加/删除设备"""
        meta = self.DEVICE_TYPE_META.get(device_type)
        if not meta:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{meta['icon']} {meta['name']} 设备设置 / Device Settings")
        dlg.resize(420, 480)
        dlg.setStyleSheet(
            "QDialog, QWidget { background-color: #1e1e2e; color: #cdd6f4; }"
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; border-radius: 6px; "
            "margin-top: 12px; padding-top: 15px; color: #89b4fa; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
            "QLineEdit, QComboBox { background-color: #313244; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 4px; padding: 6px; }"
            "QPushButton { background-color: #89b4fa; color: #11111b; border: none; "
            "border-radius: 4px; padding: 6px 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #b4befe; }"
            "QListWidget { background-color: #313244; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 4px; }"
        )

        root = QVBoxLayout(dlg)

        # ---- 已有设备列表 ----
        list_group = QGroupBox("已添加设备 / Added Devices")
        list_layout = QVBoxLayout()
        device_list = QListWidget()
        list_layout.addWidget(device_list)

        def refresh_list():
            device_list.clear()
            for d in self.config.devices:
                if d.get("type") == device_type:
                    device_list.addItem(d.get("id", ""))

        del_btn = QPushButton("删除选中设备 / Delete Selected")
        del_btn.clicked.connect(lambda: _delete_device())
        list_layout.addWidget(del_btn)
        list_group.setLayout(list_layout)
        root.addWidget(list_group)

        # ---- 添加设备表单 ----
        add_group = QGroupBox("添加设备 / Add Device")
        form = QFormLayout()

        id_input = QLineEdit()
        id_input.setPlaceholderText(f"例如 {device_type}_1")
        form.addRow("设备 ID:", id_input)

        param_inputs = {}
        for p in meta["params"]:
            inp = QLineEdit()
            inp.setText(str(p.get("default", "")))
            param_inputs[p["key"]] = inp
            form.addRow(QLabel(p["label"] + ":"), inp)

        add_btn = QPushButton("添加设备 / Add")
        add_btn.clicked.connect(lambda: _add_device())
        form.addRow("", add_btn)
        add_group.setLayout(form)
        root.addWidget(add_group)

        # ---- 手柄按键映射（gamepad 专用，替代主界面设备映射）----
        if device_type == "gamepad":
            map_group = QGroupBox("按键映射 / Button Mapping")
            map_layout = QVBoxLayout()

            gamepad_ids = [d["id"] for d in self.config.devices if d.get("type") == "gamepad"]
            self._gamepad_map_combos = {}

            if not gamepad_ids:
                map_layout.addWidget(QLabel("尚未添加手柄设备，请先在上方添加。"))
            else:
                for gid in gamepad_ids:
                    gmap = self.config.device_mappings.get(gid, {})
                    sub = QGroupBox(gid)
                    sub_form = QFormLayout()
                    combos = {}
                    for key in self.GAMEPAD_KEYS:
                        combo = QComboBox()
                        combo.addItem("（未映射）", "")
                        for aid, aname in self.ACTION_OPTIONS:
                            combo.addItem(aname, aid)
                        cur = gmap.get(key, "")
                        idx = combo.findData(cur)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                        combos[key] = combo
                        sub_form.addRow(QLabel(self.GAMEPAD_KEY_LABELS.get(key, key) + ":"), combo)
                    self._gamepad_map_combos[gid] = combos
                    sub.setLayout(sub_form)
                    map_layout.addWidget(sub)

            def _save_mapping():
                for gid, combos in self._gamepad_map_combos.items():
                    mapping = {}
                    for key, combo in combos.items():
                        action = combo.currentData()
                        if action:
                            mapping[key] = action
                    self.config.device_mappings[gid] = mapping
                self.config.save_config()
                QMessageBox.information(dlg, "提示", "手柄映射已保存，重启应用后生效")

            save_map_btn = QPushButton("保存映射 / Save Mapping")
            save_map_btn.clicked.connect(lambda: _save_mapping())
            map_layout.addWidget(save_map_btn)

            map_group.setLayout(map_layout)
            root.addWidget(map_group)

        def _add_device():
            dev_id = id_input.text().strip()
            if not dev_id:
                QMessageBox.warning(dlg, "提示", "请输入设备 ID")
                return
            for d in self.config.devices:
                if d.get("id") == dev_id:
                    QMessageBox.warning(dlg, "提示", f"设备 ID '{dev_id}' 已存在")
                    return
            cfg = {}
            for key, inp in param_inputs.items():
                cfg[key] = self._coerce(inp.text())
            self.config.devices.append({
                "id": dev_id,
                "type": device_type,
                "config": cfg,
                "enabled": True,
            })
            self.config.save_config()
            refresh_list()
            QMessageBox.information(dlg, "提示", f"已添加设备 '{dev_id}'，重启应用后生效")

        def _delete_device():
            item = device_list.currentItem()
            if not item:
                QMessageBox.warning(dlg, "提示", "请先选中要删除的设备")
                return
            dev_id = item.text()
            self.config.devices = [d for d in self.config.devices if d.get("id") != dev_id]
            self.config.device_mappings.pop(dev_id, None)
            self.config.save_config()
            refresh_list()
            QMessageBox.information(dlg, "提示", f"已删除设备 '{dev_id}'，重启应用后生效")

        refresh_list()
        dlg.exec_()

    def update_shortcut_display(self, tool_name):
        shortcuts = self.config.shortcuts.get(tool_name, {})
        text = "当前 IDE 实际快捷键：\n"
        
        # 格式化快捷键显示
        def format_keys(keys):
            return " + ".join([k.upper() for k in keys])
            
        text += f"• 内联生成: {format_keys(shortcuts.get('inline_edit', []))}\n"
        text += f"• 唤醒聊天: {format_keys(shortcuts.get('toggle_chat', []))}\n"
        text += f"• 接受代码: {format_keys(shortcuts.get('accept_diff', []))}"
        
        self.shortcut_label.setText(text)

    def on_auto_detect_changed(self, state):
        is_auto = (state == Qt.Checked)
        self.tool_combo.setDisabled(is_auto)
        if is_auto:
            self.shortcut_label.setText("当前 IDE 实际快捷键：\n(将根据前台窗口自动匹配)")
        else:
            self.update_shortcut_display(self.tool_combo.itemData(self.tool_combo.currentIndex()))

    def on_tool_changed(self, index):
        tool_name = self.tool_combo.itemData(index)
        self.update_shortcut_display(tool_name)
        self.pet_ui.switch_tool(tool_name)

    def save_settings(self):
        # 保存 IDE 绑定
        self.config.auto_detect_ide = self.auto_detect_cb.isChecked()
        if not self.config.auto_detect_ide:
            self.config.current_tool = self.tool_combo.currentData()

        # 保存设备映射（鼠标 / 手柄 / 翻页笔等所有设备）
        for device_id, combos in self.device_mapping_combos.items():
            mapping = {}
            for key, combo in combos.items():
                action = combo.currentData()
                if action:  # 空值（未映射）不写入
                    mapping[key] = action
            self.config.device_mappings[device_id] = mapping

        # 保存 LLM / Token Plan 配置
        self.config.token_plan["enabled"] = self.llm_enabled_cb.isChecked()
        self.config.token_plan["api_key"] = self.llm_api_key_input.text().strip()
        self.config.token_plan["model"] = self.model_combo.currentText().strip()
        self.config.token_plan["endpoint"] = self.endpoint_input.text().strip()
        self.config.token_plan["refine_voice_text"] = self.refine_cb.isChecked()

        # 保存输出/反馈配置
        for timing_key, checkboxes in self.feedback_checkboxes.items():
            enabled = [ftype for ftype, cb in checkboxes.items() if cb.isChecked()]
            self.config.feedback[timing_key] = enabled
        hw = self.config.feedback.setdefault("hardware", {})
        hw["led_enabled"] = self.feedback_led_cb.isChecked()
        hw["vibration_enabled"] = self.feedback_vibration_cb.isChecked()
        self.config.feedback.setdefault("mascot", {})["enabled"] = self.mascot_enabled_cb.isChecked()

        # 持久化到 config.json
        self.config.save_config()
        print("[Settings] 配置已保存 / Configuration saved")

    def create_feedback_tab(self):
        """输出 / 反馈配置页：三个时机的反馈类型 + 硬件开关"""
        widget = QWidget()
        layout = QVBoxLayout()

        feedback_types = [
            ("sound", "声音 Sound"),
            ("overlay", "浮窗 Overlay"),
            ("notification", "通知 Notify"),
            ("led", "LED"),
            ("vibration", "震动 Vibrate"),
        ]

        timing_groups = [
            ("on_received", "收到输入时 / On Received"),
            ("on_success", "执行成功时 / On Success"),
            ("on_error", "执行失败时 / On Error"),
        ]

        self.feedback_checkboxes = {}  # {timing: {type: checkbox}}

        for timing_key, timing_label in timing_groups:
            group = QGroupBox(timing_label)
            row = QHBoxLayout()
            checkboxes = {}
            current = self.config.feedback.get(timing_key, [])
            for ftype, flabel in feedback_types:
                cb = QCheckBox(flabel)
                cb.setChecked(ftype in current)
                checkboxes[ftype] = cb
                row.addWidget(cb)
            row.addStretch()
            self.feedback_checkboxes[timing_key] = checkboxes
            group.setLayout(row)
            layout.addWidget(group)

        # 硬件反馈开关
        hw_group = QGroupBox("硬件反馈 / Hardware")
        hw_form = QFormLayout()
        hardware = self.config.feedback.get("hardware", {}) or {}
        self.feedback_led_cb = QCheckBox("启用 LED 指示灯 (LED Enabled)")
        self.feedback_led_cb.setChecked(bool(hardware.get("led_enabled", False)))
        hw_form.addRow("", self.feedback_led_cb)
        self.feedback_vibration_cb = QCheckBox("启用震动马达 (Vibration Enabled)")
        self.feedback_vibration_cb.setChecked(bool(hardware.get("vibration_enabled", False)))
        hw_form.addRow("", self.feedback_vibration_cb)

        # 第三方反馈（点击跳转到三方伙伴标签页）
        tp_label = QLabel("第三方反馈 / Third-Party:")
        tp_label.setStyleSheet("color: #6c7086; border: none;")
        hw_form.addRow("", tp_label)

        tp_row = QWidget()
        tp_lay = QHBoxLayout(tp_row)
        tp_lay.setContentsMargins(0, 0, 0, 0)
        tp_lay.setSpacing(6)
        for name in ["🐂 悬浮牛来", "💨 小佩吹风机", "💡 多色灯光"]:
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self._goto_partner_tab)
            tp_lay.addWidget(btn)
        tp_lay.addStretch()
        hw_form.addRow("", tp_row)

        hw_group.setLayout(hw_form)
        layout.addWidget(hw_group)

        # 桌宠联动（悬浮牛来动画）
        mascot_group = QGroupBox("桌宠联动 / Mascot")
        mascot_form = QFormLayout()
        mascot_cfg = self.config.feedback.get("mascot", {}) or {}
        self.mascot_enabled_cb = QCheckBox("启用桌宠动画联动（工作 / 完成 / 动作 / 录音 / Skill 状态）")
        self.mascot_enabled_cb.setChecked(bool(mascot_cfg.get("enabled", True)))
        mascot_form.addRow("", self.mascot_enabled_cb)

        # 大模型生成桌宠形象
        self.mascot_prompt_input = QLineEdit()
        self.mascot_prompt_input.setPlaceholderText("描述桌宠形象，如：一只可爱的像素风黄色小牛")
        mascot_form.addRow("形象描述:", self.mascot_prompt_input)

        gen_btn = QPushButton("生成桌宠形象 (大模型文生图)")
        gen_btn.clicked.connect(self.on_generate_mascot)
        mascot_form.addRow("", gen_btn)

        self.mascot_gen_label = QLabel("生成后将作为桌宠待机形象 (custom_idle.png)")
        self.mascot_gen_label.setWordWrap(True)
        self.mascot_gen_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        mascot_form.addRow("", self.mascot_gen_label)

        mascot_group.setLayout(mascot_form)
        layout.addWidget(mascot_group)

        # 智能监控（视频流接入 + 桌宠联动报警）
        stream_group = QGroupBox("Smart Monitor / 智能监控")
        stream_form = QFormLayout()
        stream_form.addRow("RTSP/HTTP URL:", QLineEdit("rtsp://admin:12345@192.168.1.200/stream1"))
        stream_form.addRow("AI Analysis:", QCheckBox("Enable YOLOv8 Object Detection (开启异常识别)"))
        stream_group.setLayout(stream_form)
        layout.addWidget(stream_group)

        linkage_group = QGroupBox("Pet Linkage / 桌宠联动报警")
        link_layout = QVBoxLayout()
        link_layout.addWidget(QCheckBox("当监控检测到异常时，桌宠变为红色警报状态", checked=True))
        link_layout.addWidget(QCheckBox("允许使用鼠标侧键控制监控云台 (PTZ 控制)", checked=False))
        linkage_group.setLayout(link_layout)
        layout.addWidget(linkage_group)

        preview_box = QLabel("[ Video Stream Preview Area / 监控预览画面占位 ]")
        preview_box.setAlignment(Qt.AlignCenter)
        preview_box.setStyleSheet("background-color: #11111b; border: 1px dashed #45475a; border-radius: 4px; min-height: 100px;")
        layout.addWidget(preview_box)

        hint = QLabel("提示：继电器通知在「🤝 三方伙伴」标签页配置。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6c7086; font-size: 12px;")
        layout.addWidget(hint)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _goto_partner_tab(self):
        """跳转到三方伙伴标签页"""
        if hasattr(self, 'tabs') and hasattr(self, 'tab_partner'):
            self.tabs.setCurrentWidget(self.tab_partner)

    def on_nl_config(self):
        """自然语言配置：调用大模型理解意图，返回 JSON 并应用配置"""
        text = self.nl_input.text().strip()
        if not text:
            self.nl_label.setText("请输入自然语言配置描述")
            return

        from .token_plan import TokenPlanClient
        client = TokenPlanClient(self.config.token_plan)
        if not client.is_enabled():
            self.nl_label.setText("Token Plan 未启用或未配置 API Key（请在「Vibe Coding 输入」页配置）")
            return

        self.nl_label.setText("AI 正在理解配置意图…")

        import threading
        import re
        import json as _json
        from PyQt5.QtCore import QTimer
        from core.config import VibeTool

        tool_list = ", ".join(t.value for t in VibeTool)

        system_prompt = (
            "你是 Vibe Mouse 桌面工具的配置助手。用户用自然语言描述想修改的配置，"
            "你需要只返回一个 JSON（不要输出其他任何内容），格式为：\n"
            '{"summary": "一句话说明做了什么", "updates": {"字段路径": 新值}}\n'
            f"支持的 AI IDE 工具：{tool_list}\n"
            "可配置字段路径（点号分隔）及取值：\n"
            "- current_tool: 当前工具（从上面工具列表中取值）\n"
            "- auto_detect_ide: 自动识别 IDE，true/false\n"
            "- shortcuts.<工具>.<动作>: 某工具某动作的快捷键，值是按键数组，如 [\"ctrl\",\"k\"]\n"
            "- device_mappings.mouse_default.button8: 鼠标上侧键(前进键)动作\n"
            "- device_mappings.mouse_default.button9: 鼠标下侧键(后退键)动作\n"
            "- device_mappings.mouse_default.middle: 鼠标中键动作\n"
            "- device_mappings.mouse_default.middle_double: 鼠标中键双击动作\n"
            "- feedback.hardware.led_enabled: LED 反馈，true/false\n"
            "- feedback.hardware.vibration_enabled: 震动反馈，true/false\n"
            "- feedback.mascot.enabled: 桌宠联动，true/false\n"
            "- token_plan.enabled: 大模型桥接，true/false\n"
            "- token_plan.model: 大模型名称\n"
            "- token_plan.refine_voice_text: 用 LLM 优化语音文本，true/false\n"
            "动作取值（用于 device_mappings 的映射值）：inline_edit(内联生成)/toggle_chat(唤醒聊天)/"
            "accept_diff(接受)/reject_diff(拒绝)/voice_input(语音输入)/submit_chat(发送提交)/"
            "relay:on_1/relay:off_1/relay:toggle_1(继电器通道1开/关/切换)，通道2、3同理。"
        )

        def _run():
            raw = client.chat(text, system_prompt)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                QTimer.singleShot(0, lambda: self.nl_label.setText(f"AI 返回无法解析：{raw}"))
                return
            try:
                parsed = _json.loads(m.group(0))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.nl_label.setText(f"JSON 解析失败：{e}"))
                return

            updates = parsed.get("updates") or {}
            summary = parsed.get("summary", "")
            applied = self._apply_config_update(updates)
            self.config.save_config()

            def _done():
                if applied:
                    self.nl_label.setText(f"已更新：{', '.join(applied)}。{summary}（部分设置重开面板后显示最新值）")
                else:
                    self.nl_label.setText(f"未找到可应用的配置变更。{summary}")

            QTimer.singleShot(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _apply_config_update(self, updates):
        """按 'a.b.c' 路径通用应用配置更新，返回成功应用的字段列表"""
        applied = []
        if not isinstance(updates, dict):
            return applied
        for path, value in updates.items():
            parts = str(path).split(".")
            obj = self.config
            ok = True
            for part in parts[:-1]:
                if isinstance(obj, dict):
                    obj = obj.setdefault(part, {})
                else:
                    obj = getattr(obj, part, None)
                if obj is None:
                    ok = False
                    break
            if not ok:
                continue
            last = parts[-1]
            try:
                if isinstance(obj, dict):
                    obj[last] = value
                else:
                    setattr(obj, last, value)
                applied.append(str(path))
            except Exception:
                continue
        return applied

    def on_generate_mascot(self):
        """大模型文生图生成桌宠待机形象，保存为 assets/custom_idle.png"""
        prompt = self.mascot_prompt_input.text().strip()
        if not prompt:
            self.mascot_gen_label.setText("请输入形象描述")
            return

        from .token_plan import TokenPlanClient
        client = TokenPlanClient(self.config.token_plan)
        if not client.is_enabled():
            self.mascot_gen_label.setText("Token Plan 未启用或未配置 API Key（请在「Vibe Coding 输入」页配置）")
            return

        self.mascot_gen_label.setText("生成中，请稍候…（约 10-40 秒）")

        import threading
        import os
        from PyQt5.QtCore import QTimer

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
        path = os.path.join(assets_dir, 'custom_idle.png')

        def _run():
            ok, result = client.generate_image(prompt)
            if not ok:
                QTimer.singleShot(0, lambda: self.mascot_gen_label.setText(f"生成失败：{result}"))
                return
            try:
                with open(path, 'wb') as f:
                    f.write(result)
            except Exception as e:
                QTimer.singleShot(0, lambda: self.mascot_gen_label.setText(f"保存失败：{e}"))
                return

            def _done():
                self.mascot_gen_label.setText("已生成桌宠形象，待机时显示")
                if self.pet_ui is not None:
                    self.pet_ui.play_idle_animation()

            QTimer.singleShot(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def create_partner_tab(self):
        """三方伙伴组件配置页：三方反馈（第三方设备 + 继电器）"""
        widget = QWidget()
        layout = QVBoxLayout()

        # ---- 三方反馈总览 ----
        fb_group = QGroupBox("三方反馈 / Third-Party Feedback")
        fb_layout = QVBoxLayout()
        fb_layout.setSpacing(8)

        dev_title = QLabel("第三方设备：")
        dev_title.setStyleSheet("color: #6c7086; border: none; font-size: 12px;")
        fb_layout.addWidget(dev_title)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(8)
        dev_items = [
            ("🐂", "悬浮牛来", "配合语音（桌宠 + 语音提示）"),
            ("💨", "小佩吹风机", "吹风反馈（第三方设备）"),
        ]
        for icon, name, desc in dev_items:
            btn = QPushButton(f"{icon} {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda c, n=name, d=desc: QMessageBox.information(self, n, f"{n}（第三方设备）\n\n{d}"))
            dev_row.addWidget(btn)
        fb_layout.addLayout(dev_row)

        relay_title = QLabel("继电器：")
        relay_title.setStyleSheet("color: #6c7086; border: none; font-size: 12px;")
        fb_layout.addWidget(relay_title)

        relay_btn = QPushButton("💡 多色灯光")
        relay_btn.setCursor(Qt.PointingHandCursor)
        relay_btn.clicked.connect(lambda: QMessageBox.information(
            self, "多色灯光", "通过 BLE 继电器控制。\n请在下方「继电器管理」中配置鉴权、通道与通知模式。"))
        fb_layout.addWidget(relay_btn)

        fb_group.setLayout(fb_layout)
        layout.addWidget(fb_group)

        # ---- 机器人执行器（自研机械臂：鼠标接管控制）----
        control_group = QGroupBox("Robot Actuator / 鼠标接管控制")
        ctrl_layout = QVBoxLayout()
        override_check = QCheckBox("Enable Mouse Override (接管鼠标操控机械臂)")
        override_check.setStyleSheet("color: #f38ba8;")
        ctrl_layout.addWidget(override_check)
        ctrl_layout.addWidget(QLabel("当开启时，鼠标移动映射为机械臂 XY 轴，滚轮映射为 Z 轴。"))
        control_group.setLayout(ctrl_layout)
        layout.addWidget(control_group)

        # ---- BLE 继电器管理（扫描/连接在控制面板进行，此处管理鉴权与设备参数）----
        relay_group = QGroupBox("BLE Relay / 继电器管理（三方伙伴）")
        form_layout = QFormLayout()

        from PyQt5.QtCore import QRegExp
        from PyQt5.QtGui import QRegExpValidator

        # 鉴权密码（连接后 AT+SEND<pwd>@ 自动鉴权）
        self.relay_pwd_input = QLineEdit(str(self.config.ble_relay.get("password", "")))
        pwd_btn = QPushButton("保存密码")
        pwd_btn.clicked.connect(self.on_relay_save_password)
        pwd_row = QWidget()
        pwd_lay = QHBoxLayout(pwd_row)
        pwd_lay.setContentsMargins(0, 0, 0, 0)
        pwd_lay.addWidget(self.relay_pwd_input)
        pwd_lay.addWidget(pwd_btn)
        form_layout.addRow("鉴权密码:", pwd_row)

        # 设备改名（AT+NAME<name>@，回复 Name Set OK）
        self.relay_name_input = QLineEdit()
        self.relay_name_input.setMaxLength(20)
        self.relay_name_input.setPlaceholderText("新设备名")
        name_btn = QPushButton("改名")
        name_btn.clicked.connect(self.on_relay_rename)
        name_row = QWidget()
        name_lay = QHBoxLayout(name_row)
        name_lay.setContentsMargins(0, 0, 0, 0)
        name_lay.addWidget(self.relay_name_input)
        name_lay.addWidget(name_btn)
        form_layout.addRow("设备改名:", name_row)

        # 修改设备密码（AT+PIN<6位>@，回复 PIN PASS 后自动更新本地密码）
        self.relay_pin_input = QLineEdit()
        self.relay_pin_input.setMaxLength(6)
        self.relay_pin_input.setPlaceholderText("6 位数字")
        self.relay_pin_input.setValidator(QRegExpValidator(QRegExp("[0-9]{6}")))
        self.relay_pin_input.setEchoMode(QLineEdit.Password)
        pin_btn = QPushButton("修改密码")
        pin_btn.clicked.connect(self.on_relay_change_pin)
        pin_row = QWidget()
        pin_lay = QHBoxLayout(pin_row)
        pin_lay.setContentsMargins(0, 0, 0, 0)
        pin_lay.addWidget(self.relay_pin_input)
        pin_lay.addWidget(pin_btn)
        form_layout.addRow("设备改密:", pin_row)

        self.relay_reply_label = QLabel("（改名/改密需先在控制面板连接继电器）")
        self.relay_reply_label.setWordWrap(True)
        self.relay_reply_label.setStyleSheet("color: #6c7086;")
        form_layout.addRow("设备回复:", self.relay_reply_label)

        relay_group.setLayout(form_layout)
        layout.addWidget(relay_group)

        # 订阅继电器 AT 回复（多订阅者列表，关闭对话框时移除）
        from .ble_relay import get_relay_controller
        self._relay = get_relay_controller(self.config)
        if self._relay is not None:
            from PyQt5.QtCore import QObject, pyqtSignal

            class _ReplyBridge(QObject):
                reply = pyqtSignal(str)

            self._relay_bridge = _ReplyBridge()
            self._relay_bridge.reply.connect(self.relay_reply_label.setText)
            self._pending_pin = None
            self._hook_raw = self._on_relay_raw
            self._relay.on_raw_msg.append(self._hook_raw)
            self.finished.connect(self._unhook_relay)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    # ------------------------------------------------------------------
    # BLE 继电器操作
    # ------------------------------------------------------------------
    def on_relay_save_password(self):
        pwd = self.relay_pwd_input.text().strip()
        if not pwd:
            self.relay_reply_label.setText("密码不能为空")
            return
        self.config.ble_relay["password"] = pwd
        self.config.save_config()
        self.relay_reply_label.setText("密码已保存，下次连接生效")

    def on_relay_rename(self):
        name = self.relay_name_input.text().strip()
        if not name:
            self.relay_reply_label.setText("请输入新设备名")
            return
        if self._relay is None or not self._relay.is_connected:
            self.relay_reply_label.setText("继电器未连接，请先在控制面板连接")
            return
        self._relay.send_at(f"AT+NAME{name}@")

    def on_relay_change_pin(self):
        pin = self.relay_pin_input.text().strip()
        if len(pin) != 6 or not pin.isdigit():
            self.relay_reply_label.setText("密码必须为 6 位数字")
            return
        if self._relay is None or not self._relay.is_connected:
            self.relay_reply_label.setText("继电器未连接，请先在控制面板连接")
            return
        self._pending_pin = pin
        self._relay.send_at(f"AT+PIN{pin}@")

    def _on_relay_raw(self, msg):
        """继电器 AT 回复（asyncio 线程触发）→ 显示 + 改密成功自动更新本地密码"""
        self._relay_bridge.reply.emit(msg)
        if "PIN PASS" in msg and getattr(self, "_pending_pin", None):
            self.config.ble_relay["password"] = self._pending_pin
            self.config.save_config()
            self._pending_pin = None

    def _unhook_relay(self):
        """对话框关闭时移除继电器回调订阅"""
        if getattr(self, "_relay", None) is not None and getattr(self, "_hook_raw", None):
            try:
                self._relay.on_raw_msg.remove(self._hook_raw)
            except ValueError:
                pass
            self._hook_raw = None

    def on_model_changed(self, index):
        """切换模型预设时，自动更新 endpoint 输入框（自定义输入则不覆盖）"""
        data = self.model_combo.currentData()
        if data and data.get("endpoint"):
            self.endpoint_input.setText(data["endpoint"])
