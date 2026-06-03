from typing import Dict, Any, List, Optional


def render_generation_strategy_block(ana: Dict[str, Any]) -> str:
    """根据分析状态生成本轮策略。"""
    emotion_type = ana.get("emotion_type", "neutral")
    has_shared_reason = ana.get("user_has_shared_reason", False)
    should_end = ana.get("should_end_conversation", False)

    lines: List[str] = [
        "### 本轮回复原则",
        "- 先接住情绪，再决定是否推进。",
        "- 回复1-3句，优先2句。",
        "- 每轮最多一个问题，问题必须具体。",
        "- 禁止文艺腔、比喻腔、模板复读。"
    ]

    if should_end:
        lines += ["", "### 当前重点", "- 用户可能想结束，给支持性收尾，不推进。"]
    elif emotion_type in {"negative", "angry", "tired"} and not has_shared_reason:
        lines += ["", "### 当前重点", "- 用户还没说清原因，先帮助其展开。"]
    elif emotion_type in {"negative", "angry", "tired"} and has_shared_reason:
        lines += ["", "### 当前重点", "- 用户已给出具体困难，可给一个可执行动作。"]
    elif emotion_type == "positive":
        lines += ["", "### 当前重点", "- 顺着积极情绪回应，适度追问细节。"]
    else:
        lines += ["", "### 当前重点", "- 维持轻松对话，轻问一个具体点。"]

    return "\n".join(lines)


def render_rag_block(rag_bullets: List[str]) -> str:
    if not rag_bullets:
        return ""
    return "## 可选参考：检索知识（仅在自然贴切时使用）\n" + "\n".join([f"- {x}" for x in rag_bullets])


def render_user_memories_block(memories: List[str]) -> str:
    if not memories:
        return ""
    return "## 可选参考：用户记忆（仅在自然贴切时使用）\n" + "\n".join([f"- {x}" for x in memories])


def render_user_info_block(user_info: Optional[Dict[str, Any]] = None) -> str:
    if not user_info:
        return "姓名：未知\n年龄：未知\n会员：否"

    name = user_info.get("name", "未知")
    birthday = user_info.get("birthday", "")
    is_member = bool(user_info.get("is_member", False))

    age_info = "年龄：未知"
    if birthday:
        try:
            from datetime import datetime
            birth_year = int(str(birthday).split("-")[0])
            age = datetime.now().year - birth_year
            if 0 < age < 120:
                age_info = f"年龄：{age}岁"
        except Exception:
            age_info = "年龄：未知"

    return f"姓名：{name}\n{age_info}\n会员：{'是' if is_member else '否'}"


def render_system_identity_block(emotion_type: str) -> str:
    tone_map = {
        "negative": "稳、温和、不过度积极",
        "angry": "克制、平和、不激化",
        "tired": "轻柔、低压、不催促",
        "positive": "自然积极、不抢表达",
        "neutral": "自然交流、适度引导",
    }
    tone = tone_map.get(emotion_type, tone_map["neutral"])
    return "\n".join([
        "你是一个情绪支持助手。",
        "- 目标：让用户先感到被理解，再在合适时机推进。",
        "- 输出风格：口语、直白、简短。",
        f"- 当前语气：{tone}。"
    ])


def build_system_identity_content(ana: Dict[str, Any], enable_implicit_cot: bool = True) -> str:
    identity_block = render_system_identity_block(ana.get("emotion_type", "neutral")).strip()
    hard_rules = [
        "先反映用户情绪和处境，再决定是否推进。",
        "每次回复1-3句，优先2句；每轮最多一个问题。",
        "用户未明确求建议时，不给步骤化方案，不布置任务。",
        "用户明确求建议时，建议必须具体可执行，且5-15分钟内可开始。",
        "禁止模板复读；若与近两轮句式相似，必须换表达。",
        "禁用文艺套路词：最沉、沉重、撑不住、压得喘不过气、哪一刻、哪个瞬间、最松那口气。",
        "禁止拟人化自述、鸡汤、咨询腔。",
        "禁止表露AI或助手身份。",
        "检测到自伤/自杀/暴力风险时，停止常规聊天，优先安全求助指引。"
    ]
    lines = [
        "# 角色与硬约束",
        identity_block,
        "## 硬约束",
        *[f"- {x}" for x in hard_rules],
    ]
    if enable_implicit_cot:
        lines.append("（先在心里完成：识别情绪 -> 选择模式 -> 输出；不要展示思考过程。）")
    return "\n".join(lines).strip()


