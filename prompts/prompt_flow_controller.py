# File: prompts/prompt_flow_controller.py
import logging
from typing import List

from prompts.chat_prompts_generator import build_final_prompt
from llm.llm_factory import chat_with_llm

# ✅ 可选导入：没有检索模块也不崩
try:
    from retriever.search import retrieve  # 你已有的话就沿用
except Exception:
    logging.warning("[prompt_flow] 未找到 retriever.search.retrieve，RAG 将被禁用")
    def retrieve(queries: List[str], top_k: int = 4):
        return []

def chat_once(analysis: dict, state_summary: str, question: str) -> str:
    # —— 可选 RAG：只在 need_rag=True 时触发 —— #
    rag_bullets = []
    if analysis.get("need_rag"):
        try:
            docs = retrieve(analysis.get("rag_queries", []), top_k=4)
            rag_bullets = [getattr(d, "snippet", str(d)) for d in (docs or [])]
            # 如需把检索片段注入到 prompt，可在 build_final_prompt 中扩展
        except Exception as e:
            logging.warning("RAG 检索失败，跳过：%s", e)

    # —— 拼装最终 Prompt —— #
    import json
    logging.info("[DEBUG] analysis/ana 参数: %s", json.dumps(analysis, ensure_ascii=False, indent=2))
    logging.info("[DEBUG] state_summary: %s", state_summary)
    logging.info("[DEBUG] question: %s", question)
    try:
        final_prompt = build_final_prompt(
            {**analysis, "rag_queries": analysis.get("rag_queries", [])},
            state_summary,
            question
        )
        logging.info("[DEBUG] 最终拼接的 prompt:\n%s", final_prompt)
        logging.info("[DEBUG] final_prompt 构建成功")
    except Exception as e:
        logging.error(f"[DEBUG] build_final_prompt 报错: {e}")
        raise

    # —— 生成（稳健解包） —— #
    resp = chat_with_llm(final_prompt)
    if isinstance(resp, dict):
        answer = resp.get("answer", "")
    else:
        answer = resp

    # —— 失败回退（为空/过短时） —— #
    if not isinstance(answer, str) or len(answer.strip()) < 4:
        fallback = {
            "warmup": "我在，先把这件事最重要的一点说给我听，好吗？",
            "mid":    "我先给一个可执行的小步骤：先把关键人/关键事写下来，然后选一项立刻行动。",
            "wrap":   "先到这儿。把今天的收获记一下，明天我来提醒你继续推进？",
        }
        answer = fallback.get(analysis.get("stage", "mid"), fallback["mid"])

    return answer