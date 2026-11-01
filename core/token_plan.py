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

# 可选模型预设（华为云 MaaS，OpenAI 兼容接口）
# 设置界面会据此生成模型下拉框；model 为 API 调用传入的模型名，
# endpoint 为对应服务地址。用户也可在下拉框中直接输入自定义模型名。
MODEL_PRESETS = [
    {
        "name": "GLM-4.7 (智谱)",
        "model": "glm-4.7",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    },
    {
        "name": "GLM-4-Plus (智谱)",
        "model": "glm-4-plus",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    },
    {
        "name": "DeepSeek-V3 (深度求索)",
        "model": "deepseek-v3",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    },
    {
        "name": "DeepSeek-R1 (深度求索)",
        "model": "deepseek-r1",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    },
    {
        "name": "Kimi-K2 (月之暗面)",
        "model": "kimi-k2",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
    },
]

# 图片生成接口（华为云 MaaS 文生图，与文本接口域名不同，仅支持「西南-贵阳一」区域）
# 参考：https://support.huaweicloud.com/model-call-maas/model-call-023.md
IMAGE_GEN_ENDPOINT = "https://api.modelarts-maas.com"
IMAGE_GEN_MODEL = "qwen-image"  # Qwen_Image 文生图模型


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

    def generate_image(self, prompt: str, size: str = "1024x1024",
                       model: str = IMAGE_GEN_MODEL):
        """
        文生图：调用华为云 MaaS 图片生成接口（同步，可能耗时较长，建议在后台线程调用）。

        Args:
            prompt: 文本提示词（描述要生成的图片）
            size: 生成尺寸，如 "1024x1024"
            model: 文生图模型，默认 qwen-image

        Returns:
            (success: bool, result: bytes 图片数据 或 str 错误信息)
        """
        import base64

        if not self.is_enabled():
            return False, "Token Plan 未启用或未配置 API Key"

        url = f"{IMAGE_GEN_ENDPOINT}/v1/images/generations"
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.get('api_key', '').strip()}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"
        except Exception as e:
            return False, f"请求失败: {e}"

        data_list = result.get("data") or []
        if not data_list:
            return False, "图片生成返回空结果"

        b64 = data_list[0].get("b64_json") or ""
        if not b64:
            return False, "图片生成结果缺少 b64_json"

        # b64_json 可能带 "data:image/jpg;base64," 前缀，去掉后再解码
        if "," in b64:
            b64 = b64.split(",", 1)[1]

        try:
            return True, base64.b64decode(b64)
        except Exception as e:
            return False, f"图片解码失败: {e}"

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
