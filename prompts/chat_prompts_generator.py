# prompts/chat_prompts_generator.py
from typing import Dict, Any, List
from prompts.prompt_spec import PromptSpec, normalize_spec, build_answer_guidelines, build_rag_block, pick_template

ROLE_DEFINITION = "你是EmoFlow情绪陪伴助手，提供温暖、清晰、可执行的回应。"

def build_final_prompt(ana: Dict[str, Any], state_summary: str, question: str) -> str:
    spec = PromptSpec(
        stage=ana["stage"],
        intent=ana["intent"],
        valence=ana["valence"],
        emotion_label=ana.get("emotion_label",""),
        ask_slot=ana["ask_slot"],
        pace=ana["pace"],
        reply_length=ana["reply_length"],
        style=ana["style"],
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

# 对话上下文
- 阶段: {spec.stage}；意图: {spec.intent}；情感: {spec.valence}/{spec.emotion_label}
- 节奏: {spec.pace}；篇幅: {spec.reply_length}

# 生成规范
{guide}

# 检索参考（如有）
{rag_block}

# 对话历史（摘要）
{state_summary}

# 用户当前输入
{question}

# 开场/过渡句（可改写保留语义）
{opener}

# 输出要求
- 严格遵守篇幅与结构；一次成型，不写自我描述。
"""