# llm/zhipu_rag.py
import os
import requests
from dotenv import load_dotenv
from vectorstore.load_vectorstore import get_retriever

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def zhipu_chat_rag(query: str, category: str = "default") -> dict:
    retriever = get_retriever(category)
    docs = retriever.invoke(query)

    # ✅ 只保留纯文本内容
    references = [doc.page_content.strip() for doc in docs]

    # ✅ 构造上下文
    context = "\n\n".join(references)

    system_prompt = (
        "你是一个情绪陪伴助手，以下是与你知识库相关的内容，请基于此回答用户问题。\n"
        "如果知识库中没有提到相关内容，可以结合常识简要补充。\n"
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