"""
Skill 引擎 / Skill Engine

Skill 是 VibeMouse 的顶层配置单元。一个 Skill = 一套完整的工作模式，
可以包含：
  - triggers: 触发方式（关键词/正则/外设绑定 skill:<name>）
  - system_prompt: LLM 人设提示词
  - actions: 激活时执行的动作序列
  - shortcuts: 快捷键覆盖层（按工具分组，覆盖默认快捷键）
  - feedback: 反馈配置覆盖层（声音/浮窗/LED/震动）
  - devices: 设备激活列表（激活 Skill 时自动启用指定设备）
  - metadata: 版本、作者等元信息

触发方式：
1. 外设按键映射到 "skill:<name>" — 直接触发
2. 语音输入匹配触发词 — 自动匹配

Skill 格式（YAML 或 JSON）:
---
name: code-review
version: "1.0"
description: 代码审查模式
triggers:
  words: ["审查", "review", "检查代码"]
  priority: 10
system_prompt: |
  你是一个资深代码审查专家...
actions:
  - type: execute_action
    value: toggle_chat
  - type: set_mode
    value: chat
shortcuts:
  trae:
    inline_edit: ["ctrl", "u"]
    toggle_chat: ["ctrl", "i"]
feedback:
  on_received: ["sound", "led"]
  on_success: ["overlay"]
  on_error: ["sound", "notification"]
devices:
  - id: voice_mic
    enabled: true
metadata:
  author: "vibemouse"
  tags: ["code", "review"]
enabled: true
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Skill:
    """Skill 数据模型 — 一个 Skill = 一套完整的工作模式"""
    name: str
    version: str = "1.0"
    description: str = ""
    triggers: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    # ===== 新增：配置覆盖层 =====
    shortcuts: Dict[str, Dict[str, list]] = field(default_factory=dict)    # {tool: {action: [keys]}}
    feedback: Dict[str, Any] = field(default_factory=dict)                 # 反馈配置覆盖
    devices: List[Dict[str, Any]] = field(default_factory=list)            # 设备激活列表
    metadata: Dict[str, Any] = field(default_factory=dict)                 # 作者、标签等
    # ===== 通用字段 =====
    enabled: bool = True
    source: str = "inline"  # "inline" 或文件路径

    @property
    def trigger_words(self) -> List[str]:
        return self.triggers.get("words", [])

    @property
    def trigger_regex(self) -> Optional[str]:
        return self.triggers.get("regex")

    @property
    def priority(self) -> int:
        return self.triggers.get("priority", 0)

    @property
    def has_overrides(self) -> bool:
        """是否包含任何配置覆盖（shortcuts/feedback/devices）"""
        return bool(self.shortcuts or self.feedback or self.devices)

    def get_shortcut_override(self, tool: str, action: str) -> Optional[list]:
        """获取 Skill 对某工具某动作的快捷键覆盖"""
        return self.shortcuts.get(tool, {}).get(action)

    def to_dict(self) -> dict:
        """导出为 dict（用于保存到配置文件）"""
        d = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "triggers": self.triggers,
            "system_prompt": self.system_prompt,
            "actions": self.actions,
            "enabled": self.enabled,
        }
        if self.shortcuts:
            d["shortcuts"] = self.shortcuts
        if self.feedback:
            d["feedback"] = self.feedback
        if self.devices:
            d["devices"] = self.devices
        if self.metadata:
            d["metadata"] = self.metadata
        return d


class SkillEngine:
    """
    Skill 引擎
    负责加载、匹配、激活和管理 Skill。

    激活 Skill 时：
    1. 执行 actions（快捷键 / set_mode / set_tool / inject_text）
    2. 应用 shortcuts 覆盖层（通过 executor 更新 config 的活跃快捷键）
    3. 应用 feedback 覆盖层（通过 executor 更新 feedback manager）
    4. 激活 devices（通过 device_manager 启用指定设备）

    退出 Skill 时：恢复所有默认配置。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.skills: Dict[str, Skill] = {}
        self.enabled = self.config.get("enabled", True)
        self.fallback_action = self.config.get("fallback_action", "inline_edit")
        self._active_skill: Optional[Skill] = None
        self._load_from_config()

    def _load_from_config(self):
        """从配置中加载所有 Skill"""
        # 1. 加载内联 Skill
        inline_skills = self.config.get("inline_skills", [])
        for sk_data in inline_skills:
            try:
                skill = self._build_skill(sk_data, source="inline")
                if skill.name:
                    self.skills[skill.name] = skill
            except Exception as e:
                print(f"[SkillEngine] Failed to load inline skill: {e}")

        # 2. 从文件加载 Skill
        skill_files = self.config.get("skill_files", [])
        for filepath in skill_files:
            self.load_skill_file(filepath)

    def _build_skill(self, data: dict, source: str = "inline") -> Skill:
        """从 dict 构建 Skill 对象"""
        return Skill(
            name=data.get("name", ""),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            triggers=data.get("triggers", {}),
            system_prompt=data.get("system_prompt", ""),
            actions=data.get("actions", []),
            shortcuts=data.get("shortcuts", {}),
            feedback=data.get("feedback", {}),
            devices=data.get("devices", []),
            metadata=data.get("metadata", {}),
            enabled=data.get("enabled", True),
            source=source,
        )

    def load_skill_file(self, filepath: str) -> bool:
        """从 YAML 或 JSON 文件加载单个 Skill"""
        if not os.path.exists(filepath):
            print(f"[SkillEngine] Skill file not found: {filepath}")
            return False

        try:
            data = self._parse_file(filepath)
            skill = self._build_skill(data, source=filepath)
            if skill.name:
                self.skills[skill.name] = skill
                print(f"[SkillEngine] Loaded skill: {skill.name} v{skill.version} from {filepath}")
                return True
        except Exception as e:
            print(f"[SkillEngine] Failed to load {filepath}: {e}")

        return False

    def _parse_file(self, filepath: str) -> dict:
        """解析 YAML 或 JSON 文件"""
        ext = os.path.splitext(filepath)[1].lower()

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if ext in (".yaml", ".yml"):
            try:
                import yaml
                return yaml.safe_load(content) or {}
            except ImportError:
                print("[SkillEngine] PyYAML not installed, falling back to JSON parsing")
                return json.loads(content)
        else:
            return json.loads(content)

    def match(self, text: str) -> Optional[Skill]:
        """
        匹配用户输入文本到最合适的 Skill

        匹配策略（按优先级排序）：
        1. 关键词匹配 trigger_words
        2. 正则表达式匹配 trigger_regex
        3. 按 priority 排序，返回最高优先级的匹配
        """
        if not self.enabled or not text:
            return None

        text_lower = text.lower().strip()
        matches = []

        for skill in self.skills.values():
            if not skill.enabled:
                continue

            # 1. 关键词匹配
            for word in skill.trigger_words:
                if word.lower() in text_lower:
                    matches.append(skill)
                    break

            # 2. 正则匹配
            if skill.trigger_regex:
                try:
                    if re.search(skill.trigger_regex, text, re.IGNORECASE):
                        if skill not in matches:
                            matches.append(skill)
                except re.error:
                    pass

        if not matches:
            return None

        matches.sort(key=lambda s: s.priority, reverse=True)
        return matches[0]

    def get_system_prompt(self, skill: Optional[Skill] = None) -> str:
        """获取 Skill 的系统提示词"""
        if skill and skill.system_prompt:
            return skill.system_prompt
        return ""

    def apply_actions(self, skill: Skill) -> Dict[str, Any]:
        """
        解析 Skill 定义的 actions，返回需要修改的上下文

        返回的 context 包含：
        - mode: 处理模式 (auto/paste/chat/action)
        - prefix: 注入前缀文本
        - tool: 要切换的工具名
        - execute_actions: 要执行的原生动作列表
        """
        context = {}
        for action in skill.actions:
            action_type = action.get("type", "")
            if action_type == "set_mode":
                context["mode"] = action.get("value", "auto")
            elif action_type == "inject_text":
                context["prefix"] = action.get("value", "")
            elif action_type == "set_tool":
                context["tool"] = action.get("value", "")
            elif action_type == "execute_action":
                actions_list = context.setdefault("execute_actions", [])
                actions_list.append(action.get("value", ""))
        return context

    def resolve_skill_action(self, action_name: str) -> Optional[Skill]:
        """
        解析动作字符串，如果是 "skill:<name>" 格式则返回对应 Skill。
        """
        if not action_name or not action_name.startswith("skill:"):
            return None

        skill_name = action_name[6:]
        skill = self.skills.get(skill_name)
        if skill and skill.enabled:
            print(f"[SkillEngine] Skill 动作触发: {skill.name} - {skill.description}")
            return skill
        elif skill_name in self.skills:
            print(f"[SkillEngine] Skill '{skill_name}' 存在但未启用")
        else:
            print(f"[SkillEngine] 未找到 Skill: {skill_name}")
        return None

    def get_skill_names(self) -> List[str]:
        """返回所有已启用 Skill 的名称列表"""
        return [s.name for s in self.skills.values() if s.enabled]

    def get_overrides(self, skill: Skill) -> Dict[str, Any]:
        """
        获取 Skill 的配置覆盖层，供 executor 应用。

        返回：
        {
            "shortcuts": {tool: {action: [keys]}},
            "feedback": {on_received: [...], on_success: [...], ...},
            "devices": [{id: "...", enabled: true}, ...]
        }
        """
        overrides = {}
        if skill.shortcuts:
            overrides["shortcuts"] = skill.shortcuts
        if skill.feedback:
            overrides["feedback"] = skill.feedback
        if skill.devices:
            overrides["devices"] = skill.devices
        return overrides

    @property
    def active_skill(self) -> Optional[Skill]:
        """当前激活的 Skill"""
        return self._active_skill

    def set_active(self, skill: Optional[Skill]):
        """设置当前激活的 Skill"""
        self._active_skill = skill

    def clear_active(self):
        """清除当前激活的 Skill"""
        self._active_skill = None

    def list_skills(self) -> List[Skill]:
        """列出所有已加载的 Skill"""
        return list(self.skills.values())

    def add_skill(self, skill: Skill):
        """动态添加 Skill"""
        self.skills[skill.name] = skill

    def remove_skill(self, name: str):
        """移除 Skill"""
        self.skills.pop(name, None)

    def toggle_skill(self, name: str) -> bool:
        """切换 Skill 的启用状态"""
        if name in self.skills:
            self.skills[name].enabled = not self.skills[name].enabled
            return self.skills[name].enabled
        return False

    def export_skill(self, name: str) -> Optional[dict]:
        """导出 Skill 为 dict"""
        if name not in self.skills:
            return None
        return self.skills[name].to_dict()

    def get_builtin_skills(self) -> List[dict]:
        """获取内置 Skill 模板（含完整配置覆盖示例）"""
        return [
            {
                "name": "quick-code",
                "version": "1.0",
                "description": "快速生成代码片段 — 激活后自动打开内联编辑，语音直接生成代码",
                "triggers": {
                    "words": ["生成代码", "写个", "帮我写", "code", "generate", "写代码"],
                    "priority": 10
                },
                "system_prompt": "你是一个资深程序员。用户通过语音输入，请直接输出代码，不要加 Markdown 代码块标记。只输出代码本身，不要解释。",
                "actions": [
                    {"type": "execute_action", "value": "inline_edit"},
                    {"type": "set_mode", "value": "paste"}
                ],
                "feedback": {
                    "on_received": ["sound"],
                    "on_success": ["sound", "overlay"],
                    "on_error": ["sound", "notification"]
                },
                "metadata": {"author": "vibemouse", "tags": ["code", "generate"]},
                "enabled": True
            },
            {
                "name": "code-review",
                "version": "1.0",
                "description": "代码审查模式 — 激活后打开聊天面板，LED 变蓝，语音用审查 prompt",
                "triggers": {
                    "words": ["审查", "review", "检查代码", "优化", "refactor"],
                    "priority": 10
                },
                "system_prompt": "你是一个资深代码审查专家。请审查用户提供的代码，指出：1. 潜在Bug 2. 性能瓶颈 3. 安全风险 4. 代码规范问题。给出具体的修改建议。",
                "actions": [
                    {"type": "execute_action", "value": "toggle_chat"},
                    {"type": "set_mode", "value": "chat"}
                ],
                "feedback": {
                    "on_received": ["sound", "led"],
                    "on_success": ["overlay"],
                    "on_error": ["sound", "notification", "led"],
                    "hardware": {"led_enabled": True}
                },
                "devices": [
                    {"id": "voice_mic", "enabled": True}
                ],
                "metadata": {"author": "vibemouse", "tags": ["code", "review"]},
                "enabled": True
            },
            {
                "name": "presentation",
                "version": "1.0",
                "description": "演示模式 — 静音反馈，仅保留 LED 指示，快捷键简化",
                "triggers": {
                    "words": ["演示", "展示", "present", "demo"],
                    "priority": 5
                },
                "system_prompt": "你是一个演示助手。请用简洁的语言帮助用户完成演示相关的操作。",
                "actions": [
                    {"type": "set_mode", "value": "chat"}
                ],
                "shortcuts": {
                    "trae": {
                        "inline_edit": ["ctrl", "u"],
                        "toggle_chat": ["ctrl", "i"],
                        "accept_diff": ["ctrl", "enter"],
                        "reject_diff": ["esc"]
                    }
                },
                "feedback": {
                    "on_received": ["led"],
                    "on_success": ["led"],
                    "on_error": ["led"],
                    "hardware": {"led_enabled": True, "vibration_enabled": False}
                },
                "metadata": {"author": "vibemouse", "tags": ["demo", "quiet"]},
                "enabled": True
            },
            {
                "name": "explain-code",
                "version": "1.0",
                "description": "解释代码逻辑和原理",
                "triggers": {
                    "words": ["解释", "explain", "什么意思", "原理", "how"],
                    "priority": 8
                },
                "system_prompt": "你是一个编程导师。请用简洁的中文解释代码的逻辑和关键知识点，让初学者也能理解。",
                "actions": [
                    {"type": "execute_action", "value": "toggle_chat"},
                    {"type": "set_mode", "value": "chat"}
                ],
                "metadata": {"author": "vibemouse", "tags": ["explain", "learn"]},
                "enabled": True
            },
        ]
