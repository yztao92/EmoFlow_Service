# prompts/chat_prompts_generator.py
from typing import List, Dict, Any
import logging
from llm.llm_factory import chat_with_llm

# 统一的对话prompt配置
ROLE_DEFINITION = """
你是一个贴心的朋友型聊天对象。

"""

STYLE_AND_RULES = """
- 说话自然幽默，有温度，不矫情，不装AI专家
- 幽默要生活化、接地气，让所有人都听得懂
- 回答必须简洁直接，去掉废话和套话
- 单一引导点；不要连环追问
- 当代口语；每句≤20字；最多 1–2 句
- 禁小众梗与过度比喻
"""


def build_final_prompt(
    ana: Dict[str, Any],
    rag_bullets: List[str],
    state_summary: str,
    question: str,
    fewshots: str = "",
    memory_bullets: str = ""
) -> str:
    """生成提示：根据分析结果和情绪状态生成回复"""
    mode = ana.get("mode", "普通")
    stage = ana.get("stage", "暖场")
    context_type = ana.get("context_type", "闲聊")
    ask_slot = ana.get("ask_slot", "gentle")
    rag_text = "；".join(rag_bullets) if rag_bullets else "（无）"

    # 获取是否需要共情
    need_empathy = ana.get("need_empathy", False)
    
    # 根据情绪模式、提问策略和共情需求给提示
    emotion_hint = ""
    if mode == "低谷":
        if need_empathy:
            if ask_slot == "active":
                emotion_hint = "先共情当前情绪，再温和询问触发点或原因。"
            else:  # gentle 模式（默认）
                emotion_hint = "先共情当前情绪，用共鸣、分享或轻描淡写的方式引导用户自然说出更多，避免直接提问。"
        else:
            if ask_slot == "active":
                emotion_hint = "直接回应，再温和询问触发点或原因。"
            else:  # gentle 模式（默认）
                emotion_hint = "直接回应，用共鸣、分享或轻描淡写的方式引导用户自然说出更多，避免直接提问。"
    elif mode == "庆祝":
        if need_empathy:
            if ask_slot == "active":
                emotion_hint = "先共享喜悦，再询问具体细节让快乐延续。"
            else:  # gentle 模式（默认）
                emotion_hint = "先共享喜悦，用共鸣、分享或轻描淡写的方式引导用户分享更多，避免直接提问。"
        else:
            if ask_slot == "active":
                emotion_hint = "直接分享喜悦，再询问具体细节让快乐延续。"
            else:  # gentle 模式（默认）
                emotion_hint = "直接分享喜悦，用共鸣、分享或轻描淡写的方式引导用户分享更多，避免直接提问。"
    else:
        if need_empathy:
            if ask_slot == "active":
                emotion_hint = "先共情回应，并主动询问相关细节。"
            else:  # gentle 模式（默认）
                emotion_hint = "先共情回应，用共鸣、分享或轻描淡写的方式引导用户多说，避免直接提问。"
        else:
            if ask_slot == "active":
                emotion_hint = "自然回应，并主动询问相关细节。"
            else:  # gentle 模式（默认）
                emotion_hint = "自然回应，用共鸣、分享或轻描淡写的方式引导用户多说，避免直接提问。"

    # 根据分析结果生成描述性说明
    def get_analysis_description(ana):
        mode = ana.get("mode", "普通")
        stage = ana.get("stage", "暖场") 
        context_type = ana.get("context_type", "闲聊")
        
        # 对话阶段描述
        if stage == "暖场":
            stage_desc = "对话刚开始，需要建立氛围和信任"
        elif stage == "建议":
            stage_desc = "对话中期，可以给出建设性建议"
        else:
            stage_desc = "对话后期，自然收束，避免过度深入"
        
        # 情绪模式描述
        if mode == "低谷":
            mode_desc = "用户表达悲伤、痛苦、绝望、抑郁等负面情绪"
        elif mode == "庆祝":
            mode_desc = "用户表达开心、兴奋、满足、幸福等正面情绪"
        else:
            mode_desc = "用户情绪平和，正常聊天状态"
        
        # 对话类型描述
        if context_type == "求安慰":
            context_desc = "用户寻求情感支持和理解"
        elif context_type == "求建议":
            context_desc = "用户明确需要解决方案或建议"
        elif context_type == "闲聊":
            context_desc = "日常聊天，无特殊需求"
        elif context_type == "玩梗":
            context_desc = "用户开玩笑或使用幽默表达"
        else:
            context_desc = "不属于以上类型的对话"
        
        return f"{stage_desc}，{mode_desc}，{context_desc}"
    
    return f"""
# 角色定义
{ROLE_DEFINITION}

# 沟通风格
{STYLE_AND_RULES}

# 当前对话状态
{get_analysis_description(ana)}

# 对话历史
{state_summary}

# 用户当前输入
{question}

# 可用资源
- 外部建议：{rag_text}

# 回复策略
{emotion_hint}

请直接输出最终回复。
""".strip()

def generate_reply(
    ana: Dict[str, Any],
    rag_bullets: List[str],
    state_summary: str,
    question: str,
    fewshots: str = "",
    memory_bullets: str = ""
) -> str:
    prompt = build_final_prompt(ana, rag_bullets, state_summary, question, fewshots, memory_bullets)
    logging.info("📝 [Final Prompt]\n%s", prompt)

    res = chat_with_llm(prompt)
    answer = (res.get("answer") or "").strip()
    logging.info("💬 [生成结果] %s", answer)
    return answer