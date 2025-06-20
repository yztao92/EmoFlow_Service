# rag/rag_chain.py

from rag.prompts import RAG_PROMPT
from rag.retriever import retriever
from llm.chat import chat_with_llm

def run_rag_chain(query: str) -> str:
    # Step 1: 检索文档
    docs = retriever.get_relevant_documents(query)

    print("\n🧠 [调试] 检索到文档如下：")
    for i, doc in enumerate(docs):
        print(f"—— 文档段 {i+1} ——")
        print(doc.page_content[:200])  # 显示前200字

    # Step 2: 构造 Prompt
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = RAG_PROMPT.format(context=context, question=query)

    # Step 3: 调用 LLM
    response = chat_with_llm(prompt)
    return response