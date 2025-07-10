# File: rag/rag_chain.py

from rag.prompts import RAG_PROMPT
from vectorstore.load_vectorstore import get_retriever_by_emotion
from llm.deepseek_wrapper import DeepSeekLLM
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np
import logging
import re


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ 嵌入模型（bge-m3 本地路径）
embedding_model = HuggingFaceEmbeddings(
    model_name="/Users/yangzhentao/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/fake123456",
    model_kwargs={"device": "cpu"},  # 改为 "cuda" 如可用
    encode_kwargs={"normalize_embeddings": True}
)

# ✅ DeepSeek LLM 实例
_deepseek = DeepSeekLLM()


def chat_with_llm(prompt: str) -> dict:
    """调用 DeepSeek 模型生成回复"""
    response_text = _deepseek._call([
        HumanMessage(role="user", content=prompt)
    ])
    return {"answer": response_text}

def clean_answer(text: str) -> str:
    """
    去除回答首尾可能存在的整段引号（包括中文双引号/英文引号/单引号）
    """
    text = text.strip()
    # 去除匹配形式："xxx"、“xxx”、'xxx'
    if re.fullmatch(r'^["“”\'].*["“”\']$', text):
        return text[1:-1].strip()
    return text

def run_rag_chain(
    emotion: str,
    query: str,
    round_index: int,
    state_summary: str,
) -> str:
    """
    RAG 主逻辑：
      - 用 query 检索 top-k 内容
      - 计算并打印相似度
      - 构造 Prompt 并调用 LLM 生成回答
    """
    k = 5 if round_index == 1 else 3

    retriever = get_retriever_by_emotion(emotion, k=k)
    docs = retriever.invoke(query)

    # 余弦相似度计算
    q_vec = np.array(embedding_model.embed_query(query))
    q_norm = np.linalg.norm(q_vec) + 1e-8
    doc_texts = [d.page_content for d in docs]
    d_vecs = np.array(embedding_model.embed_documents(doc_texts))
    d_norms = np.linalg.norm(d_vecs, axis=1) + 1e-8
    sims = (d_vecs @ q_vec) / (d_norms * q_norm)

    # 日志打印
    logging.info(f"\n🧠 [检索] 情绪={emotion}, k={k}，检索到：")
    for i, (doc, sim) in enumerate(zip(docs, sims), 1):
        snippet = doc.page_content.replace("\n", " ")[:200]
        logging.info(f"—— 文档段 {i} （情绪={doc.metadata.get('emotion')}，相似度 {sim*100:.1f}%）—— {snippet}…")

    # 构造 Prompt
    context = "\n\n".join(
        f"摘要: {doc.page_content}"
        for doc in docs
    )

    prompt = RAG_PROMPT.format(
        emotion=emotion,
        round_index=round_index,
        state_summary=state_summary,
        context=context,
        question=query
    )

    logging.info("\n💡 [使用 Prompt]---------------------------------------------------")
    logging.info(prompt)
    logging.info("💡 [End Prompt]---------------------------------------------------\n")

    # 生成回答
    res = chat_with_llm(prompt)
    raw_answer = res.get("answer", "").strip()
    answer = clean_answer(raw_answer)
    return answer