import json
import os
import platform
from enum import Enum

class VibeTool(Enum):
    TRAE = "trae"
    CURSOR = "cursor"
    WINDSURF = "windsurf"
    COPILOT = "copilot"
    DEVECO_STUDIO = "deveco_studio"
    DEVECO_CODE = "deveco_code"
    CODEARTS = "codearts"

# 判断操作系统，自适应 Ctrl 或 Cmd
# Detect OS to adaptively use Ctrl or Cmd
IS_MAC = platform.system() == "Darwin"
CTRL_KEY = "cmd" if IS_MAC else "ctrl"

# 默认各个工具的快捷键配置 (自适应 Mac 和 Win)
# Default shortcut configurations for each tool (Adaptive for Mac and Win)
DEFAULT_SHORTCUTS = {
    VibeTool.TRAE.value: {
        "inline_edit": [CTRL_KEY, "u"],        # 唤起 Builder / Invoke Builder
        "toggle_chat": [CTRL_KEY, "i"],        # 唤起 Chat / Invoke Chat
        "accept_diff": [CTRL_KEY, "enter"],    # 接受代码 / Accept Code
        "reject_diff": ["esc"],                # 拒绝代码 / Reject Code
    },
    VibeTool.CURSOR.value: {
        "inline_edit": [CTRL_KEY, "k"],        # 唤起 Generate / Invoke Generate
        "toggle_chat": [CTRL_KEY, "l"],        # 唤起 Chat / Invoke Chat
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
    },
    VibeTool.WINDSURF.value: {
        "inline_edit": [CTRL_KEY, "shift", "i"], # 唤起 Cascade / Invoke Cascade
        "toggle_chat": [CTRL_KEY, "l"],
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
    },
    VibeTool.COPILOT.value: {
        "inline_edit": [CTRL_KEY, "i"],        # 唤起 Inline Chat / Invoke Inline Chat
        "toggle_chat": [CTRL_KEY, "alt", "i"], # 唤起 Chat view / Invoke Chat view
        "accept_diff": [CTRL_KEY, "enter"],
        "reject_diff": ["esc"],
    },
    # DevEco Studio (HarmonyOS IDE, CodeGenie 内置 AI 助手)
    # DevEco Studio (HarmonyOS IDE with built-in CodeGenie AI assistant)
    # 参考文档: https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-edit-area-code-generation
    VibeTool.DEVECO_STUDIO.value: {
        "inline_edit": ["alt", "i"],                     # Inline Chat (Win: Alt+I, Mac: Cmd+I 通过 Alt 映射)
        "toggle_chat": ["alt", "u"],                     # CodeGenie 面板 (Win: Alt+U, Mac: Option+U)
        "accept_diff": ["alt", "enter"],                 # Accept All (接受全部生成内容)
        "reject_diff": ["esc"],                          # 拒绝 / 关闭 (Reject / Dismiss)
    },
    # DevEco Code (HarmonyOS 7 终端 AI Agent, 基于 OpenCode)
    # DevEco Code (HarmonyOS 7 Terminal AI Agent, based on OpenCode)
    # 参考: HDC 2026 发布, npm: @deveco-test/deveco-code
    VibeTool.DEVECO_CODE.value: {
        "inline_edit": ["tab"],                          # Tab 接受代码补全 (Accept suggestion)
        "toggle_chat": ["esc"],                          # Esc 取消/退出当前会话 (Dismiss/Exit session)
        "accept_diff": ["tab"],                          # Tab 接受编辑 (Accept edit)
        "reject_diff": ["esc"],                          # Esc 拒绝编辑 (Reject edit)
    },
    # 华为云码道 (CodeArts) 代码智能体
    # Huawei Cloud CodeArts Code Agent
    # 参考文档: https://support.huaweicloud.com/usermanual-codeartssnap/codeartsdoer_ug_0007.html
    VibeTool.CODEARTS.value: {
        "inline_edit": ["alt", "c"],                     # 多行代码续写 (Win: Alt+C, Mac: Option+C)
        "toggle_chat": ["alt", "x"],                     # 单行代码续写 (Win: Alt+X, Mac: Option+X)
        "accept_diff": ["tab"],                          # 接受生成的代码 (Accept)
        "reject_diff": ["esc"],                          # 取消生成的代码 (Dismiss)
    }
}

# 默认鼠标按键映射
# Default mouse button mapping
# mouse_button -> action_name
DEFAULT_MOUSE_MAPPING = {
    "button8": "inline_edit",  # 鼠标侧键 1 (后退) / Mouse side button 1 (Backward)
    "button9": "toggle_chat",  # 鼠标侧键 2 (前进) / Mouse side button 2 (Forward)
    "middle": "accept_diff",   # 鼠标中键 / Mouse middle button
    # 可以通过组合键扩展，例如 right_click + scroll 等
    # Can be extended via key combinations, e.g., right_click + scroll, etc.
}

class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.current_tool = VibeTool.TRAE.value
        self.shortcuts = DEFAULT_SHORTCUTS.copy()
        self.mouse_mapping = DEFAULT_MOUSE_MAPPING.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_tool = data.get("current_tool", self.current_tool)
                    self.shortcuts.update(data.get("shortcuts", {}))
                    self.mouse_mapping.update(data.get("mouse_mapping", {}))
            except Exception as e:
                print(f"Error loading config / 加载配置失败: {e}")
        else:
            self.save_config()

    def save_config(self):
        data = {
            "current_tool": self.current_tool,
            "shortcuts": self.shortcuts,
            "mouse_mapping": self.mouse_mapping
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_current_shortcuts(self):
        return self.shortcuts.get(self.current_tool, {})

    def get_action_for_button(self, button_name):
        return self.mouse_mapping.get(button_name)
