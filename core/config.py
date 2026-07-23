import json
import os
import platform
from enum import Enum
from .feedback import DEFAULT_FEEDBACK
from .token_plan import DEFAULT_TOKEN_PLAN

class VibeTool(Enum):
    TRAE = "trae"
    CURSOR = "cursor"
    WINDSURF = "windsurf"
    COPILOT = "copilot"
    DEVECO_STUDIO = "deveco_studio"
    DEVECO_CODE = "deveco_code"
    CODEARTS = "codearts"

# 判断操作系统，自适应 Ctrl 或 Cmd
IS_MAC = platform.system() == "Darwin"
CTRL_KEY = "cmd" if IS_MAC else "ctrl"

# 默认各个工具的快捷键配置
DEFAULT_SHORTCUTS = {
    VibeTool.TRAE.value: {
        "inline_edit": [CTRL_KEY, "u"],
        "toggle_chat": [CTRL_KEY, "i"],
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
        "voice_input": ["alt", "v"],
    },
    VibeTool.CURSOR.value: {
        "inline_edit": [CTRL_KEY, "k"],
        "toggle_chat": [CTRL_KEY, "l"],
        "accept_diff": [CTRL_KEY, "y"],
        "reject_diff": ["esc"],
        "voice_input": [],
    },
    VibeTool.WINDSURF.value: {
        "inline_edit": [CTRL_KEY, "shift", "i"],
        "toggle_chat": [CTRL_KEY, "l"],
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
        "voice_input": ["alt", "a"],
    },
    VibeTool.COPILOT.value: {
        "inline_edit": [CTRL_KEY, "i"],
        "toggle_chat": [CTRL_KEY, "alt", "i"],
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
        "voice_input": ["alt", "a"],
    },
    VibeTool.DEVECO_STUDIO.value: {
        "inline_edit": ["alt", "i"],
        "toggle_chat": ["alt", "u"],
        "accept_diff": ["alt", "enter"],
        "reject_diff": ["esc"],
        "voice_input": ["alt", "v"],
    },
    VibeTool.DEVECO_CODE.value: {
        "inline_edit": ["tab"],
        "toggle_chat": ["esc"],
        "accept_diff": ["tab"],
        "reject_diff": ["esc"],
        "voice_input": [],
    },
    VibeTool.CODEARTS.value: {
        "inline_edit": ["alt", "c"],
        "toggle_chat": ["alt", "x"],
        "accept_diff": ["tab"],
        "reject_diff": ["esc"],
        "voice_input": ["alt", "a"],
    }
}

# 默认设备列表
DEFAULT_DEVICES = [
    {
        "id": "mouse_default",
        "type": "mouse",
        "config": {},
        "enabled": True
    }
]

# 默认设备映射：device_id -> {input_id -> action}
DEFAULT_DEVICE_MAPPINGS = {
    "mouse_default": {
        "button8": "inline_edit",
        "button9": "toggle_chat",
        "middle": "accept_diff",
    }
}

