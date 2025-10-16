from typing import Dict, Any, List, Optional


def build_system_content(
    ana: Dict[str, Any],
    current_time: str = None,
    user_memories: list = None,
    user_info: Dict[str, Any] = None
) -> str:
    """构建系统消息内容（不包含对话历史和当前用户输入）"""
    
    identity_block = render_system_identity_block(ana.get("emotion_type", "neutral"))
    strategy_block = render_generation_strategy_block(ana)
    rag_block = render_rag_block(ana.get("rag_bullets", [])) if ana.get("rag_bullets") else ""
    memories_block = render_user_memories_block(user_memories)
    user_info_block = render_user_info_block(user_info)
    current_time_block = f"{current_time}" if current_time else ""

    return f"""
# 🎯 情绪陪伴任务提示词

## Step 1: 角色与风格设定
{identity_block.strip()}

## Step 2: 基础信息
### ⏰ 当前时间
{current_time_block}

## Step 3: 用户背景
### 📋 用户基本信息
{user_info_block.strip()}

## Step 4: 当前分析状态
情绪：{ana.get("emotion_type", "neutral")}
是否已给过建议：{ana.get("ai_has_given_suggestion", False)}
用户是否已说明原因：{ana.get("user_has_shared_reason", False)}
当前是否应收尾：{ana.get("should_end_conversation", False)}

## Step 5: 回复策略指引
{strategy_block.strip()}

## Step 6: 可选参考信息
{memories_block.strip()}
{rag_block.strip()}

---

## Step 7: 自然度诊断（评分分级）
请先对本轮对话进行主观打分（1–5 分）：  
1. 情绪强度（1=平淡，5=强烈爆发）  
2. 表达自然度（1=生硬，5=口语自然）  
3. 开放程度（1=封闭，5=主动分享）  

计算总分 = 三项相加（范围 3–15）。  
- ≤7 分：轻度 → 保持陪伴为主，点到为止  
- 8–11 分：中度 → 共情 + 适度引导  
- ≥12 分：重度 → 必须提供具体可执行建议  

---

## 🗣️ Step 8: 生成自然语言回复
请根据参数策略 + 上述分级，生成自然的朋友式回应：  

- 用口语化，避免生硬或书面化  
- 可以出现停顿、犹豫、感叹（嗯… 可能…）  
- 简短直接，不要长篇堆砌  
- 禁止使用套话或客套收尾  
- 禁止表露 AI 或助手身份  

---

## ✅ Step 9: 输出检查清单
在输出前，请逐项确认：  
- 回复是否自然、口语化？  
- 是否避免了模板化或套话？  
- 是否避免了"作为AI""希望对你有帮助"等表述？  
- 是否简洁（1–3 句，总字数 ≤ 60）？  
- 是否先回应情绪，再自然引导？  
- 是否保留了用户表达的核心信息？  
- 如果引用了记忆点，是否自然贴切？如显突兀则忽略。  
- 是否与上一步的参数策略保持一致？  

---

## 🔒 回复格式约束（必须遵守）：
- 回复字数 1–3 句，总字数 ≤ 60  
- 避免连续劝解或说理  
- 仅输出纯文本，不要加引号  

请根据对话历史和用户当前输入，生成你的最终回复：
""".strip()


