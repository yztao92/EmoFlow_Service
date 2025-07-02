# llm/zhipu_llm.py - 智谱AI LLM 调用封装

import os
import requests
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def zhipu_chat_llm(prompt: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"
    }

    payload = {
        "model": "glm-4",
        "messages": [
            {"role": "system", "content": "你是一个善解人意的情绪日记助手。"},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)
        print("🧠 Zhipu LLM 状态码:", response.status_code)
        print("🧠 Zhipu LLM 返回内容:", response.text)

        if response.status_code == 200:
            data = response.json()
            return {
                "answer": data["choices"][0]["message"]["content"].strip()
            }
        else:
            raise ValueError(f"调用失败: {response.status_code} - {response.text}")

    except Exception as e:
        print("[❌ ERROR] LLM 日记生成失败:", e)
        return {
            "answer": "生成失败"
        }