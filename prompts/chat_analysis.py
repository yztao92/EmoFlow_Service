# chat_analysis.py
import logging
import json
from typing import Dict, Any
from llm.llm_factory import chat_with_llm
import re

ANALYZE_PROMPT = """
你是对话分析器，负责分析用户与AI的对话状态。请仔细阅读整个对话历史，准确判断当前状态。

## 分析步骤
1. 首先通读整个对话历史，理解用户情绪发展轨迹
2. 重点关注用户的最新表达和整体情绪倾向  
3. 分析AI回复的模式和特点
4. 基于以上分析做出准确判断

## 对话历史：
{state_summary}

## 当前用户输入：
{question}

## 已搜索内容：
{searched_content}

## 判断维度和标准：

### 1. emotion_type（必选其一）：
分析用户在整个对话中表现出的**主要情绪倾向**：
- "tired"：表达疲惫、倦怠、虚无、没力气
- "negative"：表达悲伤、焦虑、痛苦、失落、难过
- "angry"：表达愤怒、委屈、不满、被冒犯
- "positive"：表达开心、激动、满足、兴奋
- "neutral"：情绪不明显或真正的中性表达


### 2. user_has_shared_reason（bool）：
用户是否已经说出了**具体的情绪原因或事件**？

**判断标准**：
- True：用户说出了具体的人、事、物、时间、地点、事件等具体信息
- False：用户只表达了情绪状态，没有具体内容"

**关键判断点**：看是否包含具体的人名、事件、时间、地点、对象等具体信息，而不是仅仅描述情绪状态

### 3. ai_has_given_suggestion（bool）：
AI是否已经提出过**具体的建议或行动方案**？

**判断标准**：
- True：AI给出了具体的行动建议、解决方案或操作指导
- False：AI只是询问、共情、倾听，没有给出行动建议


### 4. consecutive_ai_questions（bool）：
检查AI的**最近连续三轮回复**是否都以问句结尾：

**判断标准**：
- True：AI最近连续三轮回复都以问句结尾（如"吗？"、"呢？"、"什么？"等）
- False：AI回复少于三轮，或者三轮中有一轮不是问句结尾

### 5. need_rag（bool）：
当前是否需要引用外部知识？

**判断标准**：
- True：涉及专业知识、事实信息、技巧方法、具体建议等需要外部知识支持的内容
- False：纯情感陪伴对话，不需要专业知识

**具体示例**：
- True：用户询问"如何缓解焦虑"、"抑郁症的症状有哪些"、"冥想的具体步骤"
- False：用户表达"我今天心情不好"、"我很难过"、"我想找人聊聊"

### 6. rag_queries（List[str]）：
如果need_rag为True，列出检索查询词，否则返回空数组[]

**要求**：
- 如果need_rag为True，提供2-4个相关的检索关键词
- 如果need_rag为False，返回空数组[]

### 7. need_live_search（bool）：
当前是否需要实时搜索信息？

**判断标准**：
- True：涉及实时信息、最新动态、当前状态等需要搜索的内容
- False：不需要实时信息的对话

**重要提醒**：请先查看上面"已搜索内容"部分，如果已有相关信息能满足用户需求，则不需要重复搜索。

### 8. live_search_queries（List[str]）：
如果need_live_search为True，列出搜索查询词，否则返回空数组[]

**要求**：
- 如果need_live_search为True，只提供1个最精准的搜索关键词
- 如果need_live_search为False，返回空数组[]
- 严禁提供多个搜索词，只允许1个！

**查询词优化原则**：
- 必须包含具体日期：如"9月2日"、"今天"、"今日"
- 优先使用用户原话中的关键词
- 查询词要简洁明了，不超过8个字
- 选择最核心、最重要的关键词


### 9. should_end_conversation（bool）：
对话内容是否已经趋于完整，且用户没有主动延续话题的意愿？

**重要约束**：如果当前对话轮数 ≤ 3，则此值必须为 False！

**判断标准**：
- True：用户已经充分表达了当前话题，情绪趋于稳定，没有提出新问题或延续话题的意愿
- False：用户还在表达过程中，或者有明显想要继续分享、讨论的意愿

**具体表现**：
- True：用户说"谢谢你的陪伴"、"我感觉好多了"、"我想先静一静"
- False：用户说"我现在感觉到平和"、"我心情不错"、"我有点累"、"我想找人聊聊"


## 返回格式（严格JSON）：
{{
  "emotion_type": "negative",
  "user_has_shared_reason": true,
  "ai_has_given_suggestion": false,
  "consecutive_ai_questions": true,
  "need_rag": false,
  "rag_queries": [],
  "need_live_search": false,
  "live_search_queries": [],
  "should_end_conversation": false
}}

**重要提醒**：live_search_queries 数组最多只能包含1个元素！

**当前对话轮数**：第 {round_index} 轮

请基于上述标准进行分析，确保判断准确：
"""


