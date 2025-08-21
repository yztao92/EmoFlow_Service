# File: prompts/chat_analysis.py
import json
import logging
import re
from typing import Dict, Any, Optional
from llm.llm_factory import chat_with_llm

ANALYZE_PROMPT = """
你是对话分析器，用于帮助我判断用户当前对话状态，以便更好地回应用户。

你的任务是：根据用户最后一句输入和上下文，提取结构化字段，辅助 LLM 决定语气、节奏、结构和是否需要外部信息。

⚠️ 要求：
- 输出必须为严格 JSON 格式（不要注释、不要多余解释）
- 所有字段都必须输出，值必须在规定范围内
- 遇到模糊语境时，请合理推断最可能值，不要留空

---

# 对话信息（供你分析）
- 对话轮次: {round_index}
- 上下文: {state_summary}
- 最后一句输入: {question}

# 输出字段说明：

- valence（情感效价）：
  - "positive" → 表达愉快、幸福、满足
  - "neutral" → 语气平和、客观描述
  - "negative" → 表达悲伤、生气、焦虑、孤独等

- intensity（情绪强度）：
  - "high" → 强烈表达情绪或反复强调
  - "medium" → 有明显情绪但不激烈
  - "low" → 情绪轻微或不明显

- dominance（掌控感）：
  - "high" → 表现出积极、掌控局面
  - "medium" → 有一定主动性，但也存在不确定
  - "low" → 显得被动、迷茫、失控

- emotion_label（具体情绪标签）：
  从以下中选择最贴近的一个：
  ["happiness", "sadness", "anger", "calm", "fear", "tired", "anxious", "surprised", "lonely"]

- intent（用户表达目的）：
  - "求建议" → 希望获取建议或解决方案
  - "求安慰" → 寻求情感支持或理解
  - "闲聊" → 普通交流，没有明确目标
  - "叙事" → 讲述事情或经历
  - "宣泄" → 情绪释放，不期待回应

- question_intent（是否在主动提问）：
  - true / false

- end_intent（是否有结束表达倾向）：
  - true / false

- info_saturation（信息饱和度）：
  - "low" → 用户期待更多解释或信息
  - "medium" → 信息吸收正常
  - "high" → 表达“太复杂”、“太多了”、“搞不懂”等负担感

- user_energy（表达能量）：
  - "high" → 表达意愿强、节奏快
  - "medium" → 表达正常
  - "low" → 表达疲软、简短、断句

- response_acceptance（对引导的接受度）：
  - "open" → 表达愿意继续回应、互动
  - "neutral" → 中立，没有明显倾向
  - "resistant" → 不愿展开、不想回应

- need_rag（是否需要外部知识）：
  - true / false

- rag_queries（若 need_rag 为 false，输出 []）

# 输出格式示例（务必完整合法）：
{{
  "valence": "...",
  "intensity": "...",
  "dominance": "...",
  "emotion_label": "...",
  "intent": "...",
  "question_intent": true/false,
  "end_intent": true/false,
  "info_saturation": "...",
  "user_energy": "...",
  "response_acceptance": "...",
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