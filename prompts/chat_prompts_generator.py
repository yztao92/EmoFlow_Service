# prompts/chat_prompts_generator.py
import logging
from typing import Dict, Any, List

# 角色定义和沟通风格（这些常量需要从其他地方导入或定义）
ROLE_DEFINITION = "你是EmoFlow情绪陪伴助手，专门帮助用户管理情绪、提供情感支持。"
STYLE_AND_RULES = "保持温暖、理解、专业的沟通风格，根据用户情绪状态调整回复策略。"

def generate_reply(
    ana: Dict[str, Any],
    rag_bullets: List[str],
    state_summary: str,
    question: str,
    fewshots: str = "",
    memory_bullets: str = ""
) -> str:
    """生成提示：根据分析结果和情绪状态生成回复"""
    
    # 获取新字段结构
    emotion = ana.get("emotion", "neutral")
    intent = ana.get("intent", "chitchat")
    ask_slot = ana.get("ask_slot", "gentle")
    need_rag = ana.get("need_rag", False)
    rag_queries = ana.get("rag_queries", [])
    
    rag_text = "；".join(rag_bullets) if rag_bullets else "（无）"
    
    # 根据情绪状态和意图生成提示
    emotion_hint = generate_emotion_hint(emotion, intent, ask_slot)
    
    # 根据分析结果生成描述性说明
    analysis_description = get_analysis_description(emotion, intent, ask_slot, need_rag)
    
    return f"""
# 角色定义
{ROLE_DEFINITION}

# 沟通风格
{STYLE_AND_RULES}

# 当前对话状态
{analysis_description}

# 对话历史
{state_summary}

# 用户当前输入
{question}

# 可用资源
- 外部建议：{rag_text}
- 记忆要点：{memory_bullets if memory_bullets else "（无）"}
- 示例参考：{fewshots if fewshots else "（无）"}

# 回复指导
{emotion_hint}

# 输出要求
请根据以上信息生成回复，注意：
1. 符合角色定位和沟通风格
2. 根据情绪状态调整语气和策略
3. 按照ask_slot策略进行引导
4. 适当使用外部建议和记忆要点
5. 回复要自然、有温度、有引导性
"""

def generate_emotion_hint(emotion: str, intent: str, ask_slot: str) -> str:
    """根据情绪、意图和提问策略生成回复指导"""
    
    # 情绪处理策略
    if emotion == "high":
        if intent == "comfort":
            if ask_slot == "reflect":
                return "先共情当前强烈情绪，再提出开放式问题引导用户补充细节。"
            else:  # gentle 模式（默认）
                return "先共情当前强烈情绪，用共鸣、分享或轻描淡写的方式引导用户自然说出更多，避免直接提问。"
        elif intent == "vent":
            if ask_slot == "reflect":
                return "先接纳用户的情绪宣泄，再提出开放式问题引导用户继续表达。"
            else:  # gentle 模式（默认）
                return "先接纳用户的情绪宣泄，用共鸣的方式引导用户继续表达，避免打断。"
        else:
            if ask_slot == "reflect":
                return "先回应强烈情绪，再提出开放式问题引导用户补充细节。"
            else:  # gentle 模式（默认）
                return "先回应强烈情绪，用温和的方式引导用户继续分享。"
    
    elif emotion == "low":
        if intent == "chitchat":
            if ask_slot == "reflect":
                return "用轻松的语气回应，再提出开放式问题让对话延续。"
            else:  # gentle 模式（默认）
                return "用轻松的语气回应，用共鸣或分享的方式引导用户多说。"
        else:
            if ask_slot == "reflect":
                return "温和回应，再提出开放式问题引导用户补充细节。"
            else:  # gentle 模式（默认）
                return "温和回应，用共鸣的方式引导用户继续分享。"
    
    else:  # neutral
        if intent == "advice":
            if ask_slot == "reflect":
                return "先理解用户需求，再提出开放式问题引导用户补充更多信息。"
            else:  # gentle 模式（默认）
                return "先理解用户需求，用引导的方式让用户补充更多信息。"
        elif intent == "chitchat":
            if ask_slot == "reflect":
                return "自然回应，再提出开放式问题让对话延续。"
            else:  # gentle 模式（默认）
                return "自然回应，用共鸣或分享的方式引导用户多说。"
        else:
            if ask_slot == "reflect":
                return "自然回应，再提出开放式问题引导用户补充细节。"
            else:  # gentle 模式（默认）
                return "自然回应，用共鸣的方式引导用户继续分享。"

def get_analysis_description(emotion: str, intent: str, ask_slot: str, need_rag: bool) -> str:
    """根据新字段生成对话状态描述"""
    
    # 情绪状态描述
    if emotion == "high":
        emotion_desc = "用户情绪强烈，需要重点关注和回应"
    elif emotion == "low":
        emotion_desc = "用户情绪平缓，适合轻松交流"
    else:
        emotion_desc = "用户情绪稳定，正常交流状态"
    
    # 意图描述
    if intent == "comfort":
        intent_desc = "用户寻求情感支持和理解"
    elif intent == "advice":
        intent_desc = "用户需要建议或解决方案"
    elif intent == "vent":
        intent_desc = "用户需要情绪宣泄和倾听"
    else:
        intent_desc = "用户进行日常闲聊"
    
    # 提问策略描述
    if ask_slot == "reflect":
        strategy_desc = "采用反思式提问策略，先回应再提问"
    elif ask_slot == "gentle":
        strategy_desc = "采用温和引导策略，用共鸣和分享引导用户"
    else:  # none
        strategy_desc = "不主动提问，专注回应和引导"
    
    # 知识检索描述
    rag_desc = "需要外部知识支持" if need_rag else "纯情感交流，无需外部知识"
    
    return f"{emotion_desc}，{intent_desc}，{strategy_desc}，{rag_desc}"