def is_question_ending(text: str) -> bool:
    """判断文本是否以问句结尾"""
    if not text or not isinstance(text, str):
        return False
    
    # 清理文本，去除多余空格
    cleaned_text = text.strip()
    
    # 定义问句结尾模式
    question_endings = ['吗？', '呢？', '什么？', '吧？', '如何？', '？', '?']
    
    # 检查是否以问句结尾
    return any(cleaned_text.endswith(ending) for ending in question_endings)

def check_consecutive_questions(conversation_history: str) -> bool:
    """检查是否连续三轮AI回复都以问句结尾"""
    if not conversation_history:
        return False
    
    # 解析对话历史，提取AI回复
    ai_messages = []
    lines = conversation_history.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('• AI: '):
            # 提取AI回复内容
            content = line[6:].strip()  # 去掉 "• AI: " 前缀
            ai_messages.append(content)
    
    # 如果AI回复少于三轮，返回False
    if len(ai_messages) < 3:
        return False
    
    # 检查最近三轮AI回复是否都以问句结尾
    recent_three = ai_messages[-3:]
    
    for message in recent_three:
        if not is_question_ending(message):
            return False
    
    return True

def analyze_turn(state_summary: str, question: str, round_index: int = 1, searched_content: str = "") -> Dict[str, Any]:
    prompt = ANALYZE_PROMPT.format(state_summary=state_summary, question=question, searched_content=searched_content, round_index=round_index)
    
    # 不再打印分析prompt，只显示分析结果

    try:
        result = chat_with_llm(prompt)
        
        # 处理 LLM 返回的 Markdown 格式 JSON
        if isinstance(result, str):
            json_content = result.strip()
            
            # 如果被 ```json 和 ``` 包围，提取中间内容
            if json_content.startswith('```json') and json_content.endswith('```'):
                json_content = json_content[7:-3].strip()  # 移除 ```json 和 ```
            elif json_content.startswith('```') and json_content.endswith('```'):
                json_content = json_content[3:-3].strip()  # 移除 ``` 和 ```
            
            try:
                parsed = json.loads(json_content)
            except json.JSONDecodeError as je:
                logging.error(f"[chat_analysis] JSON 解析失败: {je}")
                logging.error(f"[chat_analysis] 尝试解析的内容: {json_content[:200]}...")
                raise ValueError(f"LLM 返回的不是有效 JSON: {json_content[:100]}")
        else:
            parsed = result
            
        # 使用本地判断连续问句，替代LLM判断
        consecutive_ai_questions = check_consecutive_questions(state_summary)
        
        # 添加调试日志
        logging.info(f"[本地判断] consecutive_ai_questions: {consecutive_ai_questions}")
        logging.info(f"[本地判断] 对话历史: {state_summary}")
        
        # 格式化显示分析结果
        analysis_result = {
            "user_has_shared_reason": parsed.get("user_has_shared_reason", False),
            "ai_has_given_suggestion": parsed.get("ai_has_given_suggestion", False),
            "should_end_conversation": parsed.get("should_end_conversation", False),
            "emotion_type": parsed.get("emotion_type", "neutral"),
            "consecutive_ai_questions": consecutive_ai_questions,  # 使用本地判断
            "need_rag": parsed.get("need_rag", False),
            "rag_queries": parsed.get("rag_queries", []) if parsed.get("need_rag", False) else [],
            "need_live_search": parsed.get("need_live_search", False),
            "live_search_queries": parsed.get("live_search_queries", []) if parsed.get("need_live_search", False) else []
        }
        
        # 格式化显示分析结果
        logging.info("=" * 50)
        logging.info("📊 CHAT_ANALYSIS 分析结果")
        logging.info("=" * 50)
        logging.info(f"情绪类型: {analysis_result['emotion_type']}")
        logging.info(f"已分享原因: {analysis_result['user_has_shared_reason']}")
        logging.info(f"AI已给建议: {analysis_result['ai_has_given_suggestion']}")
        logging.info(f"连续问句: {analysis_result['consecutive_ai_questions']}")
        logging.info(f"需要RAG: {analysis_result['need_rag']}")
        logging.info(f"需要实时搜索: {analysis_result['need_live_search']}")
        logging.info(f"对话应结束: {analysis_result['should_end_conversation']}")
        if analysis_result['need_rag']:
            logging.info(f"RAG查询词: {analysis_result['rag_queries']}")
        if analysis_result['need_live_search']:
            logging.info(f"实时搜索查询词: {analysis_result['live_search_queries']}")
        logging.info("=" * 50)
        
        return analysis_result
    except Exception as e:
        logging.error(f"[chat_analysis] 分析失败: {e}")
        return {
            "user_has_shared_reason": False,
            "ai_has_given_suggestion": False,
            "should_end_conversation": False,
            "emotion_type": "neutral",
            "consecutive_ai_questions": False,
            "need_rag": False,
            "rag_queries": [],
            "need_live_search": False,
            "live_search_queries": []
        }