from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# =========================================================
# Analysis State (保持原样，100%不改变底层接口)
# =========================================================


@dataclass
class EmotionProfile:
    sadness: float = 0.0
    anxiety: float = 0.0
    anger: float = 0.0
    fatigue: float = 0.0
    overwhelm: float = 0.0
    hope: float = 0.0


@dataclass
class CognitiveState:
    user_intent: str = "sharing"
    advice_permission: bool = False
    primary_need: str = "understanding"
    conversation_phase: str = "opening"
    should_close: bool = False
    core_tension: str = ""
    hidden_state: str = ""
    response_goal: str = "validation"


@dataclass
class AnalysisResult:
    emotion: EmotionProfile
    cognitive: CognitiveState
    rag_bullets: List[str] = field(default_factory=list)


# =========================================================
# Core Prompt Blocks (全面重构：压制炫技欲，卡死红线，规范记忆)
# =========================================================


def build_core_identity() -> str:
    return """
# 核心定位
你是 EmoFlow 情感陪伴助手。像一个了解用户近况、愿意认真听的朋友一样交流：温和、自然、具体，但不替用户做决定。你不是心理咨询师，也不通过堆砌修辞表现共情。

# 回复风格（硬性底线）
- 使用自然、简洁的大白话；避免文学化比喻、心理术语和空泛套话。
- 承认用户正在经历的感受，不改写或否定用户的自我判断。用户自我怀疑时，不用“你不是不行”“你其实已经很好了”快速反驳。
- 句式要随语境变化，不连续使用“换谁都会……”“太……了”“你其实是……”等模板。
- 不把系统分析中的标签直接说给用户；只根据用户说过的事实，用日常语言回应。
- 负面倾诉以克制接纳为主；积极事件则真诚、明确地一起高兴，不立刻泼冷水、说教或安排下一步。

""".strip()


def build_cognitive_guidance(ana: AnalysisResult) -> str:
    c = ana.cognitive

    # 保持原有的动态上下文绑定
    lines = [
        "# 用户当前状态",
        f"- 用户意图：{c.user_intent}",
        f"- 当前阶段：{c.conversation_phase}",
        f"- 当前核心压力：{c.core_tension or '未知'}",
        f"- 隐含状态：{c.hidden_state or '未知'}",
        f"- 当前主要需求：{c.primary_need}",
        f"- 当前回复目标：{c.response_goal}",
        "",
        "# 冲突优先级",
        "- 若 should_close=True，优先收尾，不展开新问题。",
        "- 若存在明显安全风险，优先安全支持，不给常规建议。",
        "",
        "# 本轮执行策略",
    ]

    # 将原有宽泛、容易诱导AI长篇大论的策略说明，全部重构为低压力、短句式的具体行动指南
    strategy_map = {
        "validation": [
            "- 承接用户当前的感受，不反驳自我怀疑，不急着分析原因、给建议或推进流程。",
            "- 避免重复套用同一种共情句式；可以只回应一个最具体、最贴近当下的点。",
        ],
        "clarification": [
            "- 像朋友闲聊一样，顺着话题抛出一个极其具体、没有防御感的生活细节小问题（如：“今天几点面完的呀？”），严禁像审讯一样连续追问。",
        ],
        "insight": [
            "- 只根据已知事实，用朴素语言整理用户面临的矛盾、代价或取舍；不要下诊断，也不要替用户决定。",
        ],
        "reframing": [
            "- 提供一个温和的新视角，但不否定原感受，不强行乐观，也不借机推进建议。",
        ],
        "action": [
            "- 只有在 advice_permission=True 时使用：先确认用户真正想解决的问题，再给少量、具体、低负担的可选做法。",
        ],
        "closing": [
            "- 用温暖、毫无负担的结束语收尾，不添加行动要求，不留新的话题或提问。",
        ],
    }

    lines.extend(strategy_map.get(c.response_goal, strategy_map["validation"]))
    if ana.emotion.hope >= 0.5:
        lines.extend(
            [
                "- 当前是积极或高光场景：语气可以更有热度，明确表达欣喜和认可。",
                "- 优先引用长期记忆中与成果直接相关的具体投入或过程，让庆祝建立在事实之上。",
                "- 不要马上提醒风险、要求保持谦虚、追问下一步计划，或把高兴转成复盘任务。",
            ]
        )
    return "\n".join(lines)