class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.current_tool = VibeTool.TRAE.value
        self.shortcuts = {}
        self.devices = []
        self.device_mappings = {}
        self.feedback = {}
        self.load_config()

        # ===== Skill 覆盖层 =====
        # 当 Skill 被激活时，覆盖层的快捷键/反馈会叠加在默认配置之上
        # 退出 Skill 时清除覆盖层，恢复默认
        self._skill_shortcut_override = {}   # {tool: {action: [keys]}}
        self._skill_feedback_override = {}   # {on_received: [...], ...}
        self._skill_device_overrides = []    # [{id, enabled}, ...]

    def load_config(self):
        """加载配置，保持向后兼容"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error loading config / 加载配置失败: {e}")
                data = {}
        else:
            data = {}

        # 工具快捷键（新旧兼容）
        self.current_tool = data.get("current_tool", VibeTool.TRAE.value)
        loaded_shortcuts = data.get("shortcuts", {})
        # 合并默认值，确保新工具有默认配置
        self.shortcuts = self._merge_defaults(DEFAULT_SHORTCUTS, loaded_shortcuts)

        # 设备列表（新配置）
        self.devices = data.get("devices", DEFAULT_DEVICES.copy())

        # 设备映射（新配置，兼容旧的 mouse_mapping）
        if "device_mappings" in data:
            self.device_mappings = data["device_mappings"]
        elif "mouse_mapping" in data:
            # 向后兼容：将旧版 mouse_mapping 迁移到 device_mappings
            self.device_mappings = {
                "mouse_default": data["mouse_mapping"]
            }
        else:
            self.device_mappings = DEFAULT_DEVICE_MAPPINGS.copy()

        # 反馈配置
        self.feedback = data.get("feedback", DEFAULT_FEEDBACK.copy())

        # Token Plan 配置（华为云大模型接入）
        self.token_plan = data.get("token_plan", DEFAULT_TOKEN_PLAN.copy())

        # Skill 配置（技能系统）
        self.skills = data.get("skills", {"enabled": True, "fallback_action": "inline_edit", "inline_skills": []})

        # 如果配置文件不存在或刚迁移，保存一次
        if not os.path.exists(self.config_file) or "mouse_mapping" in data:
            self.save_config()

    def save_config(self):
        data = {
            "current_tool": self.current_tool,
            "shortcuts": self.shortcuts,
            "devices": self.devices,
            "device_mappings": self.device_mappings,
            "feedback": self.feedback,
            "token_plan": self.token_plan,
            "skills": self.skills,
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _merge_defaults(self, defaults, loaded):
        """合并默认配置和用户配置，确保新增工具有默认值"""
        result = {}
        for key, value in defaults.items():
            if key in loaded:
                result[key] = {**value, **loaded[key]}
            else:
                result[key] = value.copy()
        # 保留用户自定义的工具
        for key, value in loaded.items():
            if key not in result:
                result[key] = value
        return result

    def get_current_shortcuts(self):
        """获取当前工具的快捷键（含 Skill 覆盖层）"""
        base = self.shortcuts.get(self.current_tool, {})
        # 应用 Skill 覆盖层
        override = self._skill_shortcut_override.get(self.current_tool, {})
        if override:
            return {**base, **override}
        return base

    def get_base_shortcuts(self):
        """获取当前工具的默认快捷键（不含 Skill 覆盖）"""
        return self.shortcuts.get(self.current_tool, {})

    def get_current_feedback(self):
        """获取当前反馈配置（含 Skill 覆盖层）"""
        if self._skill_feedback_override:
            return {**self.feedback, **self._skill_feedback_override}
        return self.feedback

    def get_base_feedback(self):
        """获取默认反馈配置（不含 Skill 覆盖）"""
        return self.feedback

    # ===== Skill 覆盖层管理 =====
    def apply_skill_overrides(self, shortcuts=None, feedback=None, devices=None):
        """应用 Skill 的配置覆盖层"""
        if shortcuts:
            self._skill_shortcut_override = shortcuts
        if feedback:
            self._skill_feedback_override = feedback
        if devices:
            self._skill_device_overrides = devices

    def clear_skill_overrides(self):
        """清除 Skill 的配置覆盖层，恢复默认"""
        self._skill_shortcut_override = {}
        self._skill_feedback_override = {}
        self._skill_device_overrides = []

    @property
    def has_skill_overrides(self) -> bool:
        """是否当前有 Skill 覆盖层生效"""
        return bool(self._skill_shortcut_override or self._skill_feedback_override or self._skill_device_overrides)

    # ---------- 向后兼容方法 ----------
    def get_action_for_button(self, button_name):
        """兼容旧版：从 mouse_default 映射中查找"""
        mapping = self.device_mappings.get("mouse_default", {})
        return mapping.get(button_name)

    @property
    def mouse_mapping(self):
        """兼容旧版 listener.py"""
        return self.device_mappings.get("mouse_default", {})

    # ---------- 新多外设方法 ----------
    def get_devices(self):
        """获取所有启用的设备配置"""
        return [d for d in self.devices if d.get("enabled", True)]

    def get_device_mapping(self, device_id):
        """获取指定设备的 input_id -> action 映射"""
        return self.device_mappings.get(device_id, {})

    def add_device(self, device_id, device_type, device_config=None, mapping=None):
        """动态添加设备"""
        if device_config is None:
            device_config = {}
        self.devices.append({
            "id": device_id,
            "type": device_type,
            "config": device_config,
            "enabled": True
        })
        if mapping:
            self.device_mappings[device_id] = mapping
        self.save_config()

    def remove_device(self, device_id):
        """移除设备"""
        self.devices = [d for d in self.devices if d["id"] != device_id]
        self.device_mappings.pop(device_id, None)
        self.save_config()
