# prompts/chat_analysis.py
import json
import logging
from typing import Dict, Any
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
# 角色定义
你是一个专业的对话分析器，专门负责分析用户对话内容并输出结构化的分析结果。你的分析结果将用于指导AI助手的回复策略。

# 任务说明
分析当前对话内容，识别用户情绪、意图和需求，为AI助手提供回复指导信息。

# 对话内容
- 当前轮次: {round_index}
- 历史对话: {state_summary}
- 用户最新输入: {question}

# 分析字段说明

## 1. emotion（情绪张力强度）
**定义**: 用户当前情绪的表达强度
**取值**:
- `low`: 轻微情绪或情绪词，语气平缓
- `neutral`: 无明显情绪倾向，情绪稳定
- `high`: 情绪强烈，如喜悦、愤怒、悲伤、焦虑等

**判断标准**: 根据用户用词、语气词、标点符号等判断情绪强度

## 2. intent（用户意图）
**定义**: 用户在当前对话中的主要目的
**取值**:
- `comfort`: 寻求情感支持、安慰或理解
- `advice`: 寻求建议、方法或解决方案
- `vent`: 情绪宣泄、倾诉或发泄
- `chitchat`: 日常闲聊、分享或社交

**判断标准**: 分析用户表达的核心需求和行为倾向

## 3. ask_slot（提问策略）
**定义**: AI助手在下一轮回复中应采用的提问方式
**取值**:
- `gentle`: 温和引导，用共鸣、分享等方式引导用户继续分享，避免直接提问
- `reflect`: 先回应用户情绪，再提出开放式问题，引导补充细节
- `none`: 不提问，仅作回应或结束当前话题

**判断标准**: 根据用户表达完整度、情绪状态和对话阶段决定

## 4. need_rag（是否需要知识检索）
**定义**: 用户问题是否需要外部知识支持
**取值**:
- `true`: 涉及事实、方法、概念、专有名词、时间、数据等
- `false`: 纯情绪表达或观点类内容

**判断标准**: 分析用户问题是否包含需要专业知识回答的内容

## 5. rag_queries（检索关键词）
**定义**: 当need_rag=true时，用于知识库检索的关键词
**格式**: 2-3条短句，每条≤8词，无标点符号
**示例**: ["情绪管理方法", "压力缓解技巧"]


# 输出要求
1. **格式**: 仅输出JSON格式，不要任何解释、前后缀或代码块标记
2. **字段**: 只输出已使用的字段，未使用的可选字段不要输出
3. **编码**: 使用UTF-8编码，支持中文字符
4. **结构**: 严格按照上述字段定义输出

# 分析示例
## 示例1：寻求安慰
**输入**: "我今天心情很糟糕，工作压力很大"
**输出**: {{"emotion": "high", "intent": "comfort", "ask_slot": "gentle", "need_rag": false}}

## 示例2：寻求建议
**输入**: "如何缓解工作压力？"
**输出**: {{"emotion": "neutral", "intent": "advice", "ask_slot": "reflect", "need_rag": true, "rag_queries": ["工作压力缓解", "压力管理方法"]}}

## 示例3：日常闲聊
**输入**: "今天天气不错"
**输出**: {{"emotion": "low", "intent": "chitchat", "ask_slot": "gentle", "need_rag": false}}
"""

def _normalize_queries(qlist):
    """把 rag_queries 统一为 [{'q': str, 'weight': 1.0}, ...]"""
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
    round_index: int,
    state_summary: str,
    question: str
) -> Dict[str, Any]:
    """
    分析当前对话轮次，返回结构化分析结果
    
    参数:
        round_index: 对话轮次
        state_summary: 历史对话摘要
        question: 用户当前输入
        
    返回:
        包含分析结果的字典
    """
    prompt = ANALYZE_PROMPT.format(
        round_index=round_index,
        state_summary=state_summary,
        question=question
    )

    logging.info("🧠 [分析] 入参 → round=%s, question=%s", round_index, question)
    logging.info("🧠 [分析] Prompt ↓\n%s", prompt)

    res = chat_with_llm(prompt)  # 约定返回 {"answer": "..."}
    raw_output = res.get("answer", "")

    # 默认兜底结构（与新字段定义保持一致）
    parsed = {
        "emotion": "neutral",      # 情绪张力强度
        "intent": "chitchat",      # 用户意图
        "ask_slot": "gentle",      # 提问方式
        "need_rag": False,         # 是否需要外部检索
        "rag_queries": []          # 检索短句
    }

    # 解析 LLM JSON（失败就用兜底）
    try:
        parsed.update(json.loads(raw_output))
    except Exception as e:
        logging.error("🧠 [分析] JSON 解析失败 → %s", e, exc_info=True)

    # 规范化 rag_queries
    parsed["rag_queries"] = _normalize_queries(parsed.get("rag_queries", []))

    logging.info("🧠 [分析] 结构化结果 ↓\n%s", json.dumps(parsed, ensure_ascii=False, indent=2))
    return parsed