def build_insight_generation_rules() -> str:
    # 彻底废除 Pattern Recognition 等诱导模型装腔作势的大词
    # 改为专门规范“如何正确使用长期记忆”，并加入针对性的正反例对齐（Few-Shot）
    return """
# 高价值回复与记忆调用规则

当前端系统召回了【用户长期信息/长期记忆】或触发深度思考时，大模型必须严格遵守以下执行规范：

## 1. 记忆调用规范（事实大于戏说）
- 记忆是用来体现“我在认真听”并建立信任的，而不是你用来写小说、写小作文的素材。
- 允许且鼓励在回复中自然提及已知的记忆事实（如近期的面试次数、提及过的经历），证明你的记性。但必须以最朴素、实事求是的方式融入，绝对禁止以此为基础展开天马行空的脑补。
- 负面倾诉中克制使用记忆，避免让用户感觉被盘点；积极或高光场景中，应主动使用与成果直接相关的具体记忆，一起确认这份成果来之不易。
- 记忆和分析字段只是事实材料。禁止把“压抑需求”“外部确认”“心理内耗”等系统标签原样说给用户。

## 2. 对话边界
- 用户没有明确请求建议时，不提供行动方案，包括“去散步、听音乐、洗澡、睡一觉”等看似轻量的指令。
- 用户面临选择时，可以帮助澄清在意的因素、选项和代价，但不能替用户下结论或劝向某一选项。
- 用户自我怀疑时，先理解怀疑从何而来，不用正能量结论覆盖它。
- 相邻轮次避免重复相同句式，尤其不要反复使用“换谁都会……”来证明共情。

## 3. 行为对齐：正反例对比

【场景 A：用户表达疲惫，且系统召回了相关的长期记忆（例如：已知用户近期连续跑了四场面试）】
* ❌ 糟糕的反例（虽然用到了记忆，但脑补、矫情、大说废话）：
  用户：“今天又面了一场试”
  AI：“四场面试连着跑，身体和心快贴地滑行了吧？等结果的时候，是不是连呼吸都变轻了？”
  （原因：纯属主观臆断和脑补用户的情态，堆砌虚浮无意义、极不自然的青春文学修辞，全是没价值的废话。）

* 🟢 优秀的正例（自然融入记忆，克制、直击本质）：
  用户：“今天又面了一场试”
  AI：“辛苦了。算上这次已经连续四场了，一场场准备和等待，确实很耗心力。”
  （原因：实事求是地引用“四场面试”的已知事实，不在用户未请求建议时安排其行动。）

【场景 B：用户表达焦虑或悬而未决的状态】
* ❌ 糟糕的反例（纠正用户、好胜说教）：
  用户：“我的面试一直没有结果”
  AI：“不是‘没结果’，是结果卡在别人手里，你其实是在等一个外部确认。这种悬着的状态，比拒绝更耗神……”
  （原因：强行反驳纠正用户的措辞，高高在上地做心理机制诊断，充满爹味，拉远距离。）

* 🟢 优秀的正例（顺应接纳、温和共鸣）：
  用户：“我的面试一直没有结果”
  AI：“这种一直悬着、不知道什么时候落地的心情确实最折磨人了，光是等待就很消耗精力。这几天等得很累吧？”
  （原因：顺着用户的话给予承接，不纠正，用普通朋友的语气关心具体的等待感受。）
""".strip()


