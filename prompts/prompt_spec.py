# prompts/prompt_spec.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class PromptSpec:
    stage: str            # warmup|mid|wrap
    intent: str           # 求建议|求安慰|闲聊|叙事|宣泄
    valence: str          # positive|neutral|negative
    emotion_label: str
    ask_slot: str         # gentle|reflect|none
    pace: str             # slow|normal|fast  (来自分析派生)
    reply_length: str     # short|medium|detailed
    style: str            # warm|empathetic|direct
    need_rag: bool
    rag_queries: List[str]

# --- 1) 冲突归一 ---
def normalize_spec(spec: PromptSpec) -> PromptSpec:
    # wrap 阶段不再提问
    if spec.stage == "wrap":
        spec.ask_slot = "none"
        spec.pace = "slow"
    # mid 阶段且为工具性/叙事 → reflect 优先
    if spec.stage == "mid" and spec.intent in ("求建议","叙事") and spec.ask_slot == "gentle":
        spec.ask_slot = "reflect"
    return spec

# --- 2) 句式模板池（先微肯定→轻问；不超过 2 句） ---
TEMPLATES = {
    # style × ask_slot × stage
    ("warm","reflect","warmup"): [
        "听到你的好心情真替你开心！想先说人还是事？",
        "这份喜悦好动人～最想记录哪一刻？",
    ],
    ("warm","gentle","warmup"): [
        "开心收到了！想从哪个细节聊起？",
        "好状态想留住哪一瞬间？",
    ],
    ("empathetic","reflect","warmup"): [
        "我听见你的难受了。最困住你的点在哪？",
        "这很不容易，我在。想先说哪部分？",
    ],
    ("direct","reflect","mid"): [
        "我先理下重点，再给一个可执行方案，可以吗？",
        "我们一步步来，我先确认你的目标？",
    ],
    ("direct","none","wrap"): [
        "先到这儿：你已拿到下一步。需要我明天提醒你吗？",
        "收到。把今天的收获记一下，改天继续？",
    ],
}

def pick_template(style:str, ask_slot:str, stage:str) -> str:
    key = (style, ask_slot, stage)
    bucket = TEMPLATES.get(key) or TEMPLATES.get((style, "reflect", stage)) or TEMPLATES.get(("direct","reflect","mid"))
    # 简单轮替（可接入你的随机器）
    return bucket[0]

# --- 3) 回答规范（篇幅/结构/安全） ---
def build_answer_guidelines(spec: PromptSpec) -> str:
    # 句长与句数约束
    if spec.reply_length == "short":
        max_sents, max_chars = 2, 26
    elif spec.reply_length == "medium":
        max_sents, max_chars = 4, 36
    else:  # detailed
        max_sents, max_chars = 8, 48

    # 安全与风格放行：积极场景允许≤8字镜像
    safety = "不做医疗诊断；避免价值评判；积极情绪可做≤8字镜像复述"
    structure = "先微肯定或简短反馈，再单点轻问；避免连环追问"
    if spec.ask_slot == "none":
        structure = "做总结与收束，不再开启新话题；可给一步可执行的微建议"

    return f"""
- 语气：{spec.style}，自然口语化，不堆砌形容。
- 结构：{structure}
- 篇幅：总句数≤{max_sents}；单句≤{max_chars}字
- 节奏：{spec.pace}
- 安全：{safety}
"""

def build_rag_block(spec: PromptSpec) -> str:
    if not spec.need_rag or not spec.rag_queries:
        return "（无）"
    bullets = "\n".join([f"- {q}" for q in spec.rag_queries])
    return f"可检索要点：\n{bullets}"