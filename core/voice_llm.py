"""
语音 + 大模型桥接器 / Voice-to-LLM Bridge

将语音识别结果通过华为云 Token Plan 发送给大模型，获取智能回复后：
- A. 将回复文本直接粘贴到当前光标位置（模拟键盘输入）
- B. 将回复意图解析为 VibeMouse 动作并执行
- C. 将回复显示在浮窗中供用户参考

Skill 支持两种触发方式：
1. 外设按键映射为 "skill:<name>" — 直触发，激活 Skill 上下文供后续语音使用
2. 语音文本匹配触发词 — 自动匹配最佳 Skill

依赖：core/token_plan.py
"""

import threading
import time
from typing import Optional, Callable
from pynput.keyboard import Controller, Key
from .token_plan import TokenPlanClient


class VoiceLLMBridge:
    """
    语音-大模型桥接器
    连接语音识别结果与华为云大模型，实现“说一句话，AI 帮你操作/写代码”。

    可选启用「语音文本优化」：先用大模型纠正语音识别中的口音/同音字/专业术语错误，
    再将优化后的文本用于后续处理（代码生成/动作执行/对话）。

    支持「Skill 模式」：
    - 外设按键激活的 Skill（executor.active_skill）优先级最高
    - 语音触发词自动匹配作为备选
    """

    # 系统提示词：语音文本优化（纠错 + 提示词工程）
    REFINE_SYSTEM_PROMPT = (
        "你是一个语音输入优化专家。你的任务是将用户的口语化语音输入，\n"
        "转化为精准、结构化、适合大模型理解的高质量提示词。\n\n"
        "处理步骤：\n"
        "1. 纠错：修正语音识别错误（同音字、口音、术语误识别）\n"
        "2. 理解意图：判断用户想要做什么（生成代码、解释代码、执行动作、问答）\n"
        "3. 提示词优化：将口语转化为精准、包含上下文、约束明确的提示词\n\n"
        "优化规则：\n"
        "- 补充缺失的技术细节（如编程语言、框架、边界条件）\n"
        "- 将模糊描述转化为明确的指令（如'写个排序'→'用Python实现快速排序'）\n"
        "- 保留用户原始意图，不添加用户没有要求的内容\n"
        "- 如果用户意图是执行动作（生成/编辑/聊天/接受/拒绝），输出动作标记\n"
        "- 只输出优化后的最终提示词，不要任何解释、前缀、分析过程\n"
        "- 如果涉及编程关键词，使用正确的英文拼写\n\n"
        "示例：\n"
        "输入：'写个排序' → 输出：'用Python实现快速排序算法，包含输入验证、异常处理和详细注释'\n"
        "输入：'牌序' → 输出：'排序'\n"
        "输入：'打开聊天' → 输出：'[ACTION:toggle_chat]'\n"
        "输入：'看看这段代码有什么问题' → 输出：'请分析以下代码的性能瓶颈、潜在Bug和安全风险，并给出具体的优化建议'\n"
    )

    # 系统提示词：对话/代码生成（默认兜底）
    DEFAULT_SYSTEM_PROMPT = (
        "你是一个 VibeMouse 智能助手。用户通过语音与你交互。\n"
        "你的任务是帮助用户高效编程，可以：\n"
        "1. 生成代码并直接输出（纯代码，不要 Markdown 代码块标记）\n"
        "2. 回答技术问题\n"
        "3. 当用户说'生成'、'编辑'、'聊天'、'接受'、'拒绝'等意图时，"
        "在回复末尾追加一行动作标记：[ACTION:inline_edit] 等\n"
        "可用动作标记：[ACTION:inline_edit] [ACTION:toggle_chat] [ACTION:accept_diff] [ACTION:reject_diff]\n"
        "继电器控制标记（用户提到通道/继电器时使用）："
        "[ACTION:relay_on_1] [ACTION:relay_off_1] [ACTION:relay_on_2] [ACTION:relay_off_2] "
        "[ACTION:relay_on_3] [ACTION:relay_off_3]\n"
        "请用中文回复。"
    )

    def __init__(self, token_plan_config: dict, executor=None, skill_engine=None):
        self.client = TokenPlanClient(token_plan_config)
        self.executor = executor
        self.keyboard = Controller()
        self._busy = False
        self._on_response: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # 是否启用语音文本优化（从 token_plan 配置中读取）
        self.refine_enabled = token_plan_config.get("refine_voice_text", False)

        # Skill 引擎（共享实例，由 executor 创建并传入）
        self.skill_engine = skill_engine

    def is_ready(self) -> bool:
        """检查是否已配置好 Token Plan"""
        return self.client.is_enabled()

    def set_callbacks(self, on_response: Optional[Callable] = None, on_error: Optional[Callable] = None):
        """设置回调：收到回复 / 发生错误"""
        self._on_response = on_response
        self._on_error = on_error

    # ------------------------------------------------------------------
    # 语音文本优化：纠错 + 润色
    # ------------------------------------------------------------------
    def refine_text(self, raw_text: str, callback: Callable[[str], None]):
        """
        用大模型纠正语音识别结果中的错误。

        Args:
            raw_text: 语音识别的原始文本
            callback: 回调函数，接收优化后的文本
        """
        if not self.is_ready() or not self.refine_enabled:
            # 未启用优化，直接返回原文
            callback(raw_text)
            return

        print(f"[VoiceLLM] 优化语音文本: {raw_text}")

        def _on_refine(success: bool, refined: str):
            if success and refined and not refined.startswith("[TokenPlan]"):
                print(f"[VoiceLLM] 优化结果: {raw_text} -> {refined}")
                callback(refined.strip())
            else:
                # 优化失败，回退到原文
                print(f"[VoiceLLM] 优化失败，使用原文: {raw_text}")
                callback(raw_text)

        self.client.chat_async(
            user_message=raw_text,
            callback=_on_refine,
            system_prompt=self.REFINE_SYSTEM_PROMPT
        )

    # ------------------------------------------------------------------
    # 主入口：语音文本 -> (可选优化) -> 大模型 -> 处理结果
    # ------------------------------------------------------------------
    def process_voice_text(self, text: str, mode: str = "auto"):
        """
        处理语音识别后的文本

        流程：
        1. 如果启用 refine，先调用大模型纠错优化文本
        2. 将优化后的文本发送给大模型进行对话/代码生成
        3. 根据模式处理回复（粘贴/执行动作/显示对话）

        Args:
            text: 语音识别结果
            mode: 处理模式
                - "auto": 自动判断（代码生成/问答/动作）
                - "paste": 直接将大模型回复粘贴到光标位置
                - "action": 仅解析动作标记并执行
                - "chat": 仅对话，显示浮窗
        """
        if not self.is_ready():
            print("[VoiceLLM] Token Plan 未配置，跳过 LLM 处理")
            # 未配置时，尝试本地意图匹配
            self._fallback_local_action(text)
            return

        if self._busy:
            print("[VoiceLLM] 正在处理中，请稍候...")
            return

        # 第一步：可选优化语音文本
        def _proceed(processed_text: str):
            self._busy = True

            # ===== Skill 匹配 =====
            matched_skill = None
            skill_context = {}

            # 优先级 1：executor 中由外设按键激活的 Skill
            if self.executor and self.executor.active_skill:
                matched_skill = self.executor.active_skill
                skill_context = self.executor.active_skill_context
                print(f"[VoiceLLM] 使用激活的 Skill: {matched_skill.name} - {matched_skill.description}")
                # 使用完毕后清除激活状态（单次激活）
                self.executor.clear_active_skill()

            # 优先级 2：语音触发词自动匹配
            if not matched_skill and self.skill_engine:
                matched_skill = self.skill_engine.match(processed_text)
                if matched_skill:
                    print(f"[VoiceLLM] Skill 匹配: {matched_skill.name} - {matched_skill.description}")
                    skill_context = self.skill_engine.apply_actions(matched_skill)

            # Skill 可以覆盖 mode
            if "mode" in skill_context:
                mode = skill_context["mode"]

            # 确定 system_prompt：Skill > 默认
            if matched_skill and matched_skill.system_prompt:
                system_prompt = matched_skill.system_prompt
            else:
                system_prompt = self.DEFAULT_SYSTEM_PROMPT

            # 如果有 inject_text action，在消息前注入前缀
            user_message = processed_text
            if "prefix" in skill_context:
                user_message = skill_context["prefix"] + "\n" + processed_text

            print(f"[VoiceLLM] 发送给大模型: {user_message[:100]}...")

            def _callback(success: bool, result: str):
                self._busy = False
                if not success:
                    print(f"[VoiceLLM] 错误: {result}")
                    if self._on_error:
                        self._on_error(result)
                    return

                print(f"[VoiceLLM] 模型回复: {result[:200]}...")
                self._handle_model_response(result, mode)

            # 第二步：用（优化后的）文本调用大模型
            self.client.chat_async(
                user_message=user_message,
                callback=_callback,
                system_prompt=system_prompt
            )

        # 先优化，再处理
        self.refine_text(text, _proceed)

    # ------------------------------------------------------------------
    # 处理模型回复
    # ------------------------------------------------------------------
    def _handle_model_response(self, response: str, mode: str):
        """解析模型回复并执行对应操作"""
        # 提取动作标记
        action = self._extract_action(response)

        # 去掉动作标记后的纯文本
        clean_text = self._strip_action_markers(response)

        if mode == "paste":
            # 模式A：直接粘贴文本
            self._type_text(clean_text)
            if self._on_response:
                self._on_response(clean_text)

        elif mode == "action":
            # 模式B：仅执行动作
            if action and self.executor:
                self.executor.execute_action(action)

        elif mode == "chat":
            # 模式C：仅显示对话
            if self._on_response:
                self._on_response(clean_text)

        elif mode == "scad":
            # 模式D：OpenSCAD 3D 模型生成（保存 .scad → 渲染 .stl）
            self._handle_scad_response(clean_text)

        else:  # mode == "auto"
            # 自动模式：有代码内容则粘贴，有动作标记则执行动作
            if action and self.executor:
                self.executor.execute_action(action)
                time.sleep(0.3)  # 等动作触发后再粘贴

            if clean_text:
                self._type_text(clean_text)
                if self._on_response:
                    self._on_response(clean_text)

    def _handle_scad_response(self, scad_code: str):
        """
        处理 OpenSCAD 3D 模型生成：保存 .scad → 调用 OpenSCAD 渲染 .stl。

        用于「scad-design」Skill（mode=scad）：模型回复为纯 OpenSCAD 代码，
        不粘贴到 IDE，而是落盘渲染为 STL 文件供 3D 打印。
        """
        import os
        from .feedback import FeedbackTiming
        from .scad_generator import ScadGenerator

        print("[VoiceLLM] SCAD 模式：生成 3D 模型...")

        gen = ScadGenerator()
        success, result = gen.generate(scad_code)

        if success:
            basename = os.path.basename(result)
            print(f"[VoiceLLM] STL 已生成: {result}")
            if self.executor:
                self.executor.feedback.trigger(
                    FeedbackTiming.ON_SUCCESS,
                    "scad_design",
                    f"3D 模型已生成：{basename}（output 目录）",
                )
            if self._on_response:
                self._on_response(result)
        else:
            print(f"[VoiceLLM] SCAD 生成失败: {result}")
            if self.executor:
                self.executor.feedback.trigger(
                    FeedbackTiming.ON_ERROR,
                    "scad_design",
                    f"3D 模型生成失败：{result}",
                )
            if self._on_error:
                self._on_error(result)

    def _extract_action(self, text: str) -> str:
        """从回复中提取动作标记，如 [ACTION:inline_edit] / [ACTION:relay:on_1]"""
        import re
        match = re.search(r'\[ACTION:\s*([\w:]+)\s*\]', text)
        if match:
            return match.group(1)
        return ""

    def _strip_action_markers(self, text: str) -> str:
        """去掉动作标记行"""
        import re
        lines = text.split('\n')
        clean = [line for line in lines if not re.match(r'^\[ACTION:', line.strip())]
        return '\n'.join(clean).strip()

    # ------------------------------------------------------------------
    # 本地回退：未配置 Token Plan 时的本地意图匹配
    # ------------------------------------------------------------------
    def _fallback_local_action(self, text: str):
        """未启用大模型时，用本地关键词匹配执行动作"""
        text_lower = text.lower().strip()

        local_map = {
            # 继电器控制（前插，优先匹配，避免被通用关键词拦截）
            "relay_on_1": ["打开通道1", "打开通道一", "开通道1", "开通道一", "继电器1开", "继电器一开"],
            "relay_on_2": ["打开通道2", "打开通道二", "开通道2", "开通道二", "继电器2开", "继电器二开"],
            "relay_on_3": ["打开通道3", "打开通道三", "开通道3", "开通道三", "继电器3开", "继电器三开"],
            "relay_off_1": ["关闭通道1", "关闭通道一", "关通道1", "关通道一", "继电器1关", "继电器一关"],
            "relay_off_2": ["关闭通道2", "关闭通道二", "关通道2", "关通道二", "继电器2关", "继电器二关"],
            "relay_off_3": ["关闭通道3", "关闭通道三", "关通道3", "关通道三", "继电器3关", "继电器三关"],
            "inline_edit": ["生成", "编辑", "写入", "代码", "generate", "edit", "code"],
            "toggle_chat": ["聊天", "面板", "对话", "chat", "panel", "talk"],
            "accept_diff": ["接受", "采纳", "同意", "yes", "accept", "ok"],
            "reject_diff": ["拒绝", "取消", "不要", "no", "reject", "cancel"],
        }

        for action, keywords in local_map.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    print(f"[VoiceLLM] 本地匹配: {text} -> {action}")
                    if self.executor:
                        self.executor.execute_action(action)
                    return

        print(f"[VoiceLLM] 未匹配到本地动作: {text}")

    # ------------------------------------------------------------------
    # 键盘输入辅助（剪贴板 + Ctrl+V，避免逐字输入丢键）
    # ------------------------------------------------------------------
    def _type_text(self, text: str):
        """
        将文本粘贴到当前光标位置。

        使用「剪贴板 + Ctrl+V」方式，比逐字 keyboard.type() 快且可靠，
        尤其适合中文和多行文本。
        """
        if not text:
            return
        print(f"[VoiceLLM] 粘贴文本 ({len(text)} 字符)")
        try:
            # 保存当前剪贴板内容
            old_clip = self._get_clipboard()

            # 写入新文本到剪贴板
            if not self._set_clipboard(text):
                print("[VoiceLLM] 剪贴板写入失败，回退到逐字输入")
                self._type_text_fallback(text)
                return

            # 等待剪贴板就绪
            time.sleep(0.08)

            # 模拟 Ctrl+V 粘贴
            self.keyboard.press(Key.ctrl)
            self.keyboard.press('v')
            time.sleep(0.05)
            self.keyboard.release('v')
            self.keyboard.release(Key.ctrl)

            # 等待粘贴完成
            time.sleep(0.1)

            # 恢复原始剪贴板内容
            if old_clip:
                self._set_clipboard(old_clip)

            print("[VoiceLLM] 文本已粘贴")
        except Exception as e:
            print(f"[VoiceLLM] 粘贴失败: {e}，回退到逐字输入")
            self._type_text_fallback(text)

    def _type_text_fallback(self, text: str):
        """回退方案：逐字符模拟键盘输入（慢但兼容性好）"""
        for char in text:
            if char == '\n':
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
            else:
                self.keyboard.type(char)
            time.sleep(0.005)

    def _set_clipboard(self, text: str) -> bool:
        """
        设置剪贴板文本（线程安全，不依赖 tkinter）。

        Windows: 使用 Win32 API (ctypes)
        macOS:   使用 pbcopy 命令
        Linux:   使用 xclip 命令
        """
        import platform
        system = platform.system()

        if system == "Windows":
            return self._set_clipboard_win32(text)
        elif system == "Darwin":
            import subprocess
            try:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                return True
            except Exception:
                return False
        else:  # Linux
            import subprocess
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                                           stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                return True
            except Exception:
                return False

    def _set_clipboard_win32(self, text: str) -> bool:
        """Windows: 使用 Win32 API 设置剪贴板（完全线程安全）"""
        import ctypes

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # 64-bit 兼容：设置正确的返回类型和参数类型
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

        # UTF-16LE 编码 + 空终止符
        data = (text + '\0').encode('utf-16-le')

        # 重试机制：剪贴板可能被其他程序锁定
        for attempt in range(5):
            if user32.OpenClipboard(0):
                break
            time.sleep(0.05)
        else:
            return False

        try:
            user32.EmptyClipboard()

            # 分配全局内存
            h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_global:
                return False

            # 锁定内存并复制数据
            ptr = kernel32.GlobalLock(h_global)
            if ptr:
                ctypes.memmove(ptr, data, len(data))
                kernel32.GlobalUnlock(h_global)

            # 设置剪贴板数据（所有权转移给系统）
            user32.SetClipboardData(CF_UNICODETEXT, h_global)
            return True
        except Exception as e:
            print(f"[VoiceLLM] Win32 clipboard error: {e}")
            return False
        finally:
            user32.CloseClipboard()

    def _get_clipboard(self) -> str:
        """
        获取当前剪贴板文本（用于粘贴后恢复）。
        Windows 使用 Win32 API，其他平台使用系统命令。
        """
        import platform
        system = platform.system()

        if system == "Windows":
            return self._get_clipboard_win32()
        elif system == "Darwin":
            import subprocess
            try:
                result = subprocess.run(['pbpaste'], capture_output=True, timeout=2)
                return result.stdout.decode('utf-8', errors='ignore')
            except Exception:
                return ""
        else:
            import subprocess
            try:
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'],
                                        capture_output=True, timeout=2)
                return result.stdout.decode('utf-8', errors='ignore')
            except Exception:
                return ""

    def _get_clipboard_win32(self) -> str:
        """Windows: 使用 Win32 API 读取剪贴板"""
        import ctypes

        CF_UNICODETEXT = 13

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # 64-bit 兼容：设置正确的返回类型和参数类型
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.GetClipboardData.argtypes = [ctypes.c_uint]

        for attempt in range(5):
            if user32.OpenClipboard(0):
                break
            time.sleep(0.05)
        else:
            return ""

        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""

            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""

            try:
                # 读取 UTF-16LE 字符串
                raw = ctypes.wstring_at(ptr)
                return raw
            finally:
                kernel32.GlobalUnlock(handle)
        except Exception:
            return ""
        finally:
            user32.CloseClipboard()

    # ------------------------------------------------------------------
    # 快捷命令：常用场景一键调用
    # ------------------------------------------------------------------
    def quick_generate(self, description: str):
        """快捷生成代码：语音 -> 大模型生成代码 -> 自动粘贴"""
        if not self.is_ready():
            print("[VoiceLLM] Token Plan 未配置")
            return

        self._busy = True
        print(f"[VoiceLLM] 代码生成请求: {description}")

        def _callback(success, result):
            self._busy = False
            if success:
                self._type_text(result)
                if self._on_response:
                    self._on_response(result)
            else:
                if self._on_error:
                    self._on_error(result)

        self.client.chat_async(
            user_message=f"请生成以下代码，只输出代码本身，不要解释：\n{description}",
            callback=_callback,
            system_prompt="你是一个资深程序员。只输出代码，不加任何说明和 Markdown 标记。"
        )

    def quick_explain(self, code_text: str):
        """快捷解释代码：选中代码 -> 大模型解释 -> 显示浮窗"""
        if not self.is_ready():
            print("[VoiceLLM] Token Plan 未配置")
            return

        self._busy = True

        def _callback(success, result):
            self._busy = False
            if success and self._on_response:
                self._on_response(result)
            elif not success and self._on_error:
                self._on_error(result)

        self.client.chat_async(
            user_message=f"请用中文解释这段代码：\n```\n{code_text}\n```",
            callback=_callback,
            system_prompt="你是一个编程导师。用简洁的中文解释代码逻辑和关键知识点。"
        )
