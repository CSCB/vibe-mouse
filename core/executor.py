import time
from typing import Optional
from pynput.keyboard import Controller, Key, KeyCode
from .feedback import FeedbackManager, FeedbackTiming
from .voice_llm import VoiceLLMBridge
from .skill_engine import SkillEngine

class ActionExecutor:
    def __init__(self, config):
        self.config = config
        self.keyboard = Controller()
        self.feedback = FeedbackManager(config.feedback if hasattr(config, 'feedback') else None)

        # Skill 引擎（整体功能层面）
        skill_config = config.skills if hasattr(config, 'skills') else None
        self.skill_engine = SkillEngine(skill_config) if skill_config else None

        # 当前激活的 Skill
        self._active_skill = None
        self._active_skill_context = {}

        # 语音 + 大模型桥接器（华为云 Token Plan）
        tp_config = config.token_plan if hasattr(config, 'token_plan') else {}
        self.voice_llm = VoiceLLMBridge(tp_config, executor=self, skill_engine=self.skill_engine)

        # 字符串到 pynput.keyboard.Key 的映射
        self.key_map = {
            "ctrl": Key.ctrl,
            "cmd": Key.cmd,
            "alt": Key.alt,
            "shift": Key.shift,
            "enter": Key.enter,
            "esc": Key.esc,
            "space": Key.space,
            "tab": Key.tab,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right
        }

    def _get_key(self, key_str):
        key_str = key_str.lower()
        if key_str in self.key_map:
            return self.key_map[key_str]
        elif len(key_str) == 1:
            return KeyCode.from_char(key_str)
        return None

    def execute_action(self, action_name):
        """
        执行动作。支持两种格式：
        - 原生动作："inline_edit", "toggle_chat" 等 → 按快捷键
        - Skill 引用："skill:<name>" → 触发 Skill（应用配置覆盖 + 激活上下文）
        """
        # ===== 1. 检查是否为 Skill 引用 =====
        if self.skill_engine and action_name.startswith("skill:"):
            self._execute_skill(action_name)
            return

        # ===== 2. 原生快捷键动作 =====
        shortcuts = self.config.get_current_shortcuts()
        if action_name not in shortcuts:
            print(f"[Executor] Action '{action_name}' not found in current tool shortcuts")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        keys_to_press = shortcuts[action_name]
        print(f"[Executor] 执行动作: {action_name} -> {keys_to_press}")

        # 反馈：收到输入
        self.feedback.trigger(FeedbackTiming.ON_RECEIVED, action_name)

        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]

        if not parsed_keys:
            print(f"[Executor] No valid keys for action '{action_name}'")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        try:
            for key in parsed_keys:
                self.keyboard.press(key)
            time.sleep(0.05)
            for key in reversed(parsed_keys):
                self.keyboard.release(key)
            self.feedback.trigger(FeedbackTiming.ON_SUCCESS, action_name)
        except Exception as e:
            print(f"[Executor] Error: {e}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)

    def _execute_skill(self, action_name: str):
        """
        执行 Skill 动作。由 "skill:<name>" 格式的 action 触发。

        完整流程：
        1. 解析 Skill 名称
        2. 如果当前已有激活的 Skill，先退出恢复默认
        3. 执行 Skill 的 actions（execute_action → 按快捷键，set_tool → 切换工具）
        4. 应用 Skill 的配置覆盖层（shortcuts/feedback/devices）
        5. 将 Skill 设为激活状态，后续语音输入自动使用其 system_prompt
        """
        skill = self.skill_engine.resolve_skill_action(action_name)
        if not skill:
            print(f"[Executor] Skill 未找到或未启用: {action_name}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        print(f"[Executor] ===== 激活 Skill: {skill.name} v{skill.version} =====")
        print(f"[Executor] 描述: {skill.description}")
        self.feedback.trigger(FeedbackTiming.ON_RECEIVED, f"skill:{skill.name}")

        # 如果当前已有激活的 Skill，先退出
        if self._active_skill:
            print(f"[Executor] 退出上一个 Skill: {self._active_skill.name}")
            self.deactivate_skill()

        # 解析 actions
        context = self.skill_engine.apply_actions(skill)

        # 1. 执行原生动作（如先按 inline_edit 唤起 IDE 的代码生成）
        for act_name in context.get("execute_actions", []):
            print(f"[Executor] Skill 动作: 执行 '{act_name}'")
            self._execute_raw_action(act_name)

        # 2. 切换工具
        if "tool" in context:
            self.switch_tool(context["tool"])

        # 3. 应用配置覆盖层（shortcuts / feedback / devices）
        self._apply_skill_overrides(skill)

        # 4. 将 Skill 设为激活状态
        self._active_skill = skill
        self._active_skill_context = context
        self.skill_engine.set_active(skill)

        print(f"[Executor] Skill '{skill.name}' 已激活")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, f"skill:{skill.name}")

    def _apply_skill_overrides(self, skill):
        """应用 Skill 的配置覆盖层到 config 和 feedback manager"""
        overrides = self.skill_engine.get_overrides(skill)

        if not overrides:
            print(f"[Executor] Skill '{skill.name}' 无配置覆盖层")
            return

        # 应用到 config（会影响 get_current_shortcuts / get_current_feedback）
        self.config.apply_skill_overrides(
            shortcuts=overrides.get("shortcuts"),
            feedback=overrides.get("feedback"),
            devices=overrides.get("devices")
        )

        # 更新 FeedbackManager 的配置
        if "feedback" in overrides:
            new_feedback = self.config.get_current_feedback()
            self.feedback.update_config(new_feedback)
            print(f"[Executor] 反馈配置已更新: {overrides['feedback']}")

        # 设备激活（打印日志，实际设备管理由 device_manager 负责）
        if "devices" in overrides:
            for dev in overrides["devices"]:
                print(f"[Executor] 设备激活: {dev.get('id', 'unknown')} (enabled={dev.get('enabled', True)})")

        if "shortcuts" in overrides:
            print(f"[Executor] 快捷键覆盖已应用: {list(overrides['shortcuts'].keys())}")

    def deactivate_skill(self):
        """退出当前 Skill，恢复所有默认配置"""
        if not self._active_skill:
            return

        skill_name = self._active_skill.name
        print(f"[Executor] ===== 退出 Skill: {skill_name} =====")

        # 恢复默认配置
        self.config.clear_skill_overrides()

        # 恢复默认反馈配置
        self.feedback.update_config(self.config.get_base_feedback())

        # 清除激活状态
        self._active_skill = None
        self._active_skill_context = {}
        self.skill_engine.clear_active()

        print(f"[Executor] Skill '{skill_name}' 已退出，配置已恢复")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, f"skill_exit:{skill_name}")

    def _execute_raw_action(self, action_name: str):
        """直接执行原生快捷键动作（不检查 skill: 前缀，避免递归）"""
        shortcuts = self.config.get_current_shortcuts()
        if action_name not in shortcuts:
            print(f"[Executor] Raw action '{action_name}' not found in shortcuts")
            return

        keys_to_press = shortcuts[action_name]
        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]

        if not parsed_keys:
            return

        try:
            for key in parsed_keys:
                self.keyboard.press(key)
            time.sleep(0.05)
            for key in reversed(parsed_keys):
                self.keyboard.release(key)
        except Exception as e:
            print(f"[Executor] Error in raw action '{action_name}': {e}")

    @property
    def active_skill(self) -> Optional[object]:
        """返回当前激活的 Skill"""
        return self._active_skill

    @property
    def active_skill_context(self) -> dict:
        """返回当前激活 Skill 的上下文"""
        return self._active_skill_context

    def clear_active_skill(self):
        """清除当前激活的 Skill（语音使用后调用，不恢复配置）"""
        self._active_skill = None
        self._active_skill_context = {}

    def switch_tool(self, tool_name):
        self.config.current_tool = tool_name
        self.config.save_config()
        print(f"[Executor] 切换工具至: {tool_name}")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, "switch_tool", f"已切换至: {tool_name}")
