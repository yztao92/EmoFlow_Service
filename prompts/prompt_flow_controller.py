# File: prompts/prompt_flow_controller.py
import logging
from typing import List
from prompts.chat_prompts_generator import build_final_prompt
from llm.llm_factory import chat_with_llm

try:
    from retriever.search import retrieve
except Exception:
    logging.warning("[prompt_flow] 未找到 retriever.search.retrieve，RAG 将被禁用")
    def retrieve(queries: List[str], top_k: int = 4):
        return []

def chat_once(analysis: dict, state_summary: str, question: str) -> str:
    # —— 可选 RAG —— #
    rag_bullets = []
    if analysis.get("need_rag"):
        try:
            docs = retrieve(analysis.get("rag_queries", []), top_k=4)
            rag_bullets = [getattr(d, "snippet", str(d)) for d in (docs or [])]
        except Exception as e:
            logging.warning("RAG 检索失败，跳过：%s", e)

    # —— 拼装最终 Prompt —— #
    import json
    logging.info("[DEBUG] analysis/ana 参数: %s", json.dumps(analysis, ensure_ascii=False, indent=2))
    logging.info("[DEBUG] state_summary: %s", state_summary)
    logging.info("[DEBUG] question: %s", question)

    final_prompt = build_final_prompt(
        {**analysis, "rag_queries": analysis.get("rag_queries", [])},
        state_summary,
        question
    )
    logging.info("[DEBUG] 最终拼接的 prompt:\n%s", final_prompt)

    # —— 生成 —— #
    resp = chat_with_llm(final_prompt)
    answer = resp.get("answer", "") if isinstance(resp, dict) else resp

    # —— 失败回退（根据 emotion_type 适配）—— #
    if not isinstance(answer, str) or len(answer.strip()) < 4:
        emotion_type = analysis.get("emotion_type", "neutral")
        fallback = {
            "tired": "我在，先休息一下，等你想说的时候我们再聊。",
            "negative": "我理解你的感受，先让情绪沉淀一下，我在这里陪着你。",
            "angry": "我听见你的愤怒了，先冷静一下，我支持你。",
            "positive": "真为你开心！想继续分享这份喜悦吗？",
            "neutral": "我在，想聊什么都可以。"
        }
        answer = fallback.get(emotion_type, fallback["neutral"])

    return answer