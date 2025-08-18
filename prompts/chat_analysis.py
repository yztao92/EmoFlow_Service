# prompts/chat_analysis.py
import json
import logging
from typing import Dict, Any, Optional
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
你是对话分析器。阅读给定对话，只输出严格 JSON（不要多余文字、不要注释）。

# 对话
- round_index: {round_index}
- history: {state_summary}
- question: {question}

# 需要你输出（仅这些键）：
{{
  "valence": "positive|neutral|negative",
  "intensity": "high|medium|low",
  "dominance": "high|medium|low",
  "emotion_label": "happiness|sadness|anger|calm|fear|tired|anxious|surprised|lonely|...",
  "intent": "求建议|求安慰|闲聊|叙事|宣泄",
  "ask_slot": "gentle|reflect|none",
  "need_rag": true|false,
  "rag_queries": ["..."]     // need_rag=false 时给 []
}}

# 判定标准（请据此做判断）
- valence：整体情感极性。积极（赞美/感谢/庆祝/满足），消极（痛苦/抱怨/恐惧/愤怒），否则中性。
- intensity：情绪强度。依据夸张副词（非常、太、特别）、叹号/连续短句、第一人称强烈感受词（受不了/崩溃/激动）、生理线索（哭、失眠）、语速感。强→high；轻→low；否则 medium。
- dominance：掌控感。表达“我能…/已解决/有计划/已采取行动”→high；明显无助/被动/求救→low；其余 medium。
- emotion_label：更细情绪词，用常识映射（幸福/开心→happiness；难过/流泪→sadness；生气→anger；平静→calm；焦虑→anxious；害怕→fear；疲惫→tired；孤独→lonely …）。
- intent：明确求方法/建议→求建议；希望被理解/安慰→求安慰；叙述事件/讲经过→叙事；主要发泄/吐槽→宣泄；随意社交→闲聊。
- ask_slot：若对方需要被接住或梳理→reflect（先简短反馈再轻问）；轻触达成延续→gentle；不应提问（如已要收尾/明确拒绝）→none。
- need_rag：仅当回答需要外部事实/步骤/概念解释时为 true（如“如何办理…/X 的原理/定义/对比/步骤清单”）。
- rag_queries：≤3 条，名词化、可检索、简短；need_rag=false 时返回 []。

