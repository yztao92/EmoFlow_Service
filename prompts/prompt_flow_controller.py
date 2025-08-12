# prompts/prompt_flow_controller.py
import os
from typing import Dict, Any, List
from prompts.chat_analysis import analyze_turn
from prompts.knowledge_retriever import retrieve_bullets
from prompts.chat_prompts_generator import generate_reply

USE_NEW_PIPE = os.getenv("USE_NEW_RAG_PIPE", "1") == "1"
RAG_MIN_SIM = float(os.getenv("RAG_MIN_SIM", "0.50"))
RAG_ONLY_ON_STAGE = os.getenv("RAG_ONLY_ON_STAGE", "建议")

def _legacy_generate(question: str, state_summary: str, round_index: int) -> str:
    return "（旧链路占位输出）"

def _safe_get(d, k, default=None):
    return d.get(k, default) if isinstance(d, dict) else default

def chat_once(
    question: str,
    round_index: int,
    state_summary: str,
    last_turn_had_question: str = "no",
    memory_bullets: str = "",
    fewshots: str = "",
    emotion: str = "",   # 可选：透传给生成步
) -> Dict[str, Any]:
    if not USE_NEW_PIPE:
        ans = _legacy_generate(question, state_summary, round_index)
        return {"answer": ans, "debug": {"pipe": "legacy"}}

    # Step 1: 分析
    try:
        ana = analyze_turn(
            round_index=round_index,
            state_summary=state_summary,
            question=question,
            last_turn_had_question=last_turn_had_question,
        )
    except Exception:
        ana = {"mode":"普通","stage":"暖场","context_type":"闲聊",
               "ask_slot":True,"need_rag":False,"queries":[],
               "points":["接住对方","一句轻回应"]}

    # Step 1.5: 检索（受 need_rag & 阶段控制）
    rag_bullets: List[str] = []
    stage = _safe_get(ana, "stage", "")
    allowed_stages = [s.strip() for s in RAG_ONLY_ON_STAGE.split(",") if s.strip()]
    if _safe_get(ana, "need_rag", False) and (stage in allowed_stages):
        rag_bullets = retrieve_bullets(_safe_get(ana, "queries", []))

    # 兜底 - 确保 ask_slot 有值
    if not _safe_get(ana, "ask_slot"):
        ana["ask_slot"] = "gentle"

    # Step 2: 生成
    answer = generate_reply(
        ana=ana,
        rag_bullets=rag_bullets,
        state_summary=state_summary,
        question=question,
        fewshots=fewshots,
        memory_bullets=memory_bullets,
        # emotion=emotion,  # 若你的 generator 支持这个参数就打开
    )

    return {
        "answer": answer,
        "debug": {
            "pipe": "new",
            "ana": ana,
            "rag_bullets": rag_bullets,
            "threshold": RAG_MIN_SIM,
        },
    }