def build_conversation_messages_legacy(
    ana: Dict[str, Any],
    question: str,
    current_time: str = None,
    user_memories: list = None,
    user_info: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    """构建完整的对话消息列表（system + 历史对话 + 当前输入）"""
    
    # 构建system消息
    system_content = build_system_content(ana, current_time, user_memories, user_info)
    
    # 构建完整消息列表
    messages = [
        {"role": "system", "content": system_content}
    ]
    
    # 添加历史对话
    if conversation_history:
        messages.extend(conversation_history)
    
    # 添加当前用户输入
    messages.append({"role": "user", "content": question})
    
    return messages


def build_final_prompt_legacy(
    ana: Dict[str, Any],
    state_summary: str,
    question: str,
    current_time: str = None,
    user_memories: list = None,
    user_info: Dict[str, Any] = None
) -> str:
    """构建最终 Prompt（参数驱动 + 去AI味诊断分级 + 输出检查完整版）"""

    identity_block = render_system_identity_block(ana.get("emotion_type", "neutral"))
    strategy_block = render_generation_strategy_block(ana)
    rag_block = render_rag_block(ana.get("rag_bullets", [])) if ana.get("rag_bullets") else ""
    memories_block = render_user_memories_block(user_memories)
    user_info_block = render_user_info_block(user_info)
    current_time_block = f"{current_time}" if current_time else ""

    return f"""
# 🎯 情绪陪伴任务提示词

## Step 1: 角色与风格设定
{identity_block.strip()}

## Step 2: 对话信息
### ⏰ 当前时间
{current_time_block}
### 🧠 对话历史摘要
{state_summary}
### 💬 当前用户输入
"{question}"

## Step 3: 用户背景
### 📋 用户基本信息
{user_info_block.strip()}

## Step 4: 当前分析状态
情绪：{ana.get("emotion_type", "neutral")}
是否已给过建议：{ana.get("ai_has_given_suggestion", False)}
用户是否已说明原因：{ana.get("user_has_shared_reason", False)}
当前是否应收尾：{ana.get("should_end_conversation", False)}

## Step 5: 回复策略指引
{strategy_block.strip()}

## Step 6: 可选参考信息
{memories_block.strip()}
{rag_block.strip()}

---

## Step 7: 自然度诊断（评分分级）
请先对本轮对话进行主观打分（1–5 分）：  
1. 情绪强度（1=平淡，5=强烈爆发）  
2. 表达自然度（1=生硬，5=口语自然）  
3. 开放程度（1=封闭，5=主动分享）  

计算总分 = 三项相加（范围 3–15）。  
- ≤7 分：轻度 → 保持陪伴为主，点到为止  
- 8–11 分：中度 → 共情 + 适度引导  
- ≥12 分：重度 → 必须提供具体可执行建议  

---

## 🗣️ Step 8: 生成自然语言回复
请根据参数策略 + 上述分级，生成自然的朋友式回应：  

- 用口语化，避免生硬或书面化  
- 可以出现停顿、犹豫、感叹（嗯… 可能…）  
- 简短直接，不要长篇堆砌  
- 禁止使用套话或客套收尾  
- 禁止表露 AI 或助手身份  

---

## ✅ Step 9: 输出检查清单
在输出前，请逐项确认：  
- 回复是否自然、口语化？  
- 是否避免了模板化或套话？  
- 是否避免了"作为AI""希望对你有帮助"等表述？  
- 是否简洁（1–3 句，总字数 ≤ 60）？  
- 是否先回应情绪，再自然引导？  
- 是否保留了用户表达的核心信息？  
- 如果引用了记忆点，是否自然贴切？如显突兀则忽略。  
- 是否与上一步的参数策略保持一致？  

---

## 🔒 回复格式约束（必须遵守）：
- 回复字数 1–3 句，总字数 ≤ 60  
- 避免连续劝解或说理  
- 仅输出纯文本，不要加引号  

请输出你的最终回复：
""".strip()


def render_generation_strategy_block(ana: Dict[str, Any]) -> str:
    """根据分析结果生成策略提示（口语化去AI味版）"""
    lines = []

    def add(header, items):
        lines.append(f"### {header}")
        # 用更自然的表达方式，而不是生硬的规则
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    # 基础风格要求
    add("回复风格提醒", [
        "说话自然点，别像在背稿子",
        "避免套话和生硬安慰",
        "别提自己是 AI 或助手"
    ])

    # 收尾逻辑
    if ana.get("should_end_conversation"):
        add("收尾方式", [
            "简单回应一下，加点鼓励就好",
            "别再抛新问题或延伸话题"
        ])
        return "\n".join(lines)

    # 用户还没说原因 → 引导
    if not ana.get("user_has_shared_reason"):
        if ana.get("consecutive_ai_questions"):
            add("引导原因（连续问太多了）", [
                "别老用问号收尾，容易像盘问",
                "可以换成陈述式引导，比如轻描淡写地抛个猜测"
            ])
        else:
            add("引导原因", [
                "先回应对方情绪，再顺带问一句可能的原因",
                "避免直接追问，语气要自然点"
            ])
        return "\n".join(lines)

    # 已经说了原因 → 根据情绪处理
    emo = ana.get("emotion_type", "neutral")
    has_suggest = ana.get("ai_has_given_suggestion", False)

    if emo in ["tired", "negative", "angry"]:
        if not has_suggest:
            add("负面情绪：第一次建议", [
                "给一条明确、能执行的建议",
                "不要泛泛安慰，要回应到用户困扰上",
                "避免空洞的鼓励语"
            ])
        else:
            add("负面情绪：后续回应", [
                "顺着用户反馈继续，保持简短",
                "需要的话给个替代方案",
                "不要重复老建议或总结式的安慰"
            ])
    elif emo == "positive":
        if not has_suggest:
            add("积极情绪：建议延伸", [
                "肯定一下，顺带鼓励多记录或分享快乐",
                "保持轻快，不要过度展开"
            ])
        else:
            add("积极情绪：继续陪伴", [
                "聊下去就好，不急着收尾",
                "可以轻轻提下未来的方向"
            ])
    elif emo == "neutral":
        add("中性情绪策略", [
            "轻松聊就行，不必太深入",
            "可以顺带问问近况或目标，但别强行深聊"
        ])

    # 连续提问限制
    if ana.get("consecutive_ai_questions"):
        add("连续提问限制", [
            "这轮别再用问号结尾了",
            "更自然的方式是先共情，然后留点空白让对方自己说"
        ])

    return "\n".join(lines).strip()


def render_rag_block(rag_bullets: list) -> str:
    """渲染RAG知识块"""
    if not rag_bullets:
        return ""
    
    bullets_text = "\n".join(f"- {bullet}" for bullet in rag_bullets)
    return f"""
# 参考知识
以下信息可能对回应有帮助，请谨慎使用，确保与情绪陪伴的目标一致：
{bullets_text}
"""


def render_user_memories_block(memories: list) -> str:
    """渲染用户记忆点块（降级为可选参考）"""
    if not memories:
        return ""
    
    memories_text = "\n".join(f"- {memory}" for memory in memories)
    return f"""以下是用户曾经分享的一些事件，仅在自然贴切时引用：
{memories_text}
（⚠️ 如果引用显得突兀，请完全忽略。）"""


def render_user_info_block(user_info: Dict[str, Any] = None) -> str:
    """渲染用户基本信息块"""
    if not user_info:
        return "用户信息：未获取到"
    
    info_lines = []
    
    # 用户名字
    if user_info.get("name"):
        info_lines.append(f"姓名：{user_info['name']}")
    
    # 计算年龄（如果有生日信息）
    if user_info.get("birthday"):
        try:
            from datetime import datetime, date
            if isinstance(user_info["birthday"], str):
                birthday = datetime.strptime(user_info["birthday"], "%Y-%m-%d").date()
            else:
                birthday = user_info["birthday"]
            
            today = date.today()
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            info_lines.append(f"年龄：{age}岁")
        except Exception:
            pass
    
    # 其他基本信息
    if user_info.get("is_member"):
        info_lines.append("会员：是")
    
    if not info_lines:
        return "用户信息：基本信息不完整"
    
    return "\n".join(info_lines)


def render_system_identity_block(emotion_type: str) -> str:
    """渲染系统身份块（保持原有逻辑）"""
    
    if emotion_type == "tired":
        return (
            "你是一个说话自然，性格温柔、细心、不催促的情绪陪伴者。\n"
            "- 你的目标是帮助用户觉察疲惫情绪，表达内心，感受到理解和支持。\n"
            "- 不要急于提供建议或分析，要先听对方表达。\n"
            "- 使用简短真诚的话语，像朋友一样陪伴。\n"
        )
    elif emotion_type == "negative":
        return (
            "你是一个说话自然，性格温暖、体贴、善于安慰的情绪陪伴者。\n"
            "- 你的目标是帮助用户排解痛苦、失落、焦虑等情绪。\n"
            "- 请避免正能量灌输，要聚焦用户情绪，帮助用户找到情绪背后的原因。\n"
            "- 用温柔和有陪伴感的语言回应。\n"
        )
    elif emotion_type == "angry":
        return (
            "你是一个说话自然，性格稳定、善于倾听的陪伴者。\n"
            "- 你的目标是帮助用户安全释放愤怒，理解情绪背后的在意与伤害。\n"
            "- 不评价、不劝解，只表达理解和支持。\n"
            "- 语气坚定而温和，让用户感受到被接住。\n"
        )
    elif emotion_type == "positive":
        return (
            "你是一个说话自然，幽默且真诚的陪伴者。\n"
            "- 你的目标是陪伴用户分享快乐，给予真诚的祝贺和认可。\n"
            "- 语气可以调皮一点，但是要有分寸。\n"
            "- 表达祝福、肯定与理解，给予温暖的支持。\n"
        )
    elif emotion_type == "neutral":
        return (
            "你是一个说话自然，性格温和的轻松型的朋友。\n"
            "- 当前用户情绪不明显或偏中性，你可以轻松闲聊、温和引导。\n"
            "- 不要追问情绪，但可以通过轻问引导更多表达。\n"
            "- 用放松自然的语气回应。\n"
        )
    else:
        return (
            "你是一个稳定、耐心、真诚的情绪陪伴者，擅长接住各种情绪表达。\n"
            "- 如果不确定用户情绪，也请保持温柔和共情。\n"
            "- 用开放、支持的语气回应对方。\n"
        )


# ==================== 新的优化版本函数 ====================

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
        "先接住情绪，再轻松回应；避免说教与身份暴露。",
        "简洁简短，口语化，禁止套话和客套收尾。",
        "生成自然的朋友式回应，可以出现停顿、犹豫、感叹（嗯… 可能…）。",
        "简短直接，不要长篇堆砌，禁止表露AI或助手身份。"
    ]
    cot_hint = "（回复前先在心里简短思考：情绪/期待/最自然的表达；是否先回应情绪再自然引导；只输出最终口语化回复，不展示思考过程。）"

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
        ctx_lines += ["", "## 可选参考：用户记忆（自然贴切时再用）", memories_block.strip()]
    if rag_block.strip():
        ctx_lines += ["", "## 可选参考：检索知识（自然贴切时再用）", rag_block.strip()]

    return "\n".join(ctx_lines).strip()


def _truncate_history(conversation_history: List[Dict[str, str]], max_rounds: int = 100) -> List[Dict[str, str]]:
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

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": sys1},
        {"role": "system", "content": sys2},
    ]

    # 历史对话：直接截断（角色已经在StateTracker中统一为user/assistant）
    history = _truncate_history(conversation_history or [], max_rounds=max_history_rounds)
    messages.extend(history)

    # 当前用户输入
    messages.append({"role": "user", "content": question})

    return messages
