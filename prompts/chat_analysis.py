# prompts/chat_analysis.py （替换/补全关键段）
import json
import logging
from typing import Dict, Any
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
# 角色：对话分析器
输出严格 JSON，不要多余文本。

# 需要识别并给出：
- emotion: "低谷" | "普通" | "庆祝"
- stage: "暖场" | "建议" | "收尾"
- intent: "求建议" | "求安慰" | "闲聊" | "叙事" | "宣泄"
- ask_slot: "gentle" | "reflect" | "none"
- pace: "slow" | "normal" | "fast"
- need_rag: true | false
- rag_queries: string[] （若 need_rag=false 则给空数组）

# 语境
- 当前轮次: {round_index}
- 历史对话: {state_summary}
- 用户输入: {question}

# 规则提示
- 暖场阶段更少提问，优先建立安全感
- 收尾阶段不再打开新话题，避免延长
- 用户明确求建议 → intent=求建议
- 明显发泄/吐槽 → intent=宣泄
- 抑郁/痛苦突出 → emotion=低谷；庆祝/正向 → emotion=庆祝
- 仅当需要外部知识时将 need_rag=true，并写出 rag_queries（≤3条，简短）
"""

def analyze_turn(round_index:int, state_summary:str, question:str) -> Dict[str, Any]:
    payload = {
        "round_index": round_index,
        "state_summary": state_summary or "",
        "question": question or "",
    }
    raw_output = chat_with_llm(ANALYZE_PROMPT.format(**payload))

    # 兜底结构
    parsed: Dict[str, Any] = {
        "emotion": "普通",
        "stage": "暖场" if round_index <= 2 else ("建议" if round_index <= 6 else "收尾"),
        "intent": "闲聊",
        "ask_slot": "gentle",
        "pace": "normal",
        "need_rag": False,
        "rag_queries": [],
    }

    try:
        if isinstance(raw_output, str):
            parsed.update(json.loads(raw_output))
        elif isinstance(raw_output, dict):
            parsed.update(raw_output)
        else:
            logging.error("🧠 [分析] 未知类型，无法解析: %s", type(raw_output))
    except Exception as e:
        logging.error("🧠 [分析] JSON 解析失败 → %s", e, exc_info=True)

    # 轻微规则修正：反思式优先用于“建议阶段 + 求建议/叙事”
    if parsed.get("stage") == "建议" and parsed.get("intent") in ("求建议", "叙事"):
        if parsed.get("ask_slot") == "gentle":
            parsed["ask_slot"] = "reflect"

    # 保底：类型与范围
    parsed["rag_queries"] = parsed.get("rag_queries") or []
    return parsed