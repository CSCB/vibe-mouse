"""
华为云 Token Plan / MaaS 模型即服务接口封装

用户只需填入 API Key，即可调用华为云大模型（GLM / DeepSeek / Kimi 等）。
支持：文本生成、代码生成、语音对话。

配置示例 (config.json):
{
    "token_plan": {
        "enabled": true,
        "api_key": "YOUR_HW_CLOUD_API_KEY",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
        "model": "glm-4.7",
        "max_tokens": 2048,
        "temperature": 0.7
    }
}
"""

import json
import urllib.request
import urllib.error
import threading
from typing import Optional, List, Dict, Any


DEFAULT_TOKEN_PLAN = {
    "enabled": False,
    "api_key": "",
    "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    "model": "glm-4.7",
    "max_tokens": 2048,
    "temperature": 0.7,
    "refine_voice_text": False,
}


class TokenPlanClient:
    """
    华为云 Token Plan 客户端
    封装 REST API 调用，支持同步和异步请求。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_TOKEN_PLAN.copy()
        self._lock = threading.Lock()

    def is_enabled(self) -> bool:
        return self.config.get("enabled", False) and bool(self.config.get("api_key", "").strip())

    def chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        同步调用大模型进行对话

        Args:
            user_message: 用户输入的文本
            system_prompt: 可选的系统提示词

        Returns:
            模型生成的回复文本
        """
        if not self.is_enabled():
            return "[TokenPlan] 未启用或未配置 API Key"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        return self._call_api(messages)

    def chat_async(self, user_message: str, callback, system_prompt: Optional[str] = None):
        """
        异步调用大模型，结果通过 callback 返回

        Args:
            user_message: 用户输入的文本
            callback: 回调函数，接收 (success: bool, result: str)
            system_prompt: 可选的系统提示词
        """
        def _run():
            try:
                result = self.chat(user_message, system_prompt)
                callback(True, result)
            except Exception as e:
                callback(False, str(e))

        threading.Thread(target=_run, daemon=True).start()

    def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """底层 HTTP 调用"""
        api_key = self.config.get("api_key", "").strip()
        endpoint = self.config.get("endpoint", DEFAULT_TOKEN_PLAN["endpoint"]).rstrip("/")
        model = self.config.get("model", DEFAULT_TOKEN_PLAN["model"])
        max_tokens = self.config.get("max_tokens", DEFAULT_TOKEN_PLAN["max_tokens"])
        temperature = self.config.get("temperature", DEFAULT_TOKEN_PLAN["temperature"])

        url = f"{endpoint}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                # 标准 OpenAI-compatible 格式
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                return "[TokenPlan] 模型返回空响应"
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            return f"[TokenPlan] HTTP {e.code}: {err_body}"
        except Exception as e:
            return f"[TokenPlan] 请求失败: {e}"

    # ------------------------------------------------------------------
    # 预设 Prompt 模板（针对 VibeMouse 场景优化）
    # ------------------------------------------------------------------
    def generate_code(self, description: str, language: str = "python") -> str:
        """根据自然语言描述生成代码"""
        system = f"You are an expert {language} developer. Generate clean, well-commented code based on the user's description. Only output code, no explanations."
        return self.chat(description, system)

    def explain_code(self, code: str) -> str:
        """解释代码含义"""
        system = "You are a programming tutor. Explain the following code in simple Chinese, highlighting key logic and potential issues."
        return self.chat(f"请解释这段代码:\n```\n{code}\n```", system)

    def translate_to_shortcuts(self, natural_language: str) -> str:
        """
        将自然语言意图转换为快捷键操作描述
        例如："打开聊天面板" -> "toggle_chat"
        """
        system = (
            "You are a VibeMouse assistant. The user speaks natural language. "
            "Map their intent to one of these actions: inline_edit, toggle_chat, accept_diff, reject_diff, voice_input. "
            "Reply with ONLY the action name, nothing else. If unclear, reply 'unknown'."
        )
        return self.chat(natural_language, system)


class TokenPlanManager:
    """
    Token Plan 管理器
    负责 Token 用量统计、套餐余量查询等。
    """

    def __init__(self, client: TokenPlanClient):
        self.client = client
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens_prompt": 0,
            "total_tokens_completion": 0,
        }

    def record_usage(self, prompt_tokens: int, completion_tokens: int):
        """记录一次调用的 Token 用量"""
        self.usage_stats["total_requests"] += 1
        self.usage_stats["total_tokens_prompt"] += prompt_tokens
        self.usage_stats["total_tokens_completion"] += completion_tokens

    def get_usage_report(self) -> Dict[str, int]:
        """获取用量报告"""
        return self.usage_stats.copy()