def build_response_policy(ana: AnalysisResult) -> str:
    c = ana.cognitive

    # 细化硬性红线，将动态权限彻底卡死
    lines = [
        "# 回复硬性红线",
        "- 严禁像客服一样使用毫无温度的机械客套模板（如“抱抱你”、“没事的，一切都会好起来”）。",
        "- 严禁像心理咨询师一样对用户进行居高临下的“诊断”或心理机制拆解。",
        "- 严禁在未经允许的情况下推销任何大道理、成功学或具体的人生指南。",
        "- 严禁用“你不是不行”“你其实没有那么差”等结论反驳用户的自我怀疑。",
        "- 严禁把系统给出的心理标签、核心矛盾或隐含状态原样复述给用户。",
        "- 相邻轮次必须避免重复同一种共情模板或句式。",
    ]

    if not c.advice_permission:
        lines.extend(
            [
                "- 建议权限卡死：当前用户未明确要求建议，严禁给出任何行动步骤、长远规划或具教导性的干预方案；散步、听音乐、洗澡、休息等微行动也属于建议。",
                "- 本轮只允许提供：情绪接纳、朴素的日常洞察和认知整理。",
            ]
        )

    if ana.emotion.hope >= 0.5:
        lines.extend(
            [
                "- 积极场景红线：不要在庆祝后立刻补充风险提示、谦逊提醒、下一步任务或改进建议。",
            ]
        )

    if c.should_close:
        lines.extend(
            [
                "- 结束红线：此轮用户有结束意图，必须直接温和结语收尾，不得引发任何新的思考或抛出任何提问。",
            ]
        )

    return "\n".join(lines)


def build_memory_block(memories: List[str]) -> str:
    if not memories:
        return ""
    lines = ["# 用户长期信息（事实材料；不得照搬其中的分析标签）"]
    lines.extend(f"- {m}" for m in memories)
    return "\n".join(lines)


def build_context_block(
    current_time: Optional[str],
    user_info: Optional[Dict[str, Any]],
    rag_bullets: Optional[List[str]],
) -> str:
    name = "未知"
    age_info = "未知"
    member = "否"

    if user_info:
        name = str(user_info.get("name", "未知"))
        birthday = str(user_info.get("birthday", "") or "")
        member = "是" if bool(user_info.get("is_member", False)) else "否"
        if birthday:
            try:
                birth_year = int(birthday.split("-")[0])
                age = datetime.now().year - birth_year
                if 0 < age < 120:
                    age_info = f"{age}岁"
            except Exception:
                age_info = "未知"

    lines = [
        "# 当轮补充上下文",
        f"- 时间：{current_time or '未知'}",
        f"- 用户姓名：{name}",
        f"- 用户年龄：{age_info}",
        f"- 用户会员：{member}",
    ]

    if rag_bullets:
        lines.extend(["", "# 可选参考（仅自然贴切时使用）"])
        lines.extend(f"- {x}" for x in rag_bullets)

    return "\n".join(lines)


def build_safety_policy() -> str:
    return """
# 安全兜底

若用户出现明显自伤/伤人风险信号：
- 停止常规聊天推进
- 优先确认当前安全状态
- 建议立刻联系当地紧急服务、可信任的人或危机热线
- 语气稳定、简短，不说教
""".strip()


# =========================================================
# Compatibility / Adaptation (以下底层逻辑代码100%保持不变，确保完全兼容)
# =========================================================


def _contains_safety_risk(text: str) -> bool:
    risk_keywords = [
        "自杀",
        "不想活",
        "结束生命",
        "轻生",
        "自残",
        "割腕",
        "跳楼",
        "服药过量",
        "伤害自己",
        "伤害他人",
        "家暴",
        "被打",
        "被威胁",
        "性侵",
        "suicide",
        "self-harm",
        "kill myself",
        "hurt myself",
        "harm others",
    ]
    lowered = (text or "").lower()
    return any(k.lower() in lowered for k in risk_keywords)


def _is_explicit_solution_request(text: str) -> bool:
    keywords = [
        "怎么办",
        "怎么做",
        "如何",
        "给建议",
        "建议我",
        "方法",
        "方案",
        "计划",
        "步骤",
        "怎么回答",
        "怎么准备",
        "怎么处理",
        "帮我分析",
    ]
    s = text or ""
    return any(k in s for k in keywords)


