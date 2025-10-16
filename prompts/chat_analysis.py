# chat_analysis.py
import logging
import json
from typing import Dict, Any
from llm.llm_factory import chat_with_llm
import re

ANALYZE_PROMPT = """
你是对话分析器，负责分析用户与AI的对话状态。请仔细阅读整个对话历史，准确判断当前状态。

## 分析步骤
1. 通读对话历史，理解用户情绪发展
2. 重点关注用户最新表达与整体情绪倾向  
3. 分析AI的回复方式与行为特点
4. 基于以上分析做出准确判断

## 对话历史：
{state_summary}

## 当前用户输入：
{question}

## 相关搜索信息：
{cached_search_info}

# 一、情绪状态分析

## 1. emotion_type（必选其一）：
识别用户在整个对话中的主要情绪倾向：
- "tired"：表达疲惫、倦怠、虚无、没力气
- "negative"：表达悲伤、焦虑、痛苦、失落、难过
- "angry"：表达愤怒、委屈、不满、被冒犯
- "positive"：表达开心、激动、满足、兴奋
- "neutral"：情绪不明显或真正的中性表达

**提示**：忽略客套话，识别真实情绪表达

# 二、对话内容分析

## 2. user_has_shared_reason（bool）：
用户是否已说明具体情绪原因或事件？

**提示**：是否包含明确人事时地物，而非仅描述情绪状态

**示例对比**：
- True："女友不关心我"、"考试失败"、"和同事吵架了"
- False："我很难过"、"情绪低落"、"不开心"

## 3. ai_has_given_suggestion（bool）：
AI是否已提供具体建议或行动方案？

**提示**：是否出现行动性建议，而非情绪回应或询问

**示例对比**：
- True："试着沟通一下"、"可以写日记"、"建议你休息一下"
- False："我理解你的感受"、"你想说说原因吗？"

# 三、实时信息检索需求分析

## 4. need_live_search（bool）：
当前对话是否需要查询实时信息？

**判断流程**：
1. 首先检查上面的"相关搜索信息"是否已经包含用户需要的信息
2. 如果已有信息能满足用户需求，则不需要新的搜索
3. 如果已有信息不足或过时，且用户问题涉及**外部事实、新闻、状态**等实时信息时，才需搜索

**提示**：仅出现"今天""现在"等词不足以判断为 True，还需判断是否为信息查询类问题。

**示例**：
- True："今天股市怎么样"（且上面没有相关股市信息）
- False："今天股市怎么样"（但上面已有最新的股市信息）
- False："我今天很难过"、"我最近很焦虑"

## 5. has_timeliness_requirement（bool）：
检索信息是否具备时效性要求？

**提示**：出现"现在""今天""刚刚""最新"即为 True

**示例**：
- True："今天天气如何"、"最近的新闻"
- False："什么是CBT"、"如何缓解焦虑"

## 6. live_search_queries（List[str]）：
若 need_live_search 为 True，列出搜索关键词，否则返回空数组。
不要直接用用户原话作为搜索关键词，而是要根据用户原话进行总结，生成一个最精准的搜索关键词。

**要求**：
- 提供 1 个最精准的搜索关键词
- **严格禁止**：关键词中绝对不能包含任何时间相关词汇，包括但不限于：
  - 时间词："今天"、"当前"、"现在"、"最新"、"最近"
  - 日期词："2025年"、"9月5日"、"今日"、"现在"
  - 其他时间表达："目前"、"眼下"、"此时"
- 系统会自动添加时效性前缀，你只需要提供纯粹的主题关键词

# 四、知识补充需求分析

## 7. need_rag（bool）：
当前对话是否涉及心理知识补充？

**提示**：用户提问涉及专业心理知识、治疗方式、技巧建议等

**示例**：
- True："如何缓解焦虑"、"认知行为疗法是什么"
- False："我感觉低落"、"我想找人聊聊"

## 8. rag_queries（List[str]）：
若 need_rag 为 True，生成对话历史与当前用户输入的摘要，否则返回空数组

**要求**：
- 提供 1 句话摘要，包含用户问题背景和核心需求
- 摘要应涵盖历史对话和用户最新输入的整体情况
- 示例："用户因工作压力大感到焦虑，询问如何缓解焦虑情绪"

# 五、对话流程控制

## 9. should_end_conversation（bool）：
当前话题是否已完整、用户无延续意愿？

**约束**：若当前对话轮数 ≤3，**必须为 False**

**提示**：用户表达感谢、释放、暂停倾向，可判断结束  
**示例**：
- True："谢谢你的陪伴"、"我感觉好多了"、"我想先静一静"
- False："我现在感觉到平和"、"我想找人聊聊"

## 返回格式（严格JSON）：
{{
  "emotion_type": "negative",
  "user_has_shared_reason": true,
  "ai_has_given_suggestion": false,
  "need_live_search": false,
  "has_timeliness_requirement": false,
  "live_search_queries": [],
  "need_rag": false,
  "rag_queries": ["用户因工作压力大感到焦虑，询问如何缓解焦虑情绪"],
  "should_end_conversation": false
}}

**当前对话轮数**：第 {round_index} 轮

请按以上标准逐项判断，严格返回 JSON 结构结果。
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

def analyze_turn(state_summary: str, question: str, round_index: int = 1, session_id: str = None) -> Dict[str, Any]:
    # 获取缓存的搜索信息
    cached_search_info = ""
    if session_id:
        try:
            from llm.search_cache import get_cached_search_results
            cached_results = get_cached_search_results(session_id)
            if cached_results:
                # 格式化缓存信息
                search_items = []
                for result in cached_results[-3:]:  # 只取最近3次搜索
                    search_items.append(f"• 查询：{result['query']}\n• 结果：{result['result']}")
                cached_search_info = "\n\n".join(search_items)
                logging.info(f"[chat_analysis] 已加载 {len(cached_results)} 条缓存搜索信息")
        except Exception as e:
            logging.warning(f"[chat_analysis] 获取缓存搜索信息失败: {e}")
    
    prompt = ANALYZE_PROMPT.format(
        state_summary=state_summary, 
        question=question, 
        round_index=round_index,
        cached_search_info=cached_search_info
    )
    
    # 调试：打印完整的分析prompt（已禁用）
    # logging.info("=" * 80)
    # logging.info("📋 CHAT_ANALYSIS 完整Prompt")
    # logging.info("=" * 80)
    # logging.info(prompt)
    # logging.info("=" * 80)

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
            "live_search_queries": parsed.get("live_search_queries", []) if parsed.get("need_live_search", False) else [],
            "has_timeliness_requirement": parsed.get("has_timeliness_requirement", False)
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
        logging.info(f"时效性要求: {analysis_result['has_timeliness_requirement']}")
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
            "live_search_queries": [],
            "has_timeliness_requirement": False
        }