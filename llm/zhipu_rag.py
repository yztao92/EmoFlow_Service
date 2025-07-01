# llm/zhipu_rag.py
import os
import requests
from dotenv import load_dotenv
from vectorstore.load_vectorstore import get_retriever_by_emotion

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def zhipu_chat_rag(query: str, category: str = "default") -> dict:
    # round_index 如果从外层传入，可按需调整 K
    k = 3
    retriever = get_retriever_by_emotion(category, k=k)  
    docs = retriever.invoke(query)

    # ✅ 只保留纯文本内容
    references = [doc.page_content.strip() for doc in docs]

    # ✅ 构造上下文
    context = "\n\n".join(references)

    system_prompt = (
    "你是一个温柔、有同理心的情绪陪伴助手。\n"
    "当用户表达情绪（比如“我好烦”“我很难过”）时，先表达理解和支持，用简单温暖的语言回应。\n"
    "如果用户愿意说出具体原因，请在表达共情后，适度给予建设性的引导或建议，例如如何看待问题、调整状态、采取小行动等。\n"
    "建议要简洁、现实、有同理心，不要空泛，也不要强行乐观。\n"
    "每次回答最多不超过3句话，保持自然、有温度的语气。\n"
    "不需要说明你是 AI，直接自然说话就好。\n"
    "-----------\n"
    f"{context}\n"
    "-----------"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"
    }

    payload = {
        "model": "glm-4",
        "messages": messages
    }

    response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        answer = response.json()["choices"][0]["message"]["content"]

        # ✅ 简洁日志：引用数量 + 每条预览（最多前80字）
        print(f"\n📚 [引用片段总数] {len(references)}")
        for i, ref in enumerate(references):
            preview = ref.replace("\n", "").strip()[:80]
            print(f" - [{i+1}] {preview}...")

        return {
            "answer": answer,
            "references": references
        }
    else:
        raise Exception(f"请求失败: {response.status_code}, {response.text}")