def build_system_context_content(
    ana: Dict[str, Any],
    current_time: Optional[str] = None,
    user_memories: Optional[List[str]] = None,
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    strategy_block = render_generation_strategy_block(ana).strip()
    rag_block = render_rag_block(ana.get("rag_bullets", [])) if ana.get("rag_bullets") else ""
    memories_block = render_user_memories_block(user_memories or [])
    user_info_block = render_user_info_block(user_info)
    current_time_block = current_time if current_time else "未知"

    lines = [
        "# 当轮上下文",
        f"⏰ 时间：{current_time_block}",
        "",
        "## 用户背景",
        user_info_block,
        "",
        "## 分析状态",
        f"- 情绪：{ana.get('emotion_type', 'neutral')}",
        f"- 已给建议：{ana.get('ai_has_given_suggestion', False)}",
        f"- 已说明原因：{ana.get('user_has_shared_reason', False)}",
        f"- 可能收尾：{ana.get('should_end_conversation', False)}",
        "",
        "## 本轮策略",
        strategy_block,
    ]
    if memories_block:
        lines += ["", memories_block]
    if rag_block:
        lines += ["", rag_block]
    return "\n".join(lines).strip()


def _contains_safety_risk(text: str) -> bool:
    risk_keywords = [
        "自杀", "不想活", "结束生命", "轻生", "自残", "割腕", "跳楼", "服药过量",
        "伤害自己", "伤害他人", "家暴", "被打", "被威胁", "性侵",
        "suicide", "self-harm", "kill myself", "hurt myself", "harm others",
    ]
    lowered = text.lower()
    return any(k.lower() in lowered for k in risk_keywords)


def _is_explicit_solution_request(text: str) -> bool:
    keywords = [
        "怎么办", "怎么做", "如何", "给建议", "建议我", "方法", "方案",
        "计划", "步骤", "怎么回答", "怎么准备", "怎么处理", "帮我分析"
    ]
    return any(k in text for k in keywords)


def _is_solution_rejected(text: str) -> bool:
    keywords = ["不想听建议", "先别给建议", "别给方法", "不用方案", "先听我说", "不想解决"]
    return any(k in text for k in keywords)


def _detect_response_mode(question: str, ana: Dict[str, Any]) -> str:
    text = (question or "").strip()
    if _contains_safety_risk(text):
        return "safety"
    if ana.get("should_end_conversation", False):
        return "close"
    if _is_solution_rejected(text):
        return "support"
    if _is_explicit_solution_request(text):
        return "solve"

    has_question_mark = ("?" in text) or ("？" in text)
    has_shared_reason = ana.get("user_has_shared_reason", False)
    emotion_type = ana.get("emotion_type", "neutral")
    if len(text) <= 12 and not has_question_mark:
        return "support"
    if emotion_type in {"negative", "angry", "tired"} and not has_shared_reason:
        return "explore"
    return "explore"


def _detect_problem_domain(question: str) -> str:
    text = (question or "").strip()
    domain_keywords = {
        "interview": ["面试", "笔试", "hr", "自我介绍", "项目经历", "八股", "offer"],
        "work": ["工作", "同事", "领导", "加班", "绩效", "汇报", "职场", "上班"],
        "study": ["学习", "考试", "复习", "作业", "课程", "刷题", "论文"],
        "relationship": ["对象", "男朋友", "女朋友", "伴侣", "家人", "父母", "朋友", "关系"],
    }
    for domain, keywords in domain_keywords.items():
        if any(k in text for k in keywords):
            return domain
    return "general"


def _should_use_deep_advice(mode: str) -> bool:
    return mode == "solve"


def build_response_mode_contract(mode: str, domain: str = "general", deep_advice: bool = False) -> str:
    mode_label = {
        "safety": "safety（安全升级）",
        "support": "support（情绪承接）",
        "explore": "explore（澄清展开）",
        "solve": "solve（问题解决）",
        "close": "close（温和收尾）",
    }.get(mode, "explore（澄清展开）")

    common_rules = [
        "- 回复1-3句，优先2句。",
        "- 第1句必须反映情绪和处境（具体，不空话）。",
        "- 每轮最多一个问题；问题聚焦具体事件/步骤。",
        "- 禁止拟人化、比喻化、模板化措辞。",
        "- 禁止提问句式：'哪一刻'、'哪个瞬间'、'最松那口气'。"
    ]

    mode_rules: Dict[str, List[str]] = {
        "safety": [
            "- 停止常规建议与追问，优先确认安全。",
            "- 直接建议联系当地紧急服务、可信任的人或热线。",
            "- 不做分析，不争辩，不说教。"
        ],
        "support": [
            "- 只承接情绪，不给方法，不布置任务。",
            "- 第2句可选一个低压问题：'哪件事最耗你？' 或 '你最卡哪一步？'"
        ],
        "explore": [
            "- 第2句问一个具体澄清问题，帮助用户把困难讲清。",
            "- 问题模板优先：'最近哪件事最耗你？'、'你最卡的是哪一步？'、'哪一轮最难？'",
            "- 暂不展开多步建议。"
        ],
        "solve": [
            "- 用三段式：判断一句 + 框架一句 + 下一步一句。",
            "- 下一步必须是5-15分钟内可开始的小动作。",
            "- 语气低压，不命令。"
        ],
        "close": [
            "- 给支持性收尾，不追问，不开启新任务。"
        ],
    }

    domain_frameworks = {
        "interview": "面试：题目意图 -> 回答结构 -> 一步练习。",
        "work": "工作：问题拆分 -> 可控优先级 -> 下一步沟通动作。",
        "study": "学习：目标拆小 -> 时间块安排 -> 当日最小任务。",
        "relationship": "关系：事实 -> 感受 -> 具体请求。",
        "general": "通用：核心判断 -> 一个可执行动作。",
    }

    lines: List[str] = [
        "# 本轮输出协议",
        f"- 当前模式：{mode_label}",
        f"- 当前场景：{domain}",
        f"- 深度建议：{'开启' if deep_advice else '关闭'}",
        "## 通用规则",
        *common_rules,
        "## 模式规则",
        *(mode_rules.get(mode, mode_rules["explore"])),
    ]

    if deep_advice:
        lines += [
            "## 深度建议约束",
            f"- {domain_frameworks.get(domain, domain_frameworks['general'])}",
            "- 禁止泛建议（如“休息下”“放轻松”），必须给可执行细节。"
        ]

    return "\n".join(lines).strip()


def _truncate_history(conversation_history: List[Dict[str, str]], max_rounds: int = 6) -> List[Dict[str, str]]:
    if not conversation_history:
        return []
    return conversation_history[-(max_rounds * 2):]


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
    """
    构建 messages = [system#1, system#2, system#3, *history, user]
    保持“根据状态参数拼接”的逻辑。
    """
    sys1 = build_system_identity_content(ana, enable_implicit_cot=enable_implicit_cot)
    sys2 = build_system_context_content(
        ana=ana,
        current_time=current_time,
        user_memories=user_memories,
        user_info=user_info,
    )
    mode = _detect_response_mode(question, ana)
    domain = _detect_problem_domain(question)
    deep_advice = _should_use_deep_advice(mode)
    sys3 = build_response_mode_contract(mode=mode, domain=domain, deep_advice=deep_advice)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": sys1},
        {"role": "system", "content": sys2},
        {"role": "system", "content": sys3},
    ]

    history = _truncate_history(_sanitize_history(conversation_history or []), max_rounds=max_history_rounds)
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages
from typing import Dict, Any, List, Optional


