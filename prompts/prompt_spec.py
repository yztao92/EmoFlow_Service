# File: prompts/prompt_spec.py
from dataclasses import dataclass
from typing import List, Dict
import random

@dataclass
class PromptSpec:
    stage: str            # warmup|mid|wrap
    intent: str           # 求建议|求安慰|闲聊|叙事|宣泄
    valence: str          # positive|neutral|negative
    emotion_label: str
    ask_slot: str         # gentle|reflect|none
    pace: str             # slow|normal|fast
    reply_length: str     # short|medium|detailed
    style: str            # warm|empathetic|direct
    need_rag: bool
    rag_queries: List[str]

# --- 1) 冲突归一 ---
def normalize_spec(spec: PromptSpec) -> PromptSpec:
    # wrap 阶段不再提问，放慢节奏（祝福/收束由 stage 决定）
    if spec.stage == "wrap":
        spec.ask_slot = "none"
        spec.pace = "slow"

    # 非 wrap 阶段禁止 none，避免误收束
    if spec.stage in ("warmup", "mid") and spec.ask_slot == "none":
        spec.ask_slot = "reflect" if spec.intent in ("求建议","叙事") else "gentle"

    # mid 阶段且为工具性/叙事 → reflect 优先
    if spec.stage == "mid" and spec.intent in ("求建议","叙事") and spec.ask_slot == "gentle":
        spec.ask_slot = "reflect"
    return spec

# --- 2) 句式模板池（仅作开场/过渡/收尾参考，允许模型改写） ---
TEMPLATES: Dict[tuple, List[str]] = {
    # warmup
    ("warm","gentle","warmup"): [
        "真替你高兴！想从哪段开始分享？",
        "好状态呀～最想留下的画面是啥？",
    ],
    ("warm","reflect","warmup"): [
        "听起来心情很好，是遇到什么好事了吗？",
        "这感觉真棒～哪一刻最让你记得清楚？",
    ],
    ("empathetic","reflect","warmup"): [
        "我听出来你挺难过的。最压心的是哪一块呢？",
        "嗯，我懂，这不容易。想先聊聊哪个方面？",
    ],
    ("empathetic","gentle","warmup"): [
        "听着你有些心事，要不要慢慢讲？",
        "我感受到你的情绪了，想先从哪里开始？",
    ],
    ("direct","gentle","warmup"): [
        "你先挑一个最想聊的点？",
        "从你觉得最关键的地方说起？",
    ],

    # mid
    ("direct","reflect","mid"): [
        "我先帮你理清要点，再说具体做法可以吗？",
        "咱们一步一步来，我先确认你想达成什么？",
    ],
    ("empathetic","reflect","mid"): [
        "我理解你的难处。你最想先改善哪一块？",
        "听起来确实辛苦。你觉得现在最需要的支持是什么？",
    ],
    ("warm","gentle","mid"): [
        "过程里有让你意外的地方吗？",
        "你希望从哪个角度切入比较好？",
    ],
    ("warm","reflect","mid"): [
        "先回应下你的感受，再一起想个小方案，好吗？",
        "你已经做得很努力了，要不要我帮你捋一下？",
    ],

    # wrap（祝福/陪伴感收尾）
    ("direct","none","wrap"): [
        "今天先到这里，愿你今晚睡个好觉。",
        "辛苦了，把自己放轻一点；祝你有个安稳的夜。",
    ],
    ("warm","none","wrap"): [
        "先收个尾～愿这份好心情留到明天。",
        "抱抱你，愿接下来的日子更松一分。",
    ],
    ("empathetic","none","wrap"): [
        "我们就先到这儿，我会一直在。晚安。",
        "谢谢你的信任分享，愿你今晚被温柔包围。",
    ],
}

def pick_template(style:str, ask_slot:str, stage:str) -> str:
    key = (style, ask_slot, stage)
    bucket = (
        TEMPLATES.get(key) or
        TEMPLATES.get((style, "reflect", stage)) or
        TEMPLATES.get((style, "none", stage)) or
        TEMPLATES.get(("direct","reflect","mid"))
    )
    return random.choice(bucket)

# --- 3) 回答规范（篇幅/结构/安全） → 由 stage 决定结构；wrap 强化祝福 ---
def build_answer_guidelines(spec: PromptSpec) -> str:
    # 句长与句数约束
    if spec.reply_length == "short":
        max_sents, max_chars = 2, 26
    elif spec.reply_length == "medium":
        max_sents, max_chars = 4, 36
    else:  # detailed
        max_sents, max_chars = 8, 48

    safety = "不做医疗诊断；避免价值评判；积极情绪可做≤8字镜像复述"

    # 用 stage 决定结构
    if spec.stage == "wrap":
        structure = "温柔收尾：不再开启新话题；以祝福/陪伴感结尾；必要时给一步很小的可执行建议（可选）"
        bless = "\n- 收尾祝福：末句加入自然祝福/陪伴语（如“晚安”“照顾好自己”“愿你睡个好觉”）。"
    elif spec.stage == "warmup":
        structure = "先微肯定或简短反馈，再给一个开放轻问；避免连环追问"
        bless = ""
    else:  # mid
        structure = "先简短回应，再给一点可操作建议或澄清性轻问"
        bless = ""

    return f"""
- 语气：{spec.style}，自然口语化，不堆砌形容。
- 结构：{structure}
- 篇幅：总句数≤{max_sents}；单句≤{max_chars}字
- 节奏：{spec.pace}
- 安全：{safety}{bless}
"""

def build_rag_block(spec: PromptSpec) -> str:
    if not spec.need_rag or not spec.rag_queries:
        return "（无）"
    bullets = "\n".join([f"- {q}" for q in spec.rag_queries])
    return f"可检索要点：\n{bullets}"