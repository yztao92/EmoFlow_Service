# File: llm/zhipu_wrapper.py

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")

class ZhipuLLM(BaseChatModel):
    def _call(self, messages, **kwargs):
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ZHIPU_API_KEY}"
        }
        payload = {
            "model": "glm-4",
            "messages": [
                {"role": "user", "content": messages[-1].content}
            ]
        }
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    @property
    def _llm_type(self):
        return "zhipu-chat"