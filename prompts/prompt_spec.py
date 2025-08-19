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
    ("warm","reflect","warmup"): [
        "哇，听着真开心～是遇到什么好事了吗？",
        "这感觉太棒了！说说最让你开心的瞬间吧～",
    ],
    ("warm","gentle","warmup"): [
        "真替你高兴！想从哪段开始分享？",
        "好状态呀～最想留下的画面是啥？",
    ],
    ("empathetic","reflect","warmup"): [
        "我听出来你挺难过的。最压心的是哪一块呢？",
        "嗯，我懂，这不容易。想先聊聊哪个方面？",
    ],
    ("direct","reflect","mid"): [
        "要不我先帮你梳理重点，再说下可行的做法？",
        "咱们一步步来，我先确认下你想达成什么？",
    ],
    ("direct","none","wrap"): [
        "先聊到这吧，你已经有方向了。要不要我明天再提醒你？",
        "好，今天就收个尾吧～把想法记下来，下次接着说？",
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