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

        else:  # mode == "auto"
            # 自动模式：有代码内容则粘贴，有动作标记则执行动作
            if action and self.executor:
                self.executor.execute_action(action)
                time.sleep(0.3)  # 等动作触发后再粘贴

            if clean_text:
                self._type_text(clean_text)
                if self._on_response:
                    self._on_response(clean_text)

    def _extract_action(self, text: str) -> str:
        """从回复中提取动作标记，如 [ACTION:inline_edit]"""
        import re
        match = re.search(r'\[ACTION:(\w+)\]', text)
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
    # 键盘输入辅助
    # ------------------------------------------------------------------
    def _type_text(self, text: str):
        """将文本模拟键盘输入到当前光标位置"""
        if not text:
            return
        print(f"[VoiceLLM] 粘贴文本 ({len(text)} 字符)")
        try:
            # 先粘贴到剪贴板再 Ctrl+V 更可靠，但这里用直接输入
            # 对于多行文本，逐行输入
            for char in text:
                if char == '\n':
                    self.keyboard.press(Key.enter)
                    self.keyboard.release(Key.enter)
                else:
                    self.keyboard.type(char)
                time.sleep(0.005)  # 轻微延迟避免丢键
        except Exception as e:
            print(f"[VoiceLLM] 输入文本失败: {e}")

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