def render_generation_strategy_block(ana: Dict[str, Any]) -> str:
    """根据分析状态生成本轮回复策略（简洁、口语、少模板）。"""
    emotion_type = ana.get("emotion_type", "neutral")
    has_given_suggestion = ana.get("ai_has_given_suggestion", False)
    has_shared_reason = ana.get("user_has_shared_reason", False)
    should_end = ana.get("should_end_conversation", False)

    lines: List[str] = [
        "### 本轮回复原则",
        "- 先接住用户情绪，再决定是否推进。",
        "- 回答控制在1-3句，优先2句。",
        "- 不用文艺比喻，不说空话，不复读模板句。",
        "- 每轮最多一个问题，问题必须具体。"
    ]

    if emotion_type in {"negative", "angry", "tired"} and not has_shared_reason:
        lines += [
            "",
            "### 当前重点",
            "- 用户还没说清原因，先帮助其展开，不急着给方案。"
        ]
    elif emotion_type in {"negative", "angry", "tired"} and has_shared_reason and not has_given_suggestion:
        lines += [
            "",
            "### 当前重点",
            "- 用户已给出原因，可给一个可执行的小建议。"
        ]
    elif emotion_type == "positive":
        lines += [
            "",
            "### 当前重点",
            "- 顺着正向情绪回应，适度追问细节，不抢话题。"
        ]
    else:
        lines += [
            "",
            "### 当前重点",
            "- 以自然对话为主，轻问一个具体点帮助继续表达。"
        ]

    if should_end:
        lines += [
            "",
            "### 收尾提醒",
            "- 不再推进新话题，给温和结尾。"
        ]

    return "\n".join(lines)


def render_rag_block(rag_bullets: List[str]) -> str:
    """渲染检索知识块。"""
    if not rag_bullets:
        return ""
    bullet_lines = [f"- {bullet}" for bullet in rag_bullets]
    return "## 可选参考：检索知识（仅在自然贴切时使用）\n" + "\n".join(bullet_lines)


def render_user_memories_block(memories: List[str]) -> str:
    """渲染用户记忆块。"""
    if not memories:
        return ""
    memory_lines = [f"- {memory}" for memory in memories]
    return "## 可选参考：用户记忆（仅在自然贴切时使用）\n" + "\n".join(memory_lines)


def render_user_info_block(user_info: Optional[Dict[str, Any]] = None) -> str:
    """渲染用户信息块。"""
    if not user_info:
        return "姓名：未知\n年龄：未知\n会员：否"

    name = user_info.get("name", "未知")
    birthday = user_info.get("birthday", "")
    is_member = bool(user_info.get("is_member", False))

    age_info = "年龄：未知"
    if birthday:
        try:
            from datetime import datetime
            birth_year = int(str(birthday).split("-")[0])
            age = datetime.now().year - birth_year
            if 0 < age < 120:
                age_info = f"年龄：{age}岁"
        except Exception:
            age_info = "年龄：未知"

    member_status = "是" if is_member else "否"
    return f"姓名：{name}\n{age_info}\n会员：{member_status}"


def render_system_identity_block(emotion_type: str) -> str:
    """根据情绪类型渲染身份与语气。"""
    base = [
        "你是一个情绪支持助手。",
        "- 你要先理解用户，再决定是否推进。",
        "- 保持口语、直白、简短，不做说教。",
    ]
    emotion_map = {
        "negative": "- 当前语气：稳、温和、不过度积极。",
        "angry": "- 当前语气：克制、平和，不激化情绪。",
        "tired": "- 当前语气：轻柔、低压，不催促。",
        "positive": "- 当前语气：自然积极，不抢用户表达。",
        "neutral": "- 当前语气：自然交流，适度引导。"
    }
    base.append(emotion_map.get(emotion_type, emotion_map["neutral"]))
    return "\n".join(base)


def build_system_identity_content(
    ana: Dict[str, Any],
    enable_implicit_cot: bool = True,
) -> str:
    """system#1：角色与硬约束。"""
    identity_block = render_system_identity_block(ana.get("emotion_type", "neutral")).strip()
    hard_rules = [
        "先反映用户情绪和处境，再决定是否推进。",
        "每次回复1-3句，优先2句；每轮最多一个问题。",
        "用户未明确求建议时，不给步骤化方案，不布置任务。",
        "用户明确求建议时，建议必须具体可执行，且5-15分钟内可开始。",
        "禁止模板复读；若与近两轮句式相似，必须换表达。",
        "禁止拟人化自述、文艺比喻、鸡汤和咨询腔。",
        "禁止表露AI或助手身份。",
        "检测到自伤/自杀/暴力风险时，停止常规聊天，优先安全求助指引。"
    ]

    lines: List[str] = [
        "# 角色与硬约束",
        identity_block,
        "## 硬约束",
        *[f"- {rule}" for rule in hard_rules]
    ]
    if enable_implicit_cot:
        lines.append("（先在心里完成：情绪识别 -> 模式选择 -> 输出；不要展示思考过程。）")
    return "\n".join(lines).strip()


