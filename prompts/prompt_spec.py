# prompts/prompt_spec.py
from dataclasses import dataclass
from typing import List, Literal, Dict, Tuple

Emotion = Literal["低谷", "普通", "庆祝"]
Stage = Literal["暖场", "建议", "收尾"]
Intent = Literal["求建议", "求安慰", "闲聊", "叙事", "宣泄"]
AskSlot = Literal["gentle", "reflect", "none"]
Pace = Literal["slow", "normal", "fast"]
ReplyLength = Literal["short", "medium", "detailed"]

@dataclass
class PromptSpec:
    # 分析产物（来自 chat_analysis）
    emotion: Emotion = "普通"
    stage: Stage = "暖场"
    intent: Intent = "闲聊"
    ask_slot: AskSlot = "gentle"
    pace: Pace = "normal"
    reply_length: ReplyLength = "short"
    need_rag: bool = False
    rag_queries: List[str] = None

    # 运行时上下文
    state_summary: str = ""
    question: str = ""
    fewshots: str = ""
    memory_bullets: List[str] = None
    rag_bullets: List[str] = None
    # 新增：原始对话历史，格式[(role, content)]
    history_messages: List = None

    def as_dict(self) -> Dict:
        return {
            "emotion": self.emotion, "stage": self.stage, "intent": self.intent,
            "ask_slot": self.ask_slot, "pace": self.pace, "reply_length": self.reply_length,
            "need_rag": self.need_rag, "rag_queries": self.rag_queries or [],
        }

def map_reply_length(stage: Stage, intent: Intent, pace: Pace) -> ReplyLength:
    """
    对齐你 PDF 的映射规则（示例）：
    1) 默认：暖场→short，建议→medium，收尾→short
    2) 触发 detailed：stage=建议 且 intent ∈ {求建议, 叙事}
    3) 收敛：收尾永远 short；暖场永远 short
    4) pace 仅在 stage=建议 时可将 medium→detailed（当 pace=slow 且 intent=求安慰 时保持 medium）
    """
    if stage in ("暖场", "收尾"):
        return "short"
    # stage=建议
    if intent in ("求建议", "叙事"):
        return "detailed"
    if intent == "求安慰":
        return "medium"
    # 闲聊、宣泄
    return "medium" if pace != "fast" else "short"

def build_answer_guidelines(spec: PromptSpec) -> str:
    """
    把“回答规范”拼成一段可插入 Special Instructions 的规则文本。
    只表达规则，不举例子（符合你之前的要求）。
    """
    # 语气与风格（随情绪调整）
    tone = {
        "低谷": "语气温柔克制，优先共情与安抚；避免说教与贴标签",
        "普通": "自然口语化，简洁直接；不过度延展话题",
        "庆祝": "明快积极，放大正向感受；避免功利化建议",
    }[spec.emotion]

    # 结构约束（与 ask_slot、stage 协同）
    if spec.ask_slot == "none":
        structure = "不提问；先情绪回应，再给一条可执行建议或自然收束"
    elif spec.ask_slot == "reflect":
        structure = "先做情绪反馈，再抛出一个开放式问题；问题需单点聚焦"
    else:  # gentle
        structure = "轻问一句开放问题，引导继续分享；单一引导点，避免连环追问"

    # 篇幅与节奏（reply_length / pace）
    length_rule = {
        "short": "总句数≤2，单句≤26字",
        "medium": "总句数≤4，单句≤32字",
        "detailed": "分段清晰，条理化表达，避免堆砌金句",
    }[spec.reply_length]
    pace_rule = {
        "slow": "放慢节奏，先确认感受再推进到建议",
        "normal": "正常节奏，先人后事，再到建议",
        "fast": "快速收束，用最少话语完成回应",
    }[spec.pace]

    # 安全边界
    safety = "不提供医疗诊断与处方；避免价值评判；不复述用户原话"

    # 汇总
    lines = [
        f"- 语气：{tone}",
        f"- 结构：{structure}",
        f"- 篇幅：{length_rule}",
        f"- 节奏：{pace_rule}",
        f"- 安全：{safety}",
        "- 输出必须一次成型，不写前言与自我描述",
    ]
    return "\n".join(lines)