# chat_analysis.py
import logging
from typing import Dict, Any
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
你是对话分析器，负责分析用户与AI的对话状态，输出结构化判断，用于驱动下一轮回答的生成。

请根据以下对话内容，从 5 个维度做出判断，并以 JSON 格式返回结果：

对话历史：
{state_summary}

当前用户输入：
{question}

输出字段说明：

1. emotion_type（str）：
   当前用户的主要情绪类型。请从以下选项中选择其一：
   - "tired"：疲惫、倦怠、虚无
   - "negative"：悲伤、焦虑、痛苦、失落
   - "angry"：愤怒、委屈、不满
   - "positive"：开心、激动、满足
   - "neutral"：情绪不明显或中性表达

2. user_has_shared_reason（bool）：
   用户是否已经在对话中表达了情绪背后的原因或具体事件（如压力来源、人际矛盾、生活变故等）。

3. ai_has_given_suggestion（bool）：
   AI 是否已经在对话中提出过建议、方向、行动方案等。

4. consecutive_ai_questions（bool）：
   最近连续两轮 AI 回复是否都以问句结尾（如“你觉得是为什么？”“能说说更多吗？”）。若满足该条件，则为 true，否则为 false。

5. need_rag（bool）：
   当前生成是否需要引用外部知识或语义检索结果（RAG）以丰富信息内容。

6. rag_queries（List[str]）：
   若 `need_rag` 为 true，则输出触发检索的自然语言查询列表；若为 false，则返回空列表 `[]`。

7. should_end_conversation（bool）：
   当前是否可以自然结束对话（用户表达较完整，情绪趋于平稳，无明显继续表达意愿）。


返回格式（JSON）：
{{
  "emotion_type": "tired",
  "user_has_shared_reason"：true,
  "ai_has_given_suggestion": false,
  "consecutive_ai_questions": true,
  "need_rag": true,
  "rag_queries": ["..."]，
  "should_end_conversation": false
}}
"""

def analyze_turn(state_summary: str, question: str) -> Dict[str, Any]:
    prompt = ANALYZE_PROMPT.format(state_summary=state_summary, question=question)
    logging.info("[Prompt] 分析对话状态\n" + prompt)

    try:
        result = chat_with_llm(prompt)
        parsed = eval(result) if isinstance(result, str) else result
        return {
            "user_has_shared_reason": parsed.get("user_has_shared_reason", False),
            "ai_has_given_suggestion": parsed.get("ai_has_given_suggestion", False),
            "should_end_conversation": parsed.get("should_end_conversation", False),
            "emotion_type": parsed.get("emotion_type", "neutral"),
            "consecutive_ai_questions": parsed.get("consecutive_ai_questions", False),
            "need_rag": parsed.get("need_rag", False),
            "rag_queries": parsed.get("rag_queries", []) if parsed.get("need_rag", False) else []
        }
    except Exception as e:
        logging.error(f"[chat_analysis] 分析失败: {e}")
        return {
            "user_has_shared_reason": False,
            "ai_has_given_suggestion": False,
            "should_end_conversation": False,
            "emotion_type": "neutral",
            "consecutive_ai_questions": False,
            "need_rag": False,
            "rag_queries": []
        }