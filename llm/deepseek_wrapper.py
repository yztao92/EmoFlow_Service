# File: llm/deepseek_wrapper.py

import os
import requests
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.schema import AIMessage, HumanMessage, SystemMessage, ChatResult, ChatGeneration

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

class DeepSeekLLM(BaseChatModel):
    """
    Wrapper for DeepSeek Chat API.
    """

    def _call(self, messages, **kwargs):
        # Debug: 打印当前使用的 API Key，确认是否正确
        print("🔑 Using DeepSeek key:", DEEPSEEK_API_KEY)

        # 构造 DeepSeek API 请求
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # 转换消息格式
        converted_messages = []
        for m in messages:
            if isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, AIMessage):
                role = "assistant"
            elif isinstance(m, SystemMessage):
                role = "system"
            else:
                raise ValueError(f"Unsupported message type: {type(m)}")
                
            converted_messages.append({
                "role": role,
                "content": m.content
            })
        
        payload = {
            "model": "deepseek-chat",
            "messages": converted_messages,
            **kwargs  # 允许传递其他参数
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected API response format: {str(e)}")

    def _generate(self, messages, **kwargs) -> ChatResult:
        """
        BaseChatModel 要求实现的抽象方法，用来支持 .generate 接口。
        我们内部直接调用 _call，再把结果封装成 ChatResult。
        """
        content = self._call(messages, **kwargs)
        # 用 AIMessage 封装
        ai_msg = AIMessage(content=content)
        gen = ChatGeneration(message=ai_msg)
        # ChatResult 的 generations 是 List[List[ChatGeneration]]
        return ChatResult(generations=[[gen]])

    @property
    def _llm_type(self) -> str:
        return "deepseek-chat"