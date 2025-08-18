# -*- coding: utf-8 -*-
# prompts/chat_prompts_generator.py

from __future__ import annotations
from typing import Dict, Any, List
from .prompt_spec import PromptSpec, build_answer_guidelines, map_reply_length
from llm.llm_factory import chat_with_llm  # 你项目里已存在的统一 LLM 调用

SYSTEM_ROLE = """# 角色定位
你是一个温暖、耐心、值得信赖的情绪陪伴者，具备基础心理学常识与非暴力沟通技巧。"""

BACKGROUND = """# 背景与目标
你的目标是帮助用户表达、理解和调节情绪，创造安全、轻松的交流空间。你尊重用户的节奏，
不打断、不评判、不争辩，并在对话中保持真诚和耐心。你不会提供医疗诊断或处方建议。"""


def _compose_context(spec: PromptSpec) -> str:
    analysis = f"""# 对话上下文\n## 当前对话参数\n- 情绪模式: {spec.emotion}\n- 对话阶段: {spec.stage}\n- 对话意图: {spec.intent}\n- 提问槽位: {spec.ask_slot}\n- 节奏: {spec.pace}\n- 回复长度: {spec.reply_length}"""
    # 新增：优先用原始消息
    if getattr(spec, 'history_messages', None):
        lines = ["【对话历史】"]
        for role, content in spec.history_messages:
            if role == "assistant":
                # 只取 answer 字段内容
                import re
                import ast
                # 尝试解析 {'answer': 'xxx'}
                match = re.match(r"\s*\{'answer':\s*['\"](.*?)['\"]\s*}\s*", content)
                if match:
                    answer = match.group(1)
                else:
                    try:
                        d = ast.literal_eval(content)
                        answer = d["answer"] if isinstance(d, dict) and "answer" in d else content
                    except Exception:
                        answer = content
                lines.append(f"• AI: {answer}")
            else:
                lines.append(f"• 用户: {content}")
        history = "\n".join(lines)
    else:
        history = f"\n## 对话历史\n{spec.state_summary or '（无）'}"
    user = f"\n## 用户当前输入\n{spec.question}"
    return analysis + "\n## 对话历史\n" + history + user


def _compose_special_instructions(spec: PromptSpec) -> str:
    guidelines = build_answer_guidelines(spec)
    kb = spec.rag_bullets or []
    mem = spec.memory_bullets or []
    shots = spec.fewshots or ""

    kb_block = "\n".join([f"- {b}" for b in kb]) if kb else "（无）"
    mem_block = "\n".join([f"- {m}" for m in mem]) if mem else "（无）"

    return f"""# 特殊补充
## 生成回答的规范
{guidelines}

## 可参考的观点和建议（知识库）
{kb_block}

## 记忆要点
{mem_block}

## 示例参考（可选）
{shots if shots else '（无）'}"""


def build_final_prompt(spec: PromptSpec) -> str:
    return "\n\n".join([
        SYSTEM_ROLE.strip(),
        BACKGROUND.strip(),
        _compose_context(spec).strip(),
        _compose_special_instructions(spec).strip(),
    ])


# ===== 第 6 点：兼容旧签名的包装 =====
def generate_reply(
    ana: Dict[str, Any],
    rag_bullets: List[str],
    state_summary: str,
    question: str,
    fewshots: str = "",
    memory_bullets: Any = ""
) -> str:
    """
    兼容你旧的调用方式，不改上层代码也能跑。
    - ana: chat_analysis 的结构化结果
    - rag_bullets: 预先检索好的 bullets（可空）
    - state_summary: 对话历史摘要
    - question: 用户当轮输入
    - fewshots: 可选 few-shot 文本
    - memory_bullets: 可为字符串（多行）或 List[str]
    """
    # 统一 memory 形态
    mem_list: List[str] = []
    if isinstance(memory_bullets, str):
        mem_list = [b.strip() for b in memory_bullets.split("\n") if b.strip()]
    elif isinstance(memory_bullets, list):
        mem_list = [str(b).strip() for b in memory_bullets if str(b).strip()]

    # 计算回复长度（使用新规则）
    stage = ana.get("stage", "暖场")
    intent = ana.get("intent", "闲聊")
    pace = ana.get("pace", "normal")
    reply_length = map_reply_length(stage, intent, pace)

    # 组装 Spec
    spec = PromptSpec(
        emotion=ana.get("emotion", "普通"),
        stage=stage,
        intent=intent,
        ask_slot=ana.get("ask_slot", "gentle"),
        pace=pace,
        reply_length=reply_length,
        need_rag=ana.get("need_rag", False),
        rag_queries=ana.get("rag_queries", []),
        state_summary=state_summary or "",
        question=question or "",
        fewshots=fewshots or "",
        memory_bullets=mem_list,
        rag_bullets=rag_bullets or [],
    )

    final_prompt = build_final_prompt(spec)
    return chat_with_llm(final_prompt)