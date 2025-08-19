# File: prompts/chat_analysis.py
import json
import logging
import re
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
  "rag_queries": ["..."]
}}
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

# ===== 稳健的 JSON 抽取器 =====
def _extract_json_obj(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        return {}
    s = text.strip()

    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()

    if s.startswith("{") and s.endswith("}"):
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return {k.strip(): v for k, v in d.items()}
            return d
        except Exception:
            pass

    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return {}
    candidate = m.group(0)

    end_idx = len(candidate)
    while end_idx > 0:
        chunk = candidate[:end_idx].strip()
        if chunk.endswith("}"):
            try:
                d = json.loads(chunk)
                if isinstance(d, dict):
                    return {k.strip(): v for k, v in d.items()}
                return d
            except Exception:
                pass
        end_idx -= 1
    return {}

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
    if emotion_label in ("sadness","tired","lonely","fear","anxious","anger") and last_stage in (None,"wrap"):
        stage = "warmup"
    if intensity == "low" and intent not in ("求建议","宣泄"):
        stage = "wrap"
    return stage

# ===== pace =====
def auto_pace(stage:str, intensity:str) -> str:
    if stage == "wrap":
        return "slow"
    if intensity == "high":
        return "fast"
    if intensity == "low":
        return "slow"
    return "normal"

# ===== reply_length =====
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

    # 初始兜底
    res: Dict[str,Any] = {
        "valence": "neutral",
        "intensity": "medium",
        "dominance": "medium",
        "emotion_label": "calm",
        "stage": "warmup" if round_index <= 2 else ("mid" if round_index <= 6 else "wrap"),
        "intent": "闲聊",
        "ask_slot": "gentle",
        "need_rag": False,
        "rag_queries": [],
        "pace": "normal",
        "style": "direct",
        "reply_length": "short",
    }

    try:
        cand = {}
        if isinstance(raw, dict):
            if "answer" in raw and isinstance(raw["answer"], str):
                cand = _extract_json_obj(raw["answer"])
            else:
                cand = {k: v for k, v in raw.items() if isinstance(v, (str, bool, list))}
        elif isinstance(raw, str):
            cand = _extract_json_obj(raw)

        if isinstance(cand, dict) and cand:
            for k in ("valence","intensity","dominance","emotion_label","intent","ask_slot","need_rag","rag_queries"):
                if k in cand:
                    res[k] = cand[k]
        else:
            logging.warning("🧠 [分析] 未提取到有效 JSON，使用兜底参数")
    except Exception as e:
        logging.warning(f"🧠 [分析] JSON 解析异常：{e}")

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
    if not isinstance(rqs, list):
        rqs = []
    res["rag_queries"] = [str(s).strip()[:60] for s in rqs[:3]] if res["need_rag"] else []

    # 最终规则机
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
    if res["stage"] == "wrap":
        res["ask_slot"] = "none"

    # 派生字段
    res["pace"] = auto_pace(res["stage"], res["intensity"])
    if res["stage"] == "mid" and res["intent"] in ("求建议","叙事") and res["ask_slot"] == "gentle":
        res["ask_slot"] = "reflect"
    res["style"] = "warm" if res["valence"] == "positive" else (
        "empathetic" if res["emotion_label"] in ("sadness","tired","lonely","fear","anxious","anger") else "direct"
    )
    res["reply_length"] = map_reply_length(res["stage"], res["intent"], res["intensity"], question or "")

    # —— 保底补齐所有字段 —— #
    required_defaults = {
        "stage": "warmup",
        "intent": "闲聊",
        "valence": "neutral",
        "intensity": "medium",
        "dominance": "medium",
        "emotion_label": "calm",
        "ask_slot": "gentle",
        "need_rag": False,
        "rag_queries": [],
        "pace": "normal",
        "style": "direct",
        "reply_length": "short",
    }
    for k, v in required_defaults.items():
        if k not in res or res[k] is None:
            res[k] = v

    try:
        logging.info("[ANALYSIS_READY] %s", json.dumps(res, ensure_ascii=False))
    except Exception:
        pass

    return res