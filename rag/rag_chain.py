# File: rag/rag_chain.py

from rag.prompts import RAG_PROMPT
from vectorstore.load_vectorstore import get_retriever_by_emotion
from llm.deepseek_wrapper import DeepSeekLLM
from llm.zhipu_embedding import ZhipuEmbedding
from langchain_core.messages import HumanMessage
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# 实例化嵌入模型，用于相似度计算
_embedding = ZhipuEmbedding()

# 实例化 DeepSeek LLM
_deepseek = DeepSeekLLM()

def chat_with_llm(prompt: str) -> dict:
    """
    使用 DeepSeek LLM 生成回答，返回 dict 格式
    """
    response_text = _deepseek._call([
        HumanMessage(role="user", content=prompt)
    ])
    return {"answer": response_text}


def run_rag_chain(
    emotion: str,
    query: str,
    round_index: int,
    state_summary: str,
    brief_summary: str,    # 新增参数，主线摘要
) -> str:
    """
    基于情绪和对话状态的 RAG 流程：
      1. 按 emotion 分库检索 top-k 文档（用 brief_summary 作为检索Query）
      2. 计算并打印余弦相似度
      3. 构造包含对话状态的 Prompt
      4. 打印 Prompt 并调用 LLM

    :param emotion: 用户当前情绪，如 'sad', 'happy', 'tired', 'angry'
    :param query: 用户最新提问
    :param round_index: 对话轮次
    :param state_summary: 最近对话和干预的状态摘要（Prompt用）
    :param brief_summary: LLM生成的主线摘要（检索用）
    :return: 生成的回答
    """
    # 动态设置 k: 首轮 5 条，后续 3 条
    k = 5 if round_index == 1 else 3

    # 1) 用 brief_summary 检索（如无则降级用 query）
    retriever = get_retriever_by_emotion(emotion, k=k)
    effective_query = brief_summary.strip() or query.strip()
    docs = retriever.invoke(effective_query)

    # 2) 计算相似度（此处用检索用的 effective_query）
    q_vec = np.array(_embedding.embed_query(effective_query))
    q_norm = np.linalg.norm(q_vec) + 1e-8
    doc_texts = [d.page_content for d in docs]
    d_vecs = np.array(_embedding.embed_documents(doc_texts))
    d_norms = np.linalg.norm(d_vecs, axis=1) + 1e-8
    sims = (d_vecs @ q_vec) / (d_norms * q_norm)

    # 3) 打印检索日志
    logging.info(f"\n🧠 [检索] 情绪={emotion}, k={k}，检索到：")
    for i, (doc, sim) in enumerate(zip(docs, sims), 1):
        snippet = doc.page_content.replace("\n", " ")[:200]
        logging.info(f"—— 文档段 {i} （情绪={doc.metadata.get('emotion')}，相似度 {sim*100:.1f}%）—— {snippet}…")

    # 4) 构造 Prompt，仍然注入 state_summary
    context = "\n\n".join(
        f"摘要: {doc.page_content}\n原文: {doc.metadata.get('content', '')}"
        for doc in docs
    )

    prompt = RAG_PROMPT.format(
        emotion=emotion,
        round_index=round_index,
        state_summary=state_summary,
        context=context,
        question=query
    )

    # 5) 打印实际使用的 Prompt
    logging.info("\n💡 [使用 Prompt]---------------------------------------------------")
    logging.info(prompt)
    logging.info("💡 [End Prompt]---------------------------------------------------\n")

    # 6) 调用 LLM
    res = chat_with_llm(prompt)
    answer = res.get("answer", "").strip().strip('"').strip('"').strip('"')
    return answer