# 输出要求：仅返回 JSON 对象，不要多余文本。
"""

_ALLOWED = {
    "valence": {"positive","neutral","negative"},
    "intensity": {"high","medium","low"},
    "dominance": {"high","medium","low"},
    "intent": {"求建议","求安慰","闲聊","叙事","宣泄"},
    "ask_slot": {"gentle","reflect","none"},
}

def _clamp(v: str, key: str, default: str) -> str:
    if not isinstance(v, str):
        return default
    return v if v in _ALLOWED[key] else default

# ===== 规则机：stage =====
def infer_stage(
    round_index:int,
    intent:str,
    emotion_label:str,
    *,
    explicit_close:bool=False,
    new_topic:bool=False,
    target_resolved:bool=False,
    last_stage:Optional[str]=None,
    intensity:str="medium",
) -> str:
    if new_topic:
        return "warmup"
    if explicit_close or target_resolved:
        return "wrap"
    if round_index <= 2:
        return "warmup"
    if round_index >= 7:
        return "wrap"

    stage = "mid"

    # 负向强情绪从 wrap/None 回暖以先接住
    if emotion_label in ("sadness","tired","lonely","fear","anxious","anger") and last_stage in (None,"wrap"):
        stage = "warmup"

    # 强情绪但非工具性诉求，且能量下降时可提前收束
    if intensity == "low" and intent not in ("求建议","宣泄"):
        stage = "wrap"

    return stage

# ===== pace：由 stage + intensity 自动推断（不从 LLM 获取） =====
def auto_pace(stage:str, intensity:str) -> str:
    if stage == "wrap":
        return "slow"
    if intensity == "high":
        return "fast"
    if intensity == "low":
        return "slow"
    return "normal"

# ===== reply_length：按 stage 自动；mid 某些条件触发 detailed =====
def map_reply_length(stage:str, intent:str, intensity:str, question:str) -> str:
    base = "short" if stage in ("warmup","wrap") else "medium"
    want_detail = any(k in (question or "") for k in ("详细","展开","具体点","多给些","多一点","为什么","原理","步骤"))
    if stage == "mid" and intent in ("求建议","叙事") and (want_detail or intensity=="high"):
        return "detailed"
    return base

# ===== 主函数 =====
def analyze_turn(
    round_index:int,
    state_summary:str,
    question:str,
    *,
    last_stage:Optional[str]=None,
    explicit_close:bool=False,
    new_topic:bool=False,
    target_resolved:bool=False
) -> Dict[str,Any]:
    payload = {
        "round_index": round_index,
        "state_summary": state_summary or "",
        "question": question or "",
    }
    raw = chat_with_llm(ANALYZE_PROMPT.format(**payload))

    # 兜底
    res: Dict[str,Any] = {
        "valence": "neutral",
        "intensity": "medium",
        "dominance": "medium",
        "emotion_label": "calm",

        # 下面这些由本地规则机/派生计算
        "stage": "warmup" if round_index <= 2 else ("mid" if round_index <= 6 else "wrap"),
        "intent": "闲聊",
        "ask_slot": "gentle",
        "need_rag": False,
        "rag_queries": [],

        "pace": "normal",
        "style": "direct",
        "reply_length": "short",
    }

    # 解析 LLM（仅上述 8 个字段）
    try:
        cand = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, dict) else {})
        if isinstance(cand, dict):
            res.update({k: cand.get(k, res[k]) for k in ("valence","intensity","dominance","emotion_label","intent","ask_slot","need_rag","rag_queries")})
    except Exception as e:
        logging.error("🧠 [分析] JSON 解析失败 → %s", e, exc_info=True)

    # 正向情绪快速兜底
    q = (question or "")[:200]
    if any(t in q for t in ("幸福","开心","高兴","喜悦","满足","好消息","顺利")):
        res["valence"] = "positive"
        res["emotion_label"] = "happiness"

    # 规范化
    res["valence"]   = _clamp(res.get("valence"),   "valence",   "neutral")
    res["intensity"] = _clamp(res.get("intensity"), "intensity", "medium")
    res["dominance"] = _clamp(res.get("dominance"), "dominance", "medium")
    res["intent"]    = _clamp(res.get("intent"),    "intent",    "闲聊")
    res["ask_slot"]  = _clamp(res.get("ask_slot"),  "ask_slot",  "gentle")
    res["need_rag"]  = bool(res.get("need_rag"))
    rqs = res.get("rag_queries") or []
    if not isinstance(rqs, list): rqs = []
    res["rag_queries"] = [str(s).strip()[:60] for s in rqs[:3]] if res["need_rag"] else []

    # 规则机最终确定 stage
    res["stage"] = infer_stage(
        round_index=round_index,
        intent=res["intent"],
        emotion_label=res.get("emotion_label",""),
        explicit_close=explicit_close,
        new_topic=new_topic,
        target_resolved=target_resolved,
        last_stage=last_stage,
        intensity=res["intensity"],
    )

    # 收尾强约束
    if res["stage"] == "wrap":
        res["ask_slot"] = "none"

    # 由参数自动判定 pace（stage+intensity）
    res["pace"] = auto_pace(res["stage"], res["intensity"])

    # 反思式优先（mid & 求建议/叙事）
    if res["stage"] == "mid" and res["intent"] in ("求建议","叙事") and res["ask_slot"] == "gentle":
        res["ask_slot"] = "reflect"

    # style：简单基调（可按你系统风格替换）
    res["style"] = "warm" if res["valence"] == "positive" else ("empathetic" if res["emotion_label"] in ("sadness","tired","lonely","fear","anxious","anger") else "direct")

    # reply_length：自动+条件 detailed
    res["reply_length"] = map_reply_length(res["stage"], res["intent"], res["intensity"], question or "")

    return res