import time
from pynput.keyboard import Controller, Key, KeyCode

class ActionExecutor:
    def __init__(self, config):
        self.config = config
        self.keyboard = Controller()
        
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
            return

        keys_to_press = shortcuts[action_name]
        print(f"Executing action / 执行动作: {action_name} -> {keys_to_press}")
        
        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]
        
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
            
    def switch_tool(self, tool_name):
        self.config.current_tool = tool_name
        self.config.save_config()
        print(f"Switched to tool / 切换工具至: {tool_name}")
