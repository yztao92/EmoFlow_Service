# chat_analysis.py
import logging
import json
from typing import Dict, Any
from llm.llm_factory import chat_with_llm

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

## 判断维度和标准：

### 1. emotion_type（必选其一）：
分析用户在整个对话中表现出的**主要情绪倾向**：
- "tired"：表达疲惫、倦怠、虚无、没力气
- "negative"：表达悲伤、焦虑、痛苦、失落、难过
- "angry"：表达愤怒、委屈、不满、被冒犯
- "positive"：表达开心、激动、满足、兴奋
- "neutral"：情绪不明显或真正的中性表达

**判断要点**：
- 看用户用词：如"悲伤"、"不好"、"难受" → negative
- 看情境：如失恋、被忽视、关系问题 → negative  
- 不要被客套话误导，关注真实情感表达

### 2. user_has_shared_reason（bool）：
用户是否已经说出了**具体的情绪原因**？
- True示例：说出了"女友不关心我"、"工作压力大"、"考试失败"等具体事件
- False示例：只说"心情不好"、"很累"、"不开心"但没说为什么

### 3. ai_has_given_suggestion（bool）：
AI是否已经提出过**具体的建议或行动方案**？
- True示例：建议"试着沟通"、"休息一下"、"寻求帮助"等
- False示例：只是询问、共情、倾听，没有给出行动建议

### 4. consecutive_ai_questions（bool）：
检查AI的**最近连续两轮回复**是否都以问句结尾：
- 仔细数AI回复中的问句：如"吗？"、"呢？"、"什么？"
- **重要**：必须要有连续两轮AI回复，且这两轮都以问句结尾，才为True
- 如果只有一轮AI回复，或者两轮中有一轮不是问句，则为False
- 示例：如果AI回复了"你好吗？"然后"今天天气怎么样？" → True
- 示例：如果AI只回复了"你好吗？" → False

### 5. need_rag（bool）：
当前是否需要引用外部知识？
- 涉及专业知识、事实信息、技巧方法时为True
- 纯情感陪伴对话一般为False

### 6. rag_queries（List[str]）：
如果need_rag为True，列出检索查询词，否则返回空数组[]

### 7. should_end_conversation（bool）：
用户是否表达完整，情绪趋于平稳，无明显继续表达意愿？

## 分析示例
对于情绪判断，请特别注意：
- 用户说"悲伤"、"难受"、"不好" → emotion_type应该是"negative"
- 用户说"很累"、"没劲" → emotion_type应该是"tired"  
- 用户说"生气"、"愤怒" → emotion_type应该是"angry"

## 返回格式（严格JSON）：
{{
  "emotion_type": "negative",
  "user_has_shared_reason": true,
  "ai_has_given_suggestion": false,
  "consecutive_ai_questions": true,
  "need_rag": false,
  "rag_queries": [],
  "should_end_conversation": false
}}

请基于上述标准进行分析，确保判断准确：
"""

def analyze_turn(state_summary: str, question: str) -> Dict[str, Any]:
    prompt = ANALYZE_PROMPT.format(state_summary=state_summary, question=question)
    logging.info("[Prompt] 分析对话状态\n" + prompt)

    try:
        result = chat_with_llm(prompt)
        print(f"[DEBUG] LLM 原始返回结果: {repr(result)}")
        print(f"[DEBUG] 返回结果类型: {type(result)}")
        
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
                print(f"[DEBUG] JSON 解析失败: {je}")
                print(f"[DEBUG] 尝试解析的内容: {json_content[:200]}...")
                raise ValueError(f"LLM 返回的不是有效 JSON: {json_content[:100]}")
        else:
            parsed = result
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