# prompts/prompt_flow_controller.py
import logging
from prompts.chat_prompts_generator import build_final_prompt
from llm.llm_factory import chat_with_llm
from retriever.search import retrieve  # 你已有的话就沿用

def chat_once(analysis: dict, state_summary: str, question: str) -> str:
    # 可选 RAG：只在 need_rag=True 时触发
    rag_bullets = []
    if analysis.get("need_rag"):
        try:
            docs = retrieve(analysis.get("rag_queries", []), top_k=4)
            rag_bullets = [d.snippet for d in docs]
            # 也可以把结果片段塞回 analysis.rag_queries，或单独注入到 prompt
        except Exception as e:
            logging.warning("RAG 检索失败，跳过：%s", e)

    # 拼装最终 Prompt
    final_prompt = build_final_prompt({**analysis, "rag_queries": analysis.get("rag_queries", [])}, state_summary, question)

    # 生成
    answer = chat_with_llm(final_prompt)

    # 失败回退（为空/过短时）
    if not answer or len(answer.strip()) < 4:
        # 简单回退：根据 stage 给一条保守句式
        fallback = {
            "warmup": "我在，先把这件事最重要的一点说给我听，好吗？",
            "mid":    "我先给一个可执行的小步骤：先把关键人/关键事写下来，然后选一项立刻行动。",
            "wrap":   "先到这儿。把今天的收获记一下，明天我来提醒你继续推进？",
        }
        answer = fallback.get(analysis.get("stage","mid"), fallback["mid"])
    return answer