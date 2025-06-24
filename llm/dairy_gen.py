import os
import requests
from dotenv import load_dotenv

load_dotenv()

ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def generate_diary(messages: list[str]) -> str:
    diary_prompt = (
        "你是用户的情绪助手。请将以下用户与 AI 的对话内容整理成一篇 100 字以内的心情日记，"
        "用第一人称表达情绪体验，风格自然、真实、有情绪波动。不要出现 AI 或聊天助手等字眼。\n\n"
        "对话内容如下：\n"
        + "\n".join(messages)
    )

    payload = {
        "model": "glm-4",
        "messages": [
            {"role": "system", "content": "你是用户的情绪记录写手。"},
            {"role": "user", "content": diary_prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(ZHIPU_API_URL, json=payload, headers=headers, timeout=30)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[❌ ERROR] 日记生成失败: {e}")
        return "今天的心情有些复杂，暂时还没能整理好。"