# prompts/chat_prompts_generator.py
from typing import Dict, Any, List
from prompts.prompt_spec import PromptSpec, normalize_spec, build_answer_guidelines, build_rag_block, pick_template

ROLE_DEFINITION = "你是一个温暖、耐心、值得信赖的情绪陪伴者，具备基础心理学常识与非暴力沟通技巧。你善于倾听与共情，能够在不同情绪状态下提供恰当的支持和引导。"

def build_final_prompt(ana: Dict[str, Any], state_summary: str, question: str) -> str:
    spec = PromptSpec(
        stage=ana.get("stage", "暖场"),
        intent=ana.get("intent", "闲聊"),
        valence=ana.get("valence", "neutral"),
        emotion_label=ana.get("emotion_label", ""),
        ask_slot=ana.get("ask_slot", "gentle"),
        pace=ana.get("pace", "normal"),
        reply_length=ana.get("reply_length", "short"),
        style=ana.get("style", "warm"),
        need_rag=ana.get("need_rag", False),
        rag_queries=ana.get("rag_queries", []),
    )
    spec = normalize_spec(spec)

    guide = build_answer_guidelines(spec)
    rag_block = build_rag_block(spec)
    opener = pick_template(spec.style, spec.ask_slot, spec.stage)

    return f"""
# 角色
{ROLE_DEFINITION}

# 对话历史
{state_summary}

# 用户当前输入
{question}

# 生成回答规范
{guide}

# 检索参考（如有）
{rag_block}

# 开场/过渡句（不要直接用，用自然的语气改写）
{opener}

"""