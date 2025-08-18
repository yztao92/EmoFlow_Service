# -*- coding: utf-8 -*-
# prompts/prompt_flow_controller.py


from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging

from prompts.chat_analysis import analyze_turn
from prompts.knowledge_retriever import retrieve_bullets
from prompts.prompt_spec import PromptSpec, map_reply_length
from prompts.chat_prompts_generator import build_final_prompt
from llm.llm_factory import chat_with_llm

# 可调参数
RAG_MIN_SIM = 0.50
TOP_K = 15


def run_prompt_flow(
    question: str,
    state_summary: str,
    round_index: int,
    memory_bullets: Optional[List[str]] = None,
    fewshots: str = "",
    history_messages: Optional[list] = None
) -> Dict[str, Any]:
    """
    新编排主流程：返回 answer + debug
    """
    # 1) LLM 分析（情绪/阶段/意图/ask_slot/pace/need_rag/...）
    ana = analyze_turn(round_index, state_summary, question)

    # 2) reply_length 决策（集中规则，符合 PDF 逻辑）
    reply_length = map_reply_length(
        stage=ana.get("stage", "暖场"),
        intent=ana.get("intent", "闲聊"),
        pace=ana.get("pace", "normal"),
    )

    # 3) 检索（可选）：把检索结果蒸馏为 bullets
    rag_bullets: List[str] = []
    if ana.get("need_rag"):
        try:
            queries = ana.get("rag_queries", []) or []
            rag_bullets = retrieve_bullets(queries, min_sim=RAG_MIN_SIM, top_k=TOP_K)
        except Exception as e:
            logging.warning(f"[prompt_flow] RAG 检索失败，继续无检索：{e}")

    # 4) 组装 PromptSpec
    spec = PromptSpec(
        emotion=ana.get("emotion", "普通"),
        stage=ana.get("stage", "暖场"),
        intent=ana.get("intent", "闲聊"),
        ask_slot=ana.get("ask_slot", "gentle"),
        pace=ana.get("pace", "normal"),
        reply_length=reply_length,
        need_rag=ana.get("need_rag", False),
        rag_queries=ana.get("rag_queries", []) or [],
        state_summary=state_summary or "",
        question=question or "",
        fewshots=fewshots or "",
        memory_bullets=memory_bullets or [],
        rag_bullets=rag_bullets or [],
        history_messages=history_messages or [],
    )

    # 5) 最终 Prompt 与生成
    final_prompt = build_final_prompt(spec)
    answer = chat_with_llm(final_prompt)

    return {
        "answer": answer,
        "debug": {
            "analysis": ana,
            "reply_length": reply_length,
            "rag_bullets": rag_bullets,
            "final_prompt_preview": final_prompt[:1200],
        },
    }


# ===== 向后兼容的旧入口 =====
def chat_once(
    question: str,
    state_summary: str = "",
    round_index: int = 1,
    memory_bullets: Optional[List[str]] = None,
    fewshots: str = "",
    history_messages: Optional[list] = None
) -> Dict[str, Any]:
    """
    兼容 main.py 的旧调用方式。
    - 入参尽量宽松，默认即可跑通
    - 返回结构与 run_prompt_flow 一致
    """
    return run_prompt_flow(
        question=question,
        state_summary=state_summary,
        round_index=round_index,
        memory_bullets=memory_bullets,
        fewshots=fewshots,
        history_messages=history_messages
    )