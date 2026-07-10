"""火山方舟豆包 Chat Completions API 包装器。"""

import logging
import os
from typing import Any, Dict, List

import requests
from langchain_core.messages import BaseMessage


logger = logging.getLogger(__name__)


class DoubaoLLM:
    """将项目使用的 LangChain 消息转换为豆包兼容的消息格式。"""

    def __init__(self) -> None:
        self.api_key = os.getenv("ARK_API_KEY") or os.getenv("DOUBAO_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 ARK_API_KEY（或 DOUBAO_API_KEY）环境变量")

        base_url = os.getenv(
            "DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        ).rstrip("/")
        self.api_url = f"{base_url}/chat/completions"
        self.model = os.getenv("DOUBAO_MODEL", "Doubao-Seed-Character")
        self.timeout = float(os.getenv("DOUBAO_TIMEOUT", "30"))

    def _call(self, messages: List[BaseMessage]) -> str:
        response = self._make_request(self._format_messages(messages))
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"豆包 API 响应格式异常: {response}") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("豆包 API 返回了空回复")
        return content

    @staticmethod
    def _format_messages(messages: List[BaseMessage]) -> List[Dict[str, str]]:
        roles = {"human": "user", "ai": "assistant", "system": "system"}
        formatted = []
        for message in messages:
            if not hasattr(message, "content"):
                continue
            formatted.append(
                {
                    "role": roles.get(getattr(message, "type", "human"), "user"),
                    "content": str(message.content),
                }
            )
        return formatted

    def _make_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.8,
            },
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            logger.error("豆包 API HTTP 错误: %s", response.text[:1000])
            raise
