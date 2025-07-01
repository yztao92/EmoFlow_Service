# rag/rag_chain.py

from rag.prompts import RAG_PROMPT
from rag.retriever import get_retriever_by_emotion
# 把旧的 llm.chat 替换成新的 zhipu_llm 接口，并映射为 chat_with_llm
from llm.zhipu_llm import zhipu_chat_llm as chat_with_llm

def run_rag_chain(emotion: str, query: str, round_index: int) -> str:
    """
    基于情绪的 RAG 流程：
      1. 按 emotion 加载对应的 Retriever
      2. 检索最相关的文档片段
      3. 将 context、emotion 和 question 注入 Prompt
      4. 调用 LLM 生成回答

    :param emotion: 当前用户情绪，如 'sad', 'happy', 'tired', 'angry'
    :param query: 用户提出的问题
    :return: LLM 生成的回答字符串
    """
    # 1) 获取按情绪分库的 Retriever，返回 top-k 片段
    retriever = get_retriever_by_emotion(emotion, k=3)
    docs = retriever.get_relevant_documents(query)

    # 调试输出检索结果
    print(f"\n🧠 [调试] 针对情绪“{emotion}”检索到文档：")
    for i, doc in enumerate(docs, 1):
        snippet = doc.page_content.replace("\n", " ")[:200]
        print(f"—— 文档段 {i} —— {snippet}…")

    # 2) 构造 Prompt，上下文及情绪一起注入
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = RAG_PROMPT.format(
        emotion=emotion,
        context=context,
        question=query,
        round_index=round_index
    )

    # 3) 调用底层 LLM 接口，它返回形如 {"answer": "..."} 的 dict
    res = chat_with_llm(prompt)
    # 如果模型在前后带了引号，这里先去掉它
    ans = res.get("answer", "")
    # 去掉英文双引号或中文书名号
    ans = ans.strip().strip('"').strip('“').strip('”')
    return ans