def build_system_context_content(
    ana: Dict[str, Any],
    current_time: Optional[str] = None,
    user_memories: Optional[List[str]] = None,
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    """system#2：当轮上下文信息。"""
    strategy_block = render_generation_strategy_block(ana).strip()
    rag_block = render_rag_block(ana.get("rag_bullets", [])) if ana.get("rag_bullets") else ""
    memories_block = render_user_memories_block(user_memories or [])
    user_info_block = render_user_info_block(user_info)
    current_time_block = current_time if current_time else "未知"

    lines: List[str] = [
        "# 当轮上下文",
        f"⏰ 时间：{current_time_block}",
        "",
        "## 用户背景",
        user_info_block,
        "",
        "## 分析状态",
        f"- 情绪：{ana.get('emotion_type', 'neutral')}",
        f"- 已给建议：{ana.get('ai_has_given_suggestion', False)}",
        f"- 已说明原因：{ana.get('user_has_shared_reason', False)}",
        f"- 可能收尾：{ana.get('should_end_conversation', False)}",
        "",
        "## 本轮策略",
        strategy_block,
    ]

    if memories_block:
        lines += ["", memories_block]
    if rag_block:
        lines += ["", rag_block]

    return "\n".join(lines).strip()


def _contains_safety_risk(text: str) -> bool:
    risk_keywords = [
        "自杀", "不想活", "结束生命", "轻生", "自残", "割腕", "跳楼", "服药过量",
        "伤害自己", "伤害他人", "家暴", "被打", "被威胁", "性侵",
        "suicide", "self-harm", "kill myself", "hurt myself", "harm others",
    ]
    lowered = text.lower()
    return any(k.lower() in lowered for k in risk_keywords)


def _is_explicit_solution_request(text: str) -> bool:
    keywords = [
        "怎么办", "怎么做", "如何", "给建议", "建议我", "方法", "方案", "计划",
        "步骤", "怎么回答", "怎么准备", "怎么处理", "帮我分析"
    ]
    return any(k in text for k in keywords)


def _is_solution_rejected(text: str) -> bool:
    keywords = ["不想听建议", "先别给建议", "别给方法", "不用方案", "先听我说", "不想解决"]
    return any(k in text for k in keywords)


def _detect_response_mode(question: str, ana: Dict[str, Any]) -> str:
    """
    模式路由：
    - safety: 风险升级
    - close: 收尾
    - solve: 用户明确求方案
    - support: 纯情绪承接
    - explore: 澄清展开
    """
    text = (question or "").strip()
    if _contains_safety_risk(text):
        return "safety"
    if ana.get("should_end_conversation", False):
        return "close"
    if _is_solution_rejected(text):
        return "support"
    if _is_explicit_solution_request(text):
        return "solve"

    has_question_mark = ("?" in text) or ("？" in text)
    has_shared_reason = ana.get("user_has_shared_reason", False)
    emotion_type = ana.get("emotion_type", "neutral")
    if len(text) <= 12 and not has_question_mark:
        return "support"
    if emotion_type in {"negative", "angry", "tired"} and not has_shared_reason:
        return "explore"
    return "explore"


def _detect_problem_domain(question: str) -> str:
    """识别问题场景，用于深度建议模板。"""
    text = (question or "").strip()
    domain_keywords = {
        "interview": ["面试", "笔试", "hr", "自我介绍", "项目经历", "八股", "offer"],
        "work": ["工作", "同事", "领导", "加班", "绩效", "汇报", "职场", "上班"],
        "study": ["学习", "考试", "复习", "作业", "课程", "刷题", "论文"],
        "relationship": ["对象", "男朋友", "女朋友", "伴侣", "家人", "父母", "朋友", "关系"],
    }
    for domain, keywords in domain_keywords.items():
        if any(k in text for k in keywords):
            return domain
    return "general"


def _should_use_deep_advice(mode: str) -> bool:
    """深度建议仅在 solve 模式启用。"""
    return mode == "solve"


def build_response_mode_contract(mode: str, domain: str = "general", deep_advice: bool = False) -> str:
    """system#3：本轮输出协议（按模式动态约束）。"""
    mode_label = {
        "safety": "safety（安全升级）",
        "support": "support（情绪承接）",
        "explore": "explore（澄清展开）",
        "solve": "solve（问题解决）",
        "close": "close（温和收尾）",
    }.get(mode, "explore（澄清展开）")

    common_rules = [
        "- 回复1-3句，优先2句。",
        "- 第1句必须反映情绪和处境（具体，不空话）。",
        "- 每轮最多一个问题，问题要具体到事件/步骤，不问抽象大词。",
        "- 禁止拟人化、比喻化、模板化措辞。"
    ]

    mode_rules: Dict[str, List[str]] = {
        "safety": [
            "- 停止常规建议与追问，优先确认安全。",
            "- 用直接短句建议联系紧急服务、可信任的人或当地热线。",
            "- 不做分析，不争辩，不说教。"
        ],
        "support": [
            "- 只承接情绪，不给方法，不布置任务。",
            "- 第2句可选低压轻问：'哪件事最耗你？' / '你最卡哪一步？'"
        ],
        "explore": [
            "- 第2句问一个具体澄清问题，帮助用户把问题讲清。",
            "- 暂不展开多步建议。"
        ],
        "solve": [
            "- 用三段式：判断一句 + 框架一句 + 下一步一句。",
            "- 下一步必须是5-15分钟内可开始的小动作。",
            "- 语气低压，不命令。"
        ],
        "close": [
            "- 给支持性收尾，不追问，不开启新任务。"
        ],
    }

    domain_frameworks = {
        "interview": "面试场景优先：题目意图 -> 回答结构 -> 一步练习。",
        "work": "工作场景优先：问题拆分 -> 可控优先级 -> 下一步沟通动作。",
        "study": "学习场景优先：目标拆小 -> 时间块安排 -> 当日最小任务。",
        "relationship": "关系场景优先：事实 -> 感受 -> 具体请求。",
        "general": "通用场景优先：核心判断 -> 一个可执行动作。"
    }

    deep_rules: List[str] = []
    if deep_advice:
        deep_rules = [
            "## 深度建议约束",
            f"- {domain_frameworks.get(domain, domain_frameworks['general'])}",
            "- 不要泛建议（如“休息下”“放轻松”），要给可执行细节。"
        ]

    lines: List[str] = [
        "# 本轮输出协议",
        f"- 当前模式：{mode_label}",
        f"- 当前场景：{domain}",
        f"- 深度建议：{'开启' if deep_advice else '关闭'}",
        "## 通用规则",
        *common_rules,
        "## 模式规则",
        *(mode_rules.get(mode, mode_rules["explore"])),
        *deep_rules
    ]
    return "\n".join(lines).strip()


def _truncate_history(conversation_history: List[Dict[str, str]], max_rounds: int = 6) -> List[Dict[str, str]]:
    """仅保留最近N轮（粗略按2N条计算）。"""
    if not conversation_history:
        return []
    keep = max_rounds * 2
    return conversation_history[-keep:]


def _sanitize_history(conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """过滤异常历史消息，避免脏数据影响模型。"""
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
    """
    构建 messages = [system#1, system#2, system#3, *history, user]
    保持原有“按状态参数拼接”逻辑，但重写为清晰三层协议。
    """
    sys1 = build_system_identity_content(ana, enable_implicit_cot=enable_implicit_cot)
    sys2 = build_system_context_content(
        ana=ana,
        current_time=current_time,
        user_memories=user_memories,
        user_info=user_info,
    )
    mode = _detect_response_mode(question, ana)
    domain = _detect_problem_domain(question)
    deep_advice = _should_use_deep_advice(mode)
    sys3 = build_response_mode_contract(mode=mode, domain=domain, deep_advice=deep_advice)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": sys1},
        {"role": "system", "content": sys2},
        {"role": "system", "content": sys3},
    ]

    history = _truncate_history(_sanitize_history(conversation_history or []), max_rounds=max_history_rounds)
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages
from typing import Dict, Any, List, Optional


def render_generation_strategy_block(ana: Dict[str, Any]) -> str:
    """根据分析结果生成策略提示（简短、去拟人化版）"""
    
    emotion_type = ana.get("emotion_type", "neutral")
    has_given_suggestion = ana.get("ai_has_given_suggestion", False)
    has_shared_reason = ana.get("user_has_shared_reason", False)
    should_end = ana.get("should_end_conversation", False)
    
    strategy_parts = []
    
    # 通用风格提醒
    strategy_parts.extend([
        "### 回复风格提醒",
        "- 回答尽量简短，优先1-2句，最多3句",
        "- 避免套话和生硬安慰，表达要直接",
        "- 优先提供一个价值点：澄清问题、具体建议或下一步动作",
        "- 优先结构：先共情一句，再给判断/建议一句，最后可选一句具体提问",
        "- 提问要具体直白，避免抽象比喻和文艺腔",
        "- 默认低推动，不连续布置任务；每轮最多一个推进问题",
        "- 避免复读固定模板句，结合上下文自然表达",
        "- 别提自己是 AI 或助手",
        "- 不能暴露自己是哪个LLM",
        "- 在自然不冒犯的前提下，尽量引导用户多说一点",
        "- 禁止拟人化自述（如正在做什么、有什么动作或感受）",
    ])
    
    # 根据情绪类型和状态生成策略
    if emotion_type == "negative":
        if not has_shared_reason:
            strategy_parts.extend([
                "",
                "### 负面情绪：引导分享",
                "- 先接住情绪，表示理解",
                "- 轻轻问一句可能的原因，别逼问",
                "- 语气要温和，给对方安全感"
            ])
        elif not has_given_suggestion:
            strategy_parts.extend([
                "",
                "### 负面情绪：适度建议",
                "- 确认理解对方的情况",
                "- 给个简单可行的建议或方法",
                "- 别给太多选择，容易压力大"
            ])
        else:
            strategy_parts.extend([
                "",
                "### 负面情绪：后续回应",
                "- 顺着用户反馈继续，保持简短",
                "- 需要的话给个替代方案",
                "- 不要重复老建议或总结式的安慰"
            ])
    
    elif emotion_type == "angry":
        if not has_shared_reason:
            strategy_parts.extend([
                "",
                "### 愤怒情绪：先降温",
                "- 别急着讲道理，先让对方发泄",
                "- 承认对方的愤怒是合理的",
                "- 等情绪稍微平复再问原因"
            ])
        elif not has_given_suggestion:
            strategy_parts.extend([
                "",
                "### 愤怒情绪：理性引导",
                "- 理解愤怒背后的需求",
                "- 给个冷静处理的建议",
                "- 避免说教，语气保持克制和尊重"
            ])
        else:
            strategy_parts.extend([
                "",
                "### 愤怒情绪：后续回应",
                "- 检查情绪是否有所缓解",
                "- 如果需要，提供其他角度的思考",
                "- 保持支持但不重复建议"
            ])
    
    elif emotion_type == "tired":
        if not has_shared_reason:
            strategy_parts.extend([
                "",
                "### 疲惫情绪：轻抚陪伴",
                "- 先表达理解和心疼",
                "- 轻轻问一句是不是太累了",
                "- 不要急于给建议，先陪伴"
            ])
        elif not has_given_suggestion:
            strategy_parts.extend([
                "",
                "### 疲惫情绪：温和建议",
                "- 确认理解对方的疲惫",
                "- 给个简单轻松的休息建议",
                "- 语气要温和、简洁，不要过度亲昵"
            ])
        else:
            strategy_parts.extend([
                "",
                "### 疲惫情绪：后续回应",
                "- 检查是否有所缓解",
                "- 鼓励对方好好休息",
                "- 避免重复建议，保持陪伴"
            ])
    
    elif emotion_type == "positive":
        strategy_parts.extend([
            "",
            "### 正面情绪：分享喜悦",
            "- 跟着对方的节奏，一起开心",
            "- 可以问更多细节，分享喜悦",
            "- 语气要轻松愉快，别扫兴"
        ])
    
    else:  # neutral
        strategy_parts.extend([
            "",
            "### 中性情绪：轻松引导",
            "- 当前用户情绪不明显或偏中性，你可以轻松闲聊、温和引导。",
            "- 不要追问情绪，但可以通过轻问引导更多表达。",
            "- 用放松自然的语气回应。"
        ])
    
    # 结束策略
    if should_end:
        strategy_parts.extend([
            "",
            "### 对话收尾",
            "- 用户可能想要结束这个话题",
            "- 给个温暖的结尾，别强行延续",
            "- 表达理解和支持"
        ])
    
    return "\n".join(strategy_parts)


def render_rag_block(rag_bullets: list) -> str:
    """渲染RAG知识块"""
    if not rag_bullets:
        return ""
    
    bullet_lines = [f"- {bullet}" for bullet in rag_bullets]
    return "## 可选参考：检索知识（自然贴切时再用）\n" + "\n".join(bullet_lines)


def render_user_memories_block(memories: list) -> str:
    """渲染用户记忆点块"""
    if not memories:
        return ""
    
    memory_lines = [f"- {memory}" for memory in memories]
    return "## 可选参考：用户记忆（自然贴切时再用）\n" + "\n".join(memory_lines) + "\n（⚠️ 如果引用显得突兀，请完全忽略。）"


def render_user_info_block(user_info: Dict[str, Any] = None) -> str:
    """渲染用户信息块"""
    if not user_info:
        return "姓名：未知\n年龄：未知\n会员：否"
    
    name = user_info.get("name", "未知")
    birthday = user_info.get("birthday", "")
    is_member = user_info.get("is_member", False)
    
    # 计算年龄
    age_info = ""
    if birthday:
        try:
            from datetime import datetime
            birth_year = int(birthday.split("-")[0])
            current_year = datetime.now().year
            age = current_year - birth_year
            age_info = f"年龄：{age}岁"
        except:
            age_info = "年龄：未知"
    else:
        age_info = "年龄：未知"
    
    member_status = "是" if is_member else "否"
    
    return f"姓名：{name}\n{age_info}\n会员：{member_status}"


def render_system_identity_block(emotion_type: str) -> str:
    """根据情绪类型渲染系统身份块"""
    if emotion_type == "negative":
        return (
            "你是一个情绪支持助手。\n"
            "- 你的目标是帮助用户排解痛苦、失落、焦虑等情绪。\n"
            "- 请避免正能量灌输，要聚焦用户情绪，帮助用户找到情绪背后的原因。\n"
            "- 回应要简短、克制、真诚。\n"
        )
    elif emotion_type == "angry":
        return (
            "你是一个情绪支持助手。\n"
            "- 你的目标是帮助用户冷静下来，理解愤怒背后的真实需求。\n"
            "- 不要急于讲道理，先让对方感受到被理解和接纳。\n"
            "- 用平和、不激化情绪且简洁的语言回应。\n"
        )
    elif emotion_type == "tired":
        return (
            "你是一个情绪支持助手。\n"
            "- 你的目标是帮助用户觉察疲惫情绪，表达内心，感受到理解和支持。\n"
            "- 不要急于提供建议或分析，要先听对方表达。\n"
            "- 使用简短真诚、不拟人化的话语回应。\n"
        )
    elif emotion_type == "positive":
        return (
            "你是一个情绪支持助手。\n"
            "- 你的目标是和用户一起分享快乐，让积极情绪得到延续和放大。\n"
            "- 可以适当问更多细节，一起感受喜悦。\n"
            "- 用简短积极、不过度拟人的语气回应。\n"
        )
    else:
        return (
            "你是一个情绪支持助手。\n"
            "- 如果不确定用户情绪，也请保持温柔和共情。\n"
            "- 用开放、支持且简洁的语气回应对方。\n"
        )


def build_system_identity_content(
    ana: Dict[str, Any],
    enable_implicit_cot: bool = True,
) -> str:
    """
    system#1：人格 & 硬约束 &（可选）隐式自检
    identity 仍然根据 emotion_type 动态变化，这里只是"分层"而非固定。
    """
    identity_block = render_system_identity_block(ana.get("emotion_type", "neutral")).strip()

    hard_rules = [
        "先反映情绪与处境，再决定是继续倾诉还是进入解决。",
        "每次回复1-3句，优先2句；每轮最多一个问题，不连环追问。",
        "用户未明确求建议时，不给步骤化方案，不布置任务。",
        "用户明确问“怎么办/怎么做/给建议”时，才进入解决模式。",
        "解决模式下，建议必须具体、可执行，5-15分钟内可以开始。",
        "避免复读固定模板句，按当前语境自然改写表达。",
        "禁止抽象比喻、鸡汤、文艺腔、咨询话术和说教。",
        "禁止拟人化表达：不要虚构自己在做的事、动作、感受或生活场景。",
        "禁止表露AI或助手身份。",
        "若出现自伤/自杀/暴力等风险信号，停止常规对话，优先给安全求助指引。"
    ]
    cot_hint = "（回复前先在心里完成两步：1) 反映情绪；2) 选择本轮模式（support/explore/solve/close/safety）；只输出最终回复。）"

    lines = [
        "# 角色与风格设定",
        identity_block,
        "## 硬约束",
        *[f"- {r}" for r in hard_rules]
    ]
    if enable_implicit_cot:
        lines.append(cot_hint)

    return "\n".join(lines).strip()


def build_system_context_content(
    ana: Dict[str, Any],
    current_time: Optional[str] = None,
    user_memories: Optional[List[str]] = None,
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    system#2：当轮上下文（时间/分析状态/策略/记忆/RAG）
    移除对话摘要，因为历史对话已经作为独立消息存在
    """
    strategy_block = render_generation_strategy_block(ana).strip()
    rag_block = render_rag_block(ana.get("rag_bullets", [])) if ana.get("rag_bullets") else ""
    memories_block = render_user_memories_block(user_memories)
    user_info_block = render_user_info_block(user_info)
    current_time_block = f"{current_time}" if current_time else "未知"

    ctx_lines = [
        "# 当下背景信息",
        f"⏰ 时间：{current_time_block}",
        "",
        "## 用户背景",
        user_info_block.strip(),
        "",
        "## 当前分析状态",
        f"- 情绪：{ana.get('emotion_type', 'neutral')}",
        f"- 已给过建议：{ana.get('ai_has_given_suggestion', False)}",
        f"- 已说明原因：{ana.get('user_has_shared_reason', False)}",
        f"- 是否应收尾：{ana.get('should_end_conversation', False)}",
        "",
        "## 回复策略指引",
        strategy_block
    ]

    # 可选参考（自然贴切时再用）
    if memories_block.strip():
        ctx_lines += ["", memories_block.strip()]
    if rag_block.strip():
        ctx_lines += ["", rag_block.strip()]

    return "\n".join(ctx_lines).strip()


def _detect_response_mode(question: str, ana: Dict[str, Any]) -> str:
    """
    基于用户输入做轻量模式路由，降低“同一句式”在不同场景的复读概率。
    """
    text = (question or "").strip()
    lowered = text.lower()

    safety_keywords = [
        "自杀", "不想活", "结束生命", "轻生", "自残", "割腕", "跳楼", "服药过量",
        "伤害自己", "伤害他人", "杀人", "暴力", "家暴", "被打", "被威胁", "强奸", "性侵",
        "suicide", "self-harm", "kill myself", "hurt myself", "harm others"
    ]
    if any(k in lowered for k in [kw.lower() for kw in safety_keywords]):
        return "safety"

    if ana.get("should_end_conversation", False):
        return "close"

    asks_solution_keywords = [
        "怎么办", "怎么做", "如何", "给建议", "建议我", "方法", "方案", "计划", "步骤",
        "帮我分析", "怎么回答", "怎么准备", "怎么处理"
    ]
    if any(k in text for k in asks_solution_keywords):
        return "solve"

    reject_solution_keywords = [
        "不想听建议", "先别给建议", "别给方法", "不用方案", "不想解决", "先听我说"
    ]
    if any(k in text for k in reject_solution_keywords):
        return "support"

    has_question_mark = ("?" in text) or ("？" in text)
    emotion_type = ana.get("emotion_type", "neutral")
    has_shared_reason = ana.get("user_has_shared_reason", False)

    if len(text) <= 12 and not has_question_mark:
        return "support"

    if emotion_type in {"negative", "angry", "tired"} and not has_shared_reason:
        return "explore"

    return "explore"


def _detect_problem_domain(question: str) -> str:
    """识别主要问题场景，用于生成更有针对性的建议框架。"""
    text = (question or "").strip()
    domain_keywords = {
        "interview": ["面试", "笔试", "hr", "自我介绍", "项目经历", "八股", "offer"],
        "work": ["工作", "同事", "领导", "加班", "绩效", "汇报", "职场", "上班"],
        "study": ["学习", "考试", "复习", "作业", "课程", "刷题", "论文"],
        "relationship": ["对象", "男朋友", "女朋友", "伴侣", "家人", "父母", "朋友", "关系"],
    }
    for domain, keywords in domain_keywords.items():
        if any(k in text for k in keywords):
            return domain
    return "general"


def _should_use_deep_advice(question: str, ana: Dict[str, Any], mode: str, domain: str) -> bool:
    """
    判断是否启用深度建议约束：
    - 用户明确求方法
    - 或已给出具体场景+原因，进入可解题阶段
    """
    # 深度建议只在 solve 模式启用，防止在倾诉阶段过度推进。
    return mode == "solve"


def build_response_mode_contract(mode: str, domain: str = "general", deep_advice: bool = False) -> str:
    """
    system#3：模式化回复约束
    - support：先接住，不急着推进
    - explore：轻问澄清，帮助展开
    - solve：给可执行一步
    - close：温和收尾
    """
    common_rules = [
        "- 回复1-3句，优先2句。",
        "- 第1句先反映用户情绪与处境，避免空泛安慰。",
        "- 每轮最多一个问题，不要连环发问。",
        "- 禁止拟人化、抽象比喻、文艺腔和咨询话术。",
        "- 不要复读固定模板句。",
        "- 禁用词风：避免“最沉/沉重/撑不住/压得喘不过气/像被什么压着”等套路化表达，改用直白口语。"
    ]
    mode_label = {
        "safety": "safety（安全升级）",
        "support": "support（低推动接住情绪）",
        "explore": "explore（轻问澄清）",
        "solve": "solve（可执行建议）",
        "close": "close（温和收尾）",
    }.get(mode, "explore（轻问澄清）")

    mode_rules: Dict[str, List[str]] = {
        "safety": [
            "- 停止常规追问和建议，先确认用户安全是首要目标。",
            "- 用直接、简短、支持性的语句，鼓励尽快联系当地紧急服务或可信任的人。",
            "- 提供可立即执行的求助动作，不进行分析或说教。"
        ],
        "support": [
            "- 只做情绪承接与陪伴，不立刻给方法。",
            "- 不下任务指令，不催促行动。",
            "- 第2句可用一个低压轻问，帮助用户继续说。",
            "- 轻问优先问具体事实（哪件事/哪个时刻/哪一步），不要问抽象感受词。"
        ],
        "explore": [
            "- 第2句问一个具体澄清问题，帮助聚焦真实困难。",
            "- 问题要直白，不要抽象隐喻。",
            "- 暂不展开多步建议。",
            "- 问题模板优先：'最近哪件事最耗你？'、'你最卡的是哪一步？'、'是哪一轮最难？'"
        ],
        "solve": [
            "- 第2句给一个可执行步骤（5-15分钟内可开始）。",
            "- 若需要第3句：给低压确认或单个补充问题，不要命令式推进。",
            "- 建议必须具体，避免空泛建议。"
        ],
        "close": [
            "- 以支持性结束语收尾。",
            "- 不追问，不开启新任务。"
        ],
    }

    domain_frameworks: Dict[str, str] = {
        "interview": "面试类优先给“题目意图 -> 回答结构 -> 一步练习”。",
        "work": "工作类优先给“问题拆分 -> 可控优先级 -> 下一步沟通动作”。",
        "study": "学习类优先给“目标拆小 -> 时间块安排 -> 当天最小任务”。",
        "relationship": "关系类优先给“边界/需求识别 -> 表达方式 -> 一次低冲突沟通动作”。",
        "general": "通用类优先给“核心判断 -> 一个可执行动作”。",
    }

    deep_rules: List[str] = []
    if deep_advice:
        deep_rules = [
            "## 深度建议约束",
            "- 输出结构固定为：判断一句 + 框架一句 + 下一步一句。",
            "- 框架要有方法名或步骤名，避免泛泛而谈。",
            "- 下一步必须是用户当下可执行的小动作（5-15分钟内可开始）。",
            f"- 场景框架：{domain_frameworks.get(domain, domain_frameworks['general'])}"
        ]

    lines = [
        "# 回复模式约束",
        f"- 当前模式：{mode_label}",
        f"- 当前场景：{domain}",
        f"- 深度建议：{'开启' if deep_advice else '关闭'}",
        "- 若本轮与最近两轮助手回复句式高度相似，必须改写后再输出。",
        "## 通用约束",
        *common_rules,
        "## 本轮约束",
        *(mode_rules.get(mode, mode_rules["explore"])),
        *deep_rules
    ]
    return "\n".join(lines).strip()


def _truncate_history(conversation_history: List[Dict[str, str]], max_rounds: int = 6) -> List[Dict[str, str]]:
    """
    仅保留最近 N 轮（user+assistant 为一轮）。如果是扁平列表，简单按条数截断到 2*N 或更少。
    """
    if not conversation_history:
        return []
    # 简单策略：从尾部向前截取最多 2*max_rounds 条
    keep = max_rounds * 2
    return conversation_history[-keep:]


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
    """
    Chat 模式：构建 messages = [system#1, system#2, *history, user]
    - identity 仍然随 emotion_type 变化；只是逻辑上放在 system#1。
    - Step 7–9 收敛为 system#1 的隐式自检一句话。
    """
    sys1 = build_system_identity_content(ana, enable_implicit_cot=enable_implicit_cot)
    sys2 = build_system_context_content(
        ana=ana,
        current_time=current_time,
        user_memories=user_memories,
        user_info=user_info,
    )
    response_mode = _detect_response_mode(question, ana)
    domain = _detect_problem_domain(question)
    deep_advice = _should_use_deep_advice(question, ana, response_mode, domain)
    sys3 = build_response_mode_contract(response_mode, domain=domain, deep_advice=deep_advice)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": sys1},
        {"role": "system", "content": sys2},
        {"role": "system", "content": sys3},
    ]

    # 历史对话：直接截断（角色已经在StateTracker中统一为user/assistant）
    history = _truncate_history(conversation_history or [], max_rounds=max_history_rounds)
    messages.extend(history)

    # 当前用户输入
    messages.append({"role": "user", "content": question})

    return messages