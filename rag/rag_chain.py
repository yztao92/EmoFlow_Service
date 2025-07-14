# File: rag/rag_chain.py

from rag.prompt_router import route_prompt_by_emotion
from llm.emotion_detector import detect_emotion
from rag.prompts import PROMPT_MAP
from vectorstore.load_vectorstore import get_retriever_by_emotion
from llm.deepseek_wrapper import DeepSeekLLM
from llm.embedding_factory import get_embedding_model
from langchain_core.messages import HumanMessage
import numpy as np
import logging
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

embedding_model = get_embedding_model()
_deepseek = DeepSeekLLM()

def chat_with_llm(prompt: str) -> dict:
    response_text = _deepseek._call([
        HumanMessage(role="user", content=prompt)
    ])
    return {"answer": response_text}

def clean_answer(text: str) -> str:
    text = text.strip()
    if re.fullmatch(r'^["“”\'].*["“”\']$', text):
        return text[1:-1].strip()
    return text

def run_rag_chain(
    query: str,
    round_index: int,
    state_summary: str,
) -> str:
    """
    RAG 主逻辑：
      - 自动识别情绪并选择 prompt 风格
      - 用 query 检索 top-k 内容
      - 构造 Prompt 并调用 LLM 生成回答
    """
    # 自动情绪识别 + prompt 路由
    emotion = detect_emotion(query)
    prompt_key = route_prompt_by_emotion(emotion)
    prompt_template = PROMPT_MAP.get(prompt_key, PROMPT_MAP["default"])
    logging.info(f"[Prompt 路由] 使用 prompt_key: {prompt_key}")  # 🟢 打印使用的模版 key


    # 检索内容
    k = 5 if round_index == 1 else 3
    retriever = get_retriever_by_emotion(emotion, k=k)

    start_time = time.time()
    docs = retriever.invoke(query)
    retrieve_duration = time.time() - start_time
    logging.info(f"⏱️ [检索耗时] {retrieve_duration:.2f} 秒")

    # 相似度
    q_vec = np.array(embedding_model.embed_query(query))
    q_norm = np.linalg.norm(q_vec) + 1e-8
    doc_texts = [d.page_content for d in docs]
    d_vecs = np.array(embedding_model.embed_documents(doc_texts))
    d_norms = np.linalg.norm(d_vecs, axis=1) + 1e-8
    sims = (d_vecs @ q_vec) / (d_norms * q_norm)

    logging.info(f"\n🧠 [检索] 情绪={emotion}, prompt={prompt_key}, k={k}")
    for i, (doc, sim) in enumerate(zip(docs, sims), 1):
        snippet = doc.page_content.replace("\n", " ")[:200]
        logging.info(f"—— 文档段 {i} （情绪={doc.metadata.get('emotion')}，相似度 {sim*100:.1f}%）—— {snippet}…")

    context = "\n\n".join(
        f"摘要: {doc.page_content}\n原文: {doc.metadata.get('content', '')[:300]}"
        for doc in docs
    )

    prompt = prompt_template.format(
        emotion=emotion,
        round_index=round_index,
        state_summary=state_summary,
        context=context,
        question=query
    )

    logging.info("\n💡 [使用 Prompt]---------------------------------------------------")
    logging.info(prompt)
    logging.info("💡 [End Prompt]---------------------------------------------------\n")

    res = chat_with_llm(prompt)
    raw_answer = res.get("answer", "").strip()
    answer = clean_answer(raw_answer)
    return answer
