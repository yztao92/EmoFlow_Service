# prompts/chat_analysis.py
import json
import logging
from typing import Dict, Any
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
你是对话分析器，负责分析用户对话内容并输出结构化分析结果。

## 分析字段说明

### emotion (用户的情绪)
- "低谷": 用户表达悲伤、痛苦、绝望、抑郁等负面情绪
- "普通": 用户情绪平和，正常聊天状态
- "庆祝": 用户表达开心、兴奋、满足、幸福等正面情绪

### stage (对话阶段分析)
- "暖场": 对话刚开始，需要建立氛围和信任
- "建议": 对话中期，可以给出建设性建议
- "收尾": 对话后期，自然收束，避免过度深入

### context_type (对话类型)
- "求建议": 用户明确需要解决方案或建议
- "求安慰": 用户寻求情感支持和理解
- "闲聊": 日常聊天，无特殊需求
- "玩梗": 用户开玩笑或使用幽默表达
- "其他": 不属于以上类型的对话

### ask_slot (提问策略)
- "gentle": 温和引导，用共鸣、分享或轻描淡写的方式引导用户自然说出更多，避免直接提问
- "active": 主动提问，直接询问用户相关细节或感受


### need_empathy (是否需要共情)
- true: 用户情绪低落、寻求安慰、表达痛苦、需要情感支持时
- false: 用户情绪平和、闲聊、分享日常、情绪稳定时

### need_rag (是否需要知识检索)
- true: 用户问题需要专业知识或建议支持
- false: 纯情感交流，无需额外知识

### queries (检索查询短语)
- 当need_rag=true时，提供2-4个检索关键词
- 每个短语6-12字，用于知识库检索

## 输出要求
仅输出JSON格式，不要包含任何其他文字。

## 分析输入
轮次: {round_index}
历史对话: {state_summary}
用户输入: {question}

上轮是否已提问: {last_turn_had_question}
"""

def _normalize_queries(qlist):
    """把 queries 统一为 [{'q': str, 'weight': 1.0}, ...]"""
    if not isinstance(qlist, list):
        return []
    out = []
    for q in qlist:
        if isinstance(q, str):
            qs = q.strip()
            if qs:
                out.append({"q": qs, "weight": 1.0})
        elif isinstance(q, dict) and isinstance(q.get("q"), str):
            qs = q["q"].strip()
            if qs:
                w = q.get("weight", 1.0)
                try:
                    w = float(w)
                except Exception:
                    w = 1.0
                out.append({"q": qs, "weight": w})
        elif isinstance(q, dict) and isinstance(q.get("q"), dict):
            # 如果q["q"]也是字典，跳过这个元素
            logging.warning(f"🧠 [分析] 跳过嵌套字典查询: {q}")
            continue
    return out

def analyze_turn(
    round_index:int,
    state_summary:str,
    question:str,
    last_turn_had_question:str="no"
) -> Dict[str, Any]:

    prompt = ANALYZE_PROMPT.format(
        round_index=round_index,
        state_summary=state_summary,
        question=question,
        last_turn_had_question=last_turn_had_question
    )

    logging.info("🧠 [分析] 入参 → round=%s, question=%s", round_index, question)
    logging.info("🧠 [分析] Prompt ↓\n%s", prompt)

    res = chat_with_llm(prompt)  # 约定返回 {"answer": "..."}
    raw_output = res.get("answer", "")

    # 默认兜底结构
    parsed = {
        "mode": "普通",
        "stage": "暖场",
        "context_type": "闲聊",
        "ask_slot": "gentle",  # 默认使用温和引导，避免直接提问
        "need_empathy": False,
        "need_rag": False,
        "queries": []
    }

    # 解析 LLM JSON（失败就用兜底）
    try:
        parsed.update(json.loads(raw_output))
    except Exception as e:
        logging.error("🧠 [分析] JSON 解析失败 → %s", e, exc_info=True)

    # 规范化 queries
    parsed["queries"] = _normalize_queries(parsed.get("queries", []))

    logging.info("🧠 [分析] 结构化结果 ↓\n%s", json.dumps(parsed, ensure_ascii=False, indent=2))
    return parsed