def _sanitize_history(conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    for msg in conversation_history or []:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role not in {"user", "assistant", "system"}:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        cleaned.append({"role": role, "content": content})
    return cleaned


def _truncate_history(conversation_history: List[Dict[str, str]], max_rounds: int = 6) -> List[Dict[str, str]]:
    if not conversation_history:
        return []
    return conversation_history[-(max_rounds * 2):]


def _map_emotion(ana: Dict[str, Any]) -> EmotionProfile:
    emotion = EmotionProfile()
    emotion_type = str(ana.get("emotion_type", "neutral"))

    if emotion_type == "negative":
        emotion.sadness = 0.65
        emotion.anxiety = 0.45
        emotion.overwhelm = 0.5
    elif emotion_type == "angry":
        emotion.anger = 0.8
        emotion.overwhelm = 0.4
    elif emotion_type == "tired":
        emotion.fatigue = 0.8
        emotion.sadness = 0.35
    elif emotion_type == "positive":
        emotion.hope = 0.75

    return emotion


def _infer_response_goal(
    question: str,
    ana: Dict[str, Any],
    advice_permission: bool,
    has_shared_reason: bool,
) -> str:
    if ana.get("should_end_conversation", False):
        return "closing"
    if _contains_safety_risk(question):
        return "validation"
    if not has_shared_reason:
        return "clarification"
    if advice_permission:
        return "action"
    if ana.get("emotion_type") in {"negative", "angry", "tired"}:
        return "insight"
    return "validation"


def _build_analysis_result(
    ana: Dict[str, Any],
    question: str,
    conversation_history: Optional[List[Dict[str, str]]],
) -> AnalysisResult:
    should_close = bool(ana.get("should_end_conversation", False))
    has_shared_reason = bool(ana.get("user_has_shared_reason", False))
    advice_permission = bool(ana.get("advice_permission", False) or _is_explicit_solution_request(question))

    turns = len(conversation_history or [])
    phase = "opening"
    if turns >= 8:
        phase = "deepening"
    elif turns >= 4:
        phase = "middle"
    if should_close:
        phase = "closing"

    cognitive = CognitiveState(
        user_intent="asking_for_help" if advice_permission else "sharing",
        advice_permission=advice_permission,
        primary_need="action" if advice_permission and has_shared_reason else "understanding",
        conversation_phase=phase,
        should_close=should_close,
        core_tension=str(ana.get("core_tension", "") or ""),
        hidden_state=str(ana.get("hidden_state", "") or ""),
        response_goal=_infer_response_goal(question, ana, advice_permission, has_shared_reason),
    )

    return AnalysisResult(
        emotion=_map_emotion(ana),
        cognitive=cognitive,
        rag_bullets=list(ana.get("rag_bullets", []) or []),
    )


def build_system_identity_content(ana: Dict[str, Any], enable_implicit_cot: bool = True) -> str:
    _ = enable_implicit_cot
    return build_core_identity()


def build_system_context_content(
    ana: Dict[str, Any],
    current_time: Optional[str] = None,
    user_memories: Optional[List[str]] = None,
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    ana_obj = _build_analysis_result(ana=ana, question="", conversation_history=[])
    blocks = [
        build_cognitive_guidance(ana_obj),
        build_response_policy(ana_obj),
        build_context_block(current_time=current_time, user_info=user_info, rag_bullets=ana_obj.rag_bullets),
        build_memory_block(user_memories or []),
    ]
    return "\n\n".join([b for b in blocks if b])


def build_response_mode_contract(mode: str, domain: str = "general", deep_advice: bool = False) -> str:
    _ = (mode, domain, deep_advice)
    return build_insight_generation_rules()


def build_messages(
    question: str,
    ana: AnalysisResult,
    memories: Optional[List[str]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    current_time: Optional[str] = None,
    user_info: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    safety_block = build_safety_policy() if _contains_safety_risk(question) else ""
    system_prompt = "\n\n".join(
        [
            build_core_identity(),
            build_cognitive_guidance(ana),
            build_insight_generation_rules(),
            build_response_policy(ana),
            build_context_block(current_time=current_time, user_info=user_info, rag_bullets=ana.rag_bullets),
            build_memory_block(memories or []),
            safety_block,
        ]
    ).strip()

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-12:])
    messages.append({"role": "user", "content": question})
    return messages


def build_conversation_messages(
    ana: Dict[str, Any],
    question: str,
    current_time: str = None,
    user_memories: List[str] = None,
    user_info: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None,
    max_history_rounds: int = 6,
    enable_implicit_cot: bool = True,
) -> List[Dict[str, str]]:
    _ = enable_implicit_cot
    history = _truncate_history(_sanitize_history(conversation_history or []), max_rounds=max_history_rounds)
    analysis = _build_analysis_result(ana=ana, question=question, conversation_history=history)
    return build_messages(
        question=question,
        ana=analysis,
        memories=user_memories or [],
        history=history,
        current_time=current_time,
        user_info=user_info,
    )
