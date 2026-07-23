import time
from pynput.keyboard import Controller, Key, KeyCode
from .feedback import FeedbackManager, FeedbackTiming
from .voice_llm import VoiceLLMBridge

class ActionExecutor:
    def __init__(self, config):
        self.config = config
        self.keyboard = Controller()
        self.feedback = FeedbackManager(config.feedback if hasattr(config, 'feedback') else None)

        # 语音 + 大模型桥接器（华为云 Token Plan）
        tp_config = config.token_plan if hasattr(config, 'token_plan') else {}
        self.voice_llm = VoiceLLMBridge(tp_config, executor=self)
        
        # 字符串到 pynput.keyboard.Key 的映射
        # Mapping from string to pynput.keyboard.Key
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
        shortcuts = self.config.get_current_shortcuts()
        if action_name not in shortcuts:
            print(f"Action '{action_name}' not found in current tool shortcuts / 未在当前工具快捷键中找到动作 '{action_name}'.")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        keys_to_press = shortcuts[action_name]
        print(f"Executing action / 执行动作: {action_name} -> {keys_to_press}")

        # 反馈：收到输入
        self.feedback.trigger(FeedbackTiming.ON_RECEIVED, action_name)

        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]

        if not parsed_keys:
            print(f"[Executor] No valid keys to press for action '{action_name}'")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        try:
            # 按下所有键
            # Press all keys
            for key in parsed_keys:
                self.keyboard.press(key)

            # 极短暂的停顿确保系统响应组合键
            # A brief pause to ensure the system responds to the key combination
            time.sleep(0.05)

            # 释放所有键 (反向释放)
            # Release all keys (in reverse order)
            for key in reversed(parsed_keys):
                self.keyboard.release(key)

            # 反馈：执行成功
            self.feedback.trigger(FeedbackTiming.ON_SUCCESS, action_name)

        except Exception as e:
            print(f"[Executor] Error executing action '{action_name}': {e}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)

    def switch_tool(self, tool_name):
        self.config.current_tool = tool_name
        self.config.save_config()
        print(f"Switched to tool / 切换工具至: {tool_name}")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, "switch_tool", f"已切换至: {tool_name}")
