import os
import requests
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def zhipu_chat_rag(query: str, retriever) -> str:
    # 1. 检索相关文档
    docs = retriever.invoke(query)
    context = "\n\n".join([doc.page_content for doc in docs])

    # 2. 构造带 context 的 prompt
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

    # 3. 发起对话请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"}
    payload = {
        "model": "glm-4",
        "messages": messages
    }

    response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)

    # 4. 返回处理
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"请求失败: {response.status_code}, {response.text}")