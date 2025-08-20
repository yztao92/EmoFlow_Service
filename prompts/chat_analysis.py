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

# 字段说明（判定标准）

- valence (情感效价):
  - "positive" → 用户表达愉快、幸福、满足
  - "neutral"  → 用户表达平静、叙事、客观
  - "negative" → 用户表达悲伤、生气、焦虑、孤独等

- intensity (情绪强度):
  - "high"   → 明显强烈的情绪爆发或持续强调
  - "medium" → 有一定情绪，但相对克制
  - "low"    → 情绪轻微或不明显

- dominance (掌控感):
  - "high"   → 用户表现出控制感、积极主动
  - "medium" → 部分掌控，但有不确定或求助
  - "low"    → 明显失控、无助、被动

- emotion_label (具体情绪标签):
  从以下中选最贴近的一个：
  ["happiness","sadness","anger","calm","fear","tired","anxious","surprised","lonely"]

- intent (意图类型):
  - "求建议" → 用户希望得到方案或建议
  - "求安慰" → 用户希望得到理解、共情、安慰
  - "闲聊"   → 普通聊天、没有特定目标
  - "叙事"   → 主要在讲述事情经过
  - "宣泄"   → 明显情绪释放或抱怨，不求解决

- ask_slot (回答中是否需要提问，以及提问方式):
  用途：指示在生成 AI 回复时，是否需要针对用户最新输入附带一个提问，引导后续对话。

  - "gentle"  
    → 需要提问；形式是温和、开放式问题，让用户可以自由选择是否继续分享。  
    → 常见场景：用户刚表达完一种情绪，需要轻轻引导他展开。  
    → 例：「你想从哪个方面说起呢？」、「最近心情波动多吗？」

  - "reflect"  
    → 需要提问；在提问前，先反馈用户的情绪，再轻轻补充一个问题，引导用户进一步补充细节。  
    → 常见场景：用户明确透露情绪或故事，但信息不完整。  
    → 例：「听起来你挺难过的，你觉得最让你心累的是哪一部分？」

  - "none"  
    → 不需要提问；只需回应、共情或自然收束，不再追问。  
    → 常见场景：用户已经得到回应，或对话进入收尾，不适合继续提问。

- need_rag:
  - true  → 用户在问知识/经验类问题，需要外部知识
  - false → 普通情绪交流或生活琐事，不需要外部知识

- rag_queries:
  - 如果 need_rag=true，请给出1-2条检索查询关键词
  - 否则输出 []

# 严格输出 JSON，格式如下：
{{
  "valence": "...",
  "intensity": "...",
  "dominance": "...",
  "emotion_label": "...",
  "intent": "...",
  "ask_slot": "...",
  "need_rag": true/false,
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
    """
    从 LLM 返回中提取首个 JSON 对象（容错 markdown 代码块与噪声）。
    """
    if not isinstance(text, str) or not text.strip():
        return {}
    s = text.strip()

    # 去除 markdown 包裹 ```
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()

    # 直接 JSON
    if s.startswith("{") and s.endswith("}"):
        try:
            d = json.loads(s)
            return d if isinstance(d, dict) else {}
        except Exception:
            pass

    # 提取第一个 {...}
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return {}
    candidate = m.group(0)

    # 从右往左收缩直至能 loads
    end_idx = len(candidate)
    while end_idx > 0:
        chunk = candidate[:end_idx].strip()
        if chunk.endswith("}"):
            try:
                d = json.loads(chunk)
                return d if isinstance(d, dict) else {}
            except Exception:
                pass
        end_idx -= 1
    return {}

# ===== 极简 new_topic 判定（行业主流） =====
def is_new_topic(round_index:int, last_stage:Optional[str]) -> bool:
    # 首轮必为新话题；上轮是 wrap 后用户再开口，也视为新话题
    if round_index <= 1:
        return True
    return (last_stage == "wrap")

# ===== 极简 stage 判定（行业主流：轮次主导 + 轻兜底） =====
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
    """
    最小可用：基于轮次 + 少量兜底
    行业内主流：1-2轮=warmup；3-5轮=mid；6轮+=wrap
    """
    # 显式信号优先
    if explicit_close or target_resolved:
        return "wrap"
    # 新话题回到 warmup（哪怕轮次高）
    if new_topic:
        return "warmup"

    # 轮次主导
    if round_index <= 2:
        return "warmup"
    if round_index >= 6:
        return "wrap"
    return "mid"

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
    new_topic:Optional[bool]=None,
    target_resolved:bool=False
) -> Dict[str,Any]:
    """
    返回结构包含：stage/intent/valence/intensity/dominance/emotion_label/ask_slot/need_rag/rag_queries/pace/style/reply_length
    """
    payload = {
        "round_index": round_index,
        "state_summary": state_summary or "",
        "question": question or "",
    }
    raw = chat_with_llm(ANALYZE_PROMPT.format(**payload))  # chat_with_llm 必须返回纯字符串

    # 初始兜底
    res: Dict[str,Any] = {
        "valence": "neutral",
        "intensity": "medium",
        "dominance": "medium",
        "emotion_label": "calm",
        "stage": "warmup" if round_index <= 2 else ("mid" if round_index <= 5 else "wrap"),
        "intent": "闲聊",
        "ask_slot": "gentle",
        "need_rag": False,
        "rag_queries": [],
        "pace": "normal",
        "style": "direct",
        "reply_length": "short",
    }

    # 稳健解析
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

    # 极简 new_topic（若调用方没传，则内部判定）
    if new_topic is None:
        new_topic_flag = is_new_topic(round_index, last_stage)
    else:
        new_topic_flag = bool(new_topic)

    # 最终 stage 判定
    res["stage"] = infer_stage(
        round_index=round_index,
        intent=res["intent"],
        emotion_label=res.get("emotion_label",""),
        explicit_close=explicit_close,
        new_topic=new_topic_flag,
        target_resolved=target_resolved,
        last_stage=last_stage,
        intensity=res["intensity"],
    )

    # 收尾强约束
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

    # 保底补齐
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

    return res