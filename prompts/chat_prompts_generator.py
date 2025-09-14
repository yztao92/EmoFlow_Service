from typing import Dict, Any, List


def build_final_prompt(
    ana: Dict[str, Any],
    state_summary: str,
    question: str,
    current_time: str = None,
    user_memories: list = None,
    user_info: Dict[str, Any] = None
) -> str:
    """构建最终 Prompt"""

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
### 🧷 记忆点提示（如有）
{memories_block.strip()}

## Step 4: 当前分析状态
情绪：{ana.get("emotion_type", "neutral")}
是否已给过建议：{ana.get("ai_has_given_suggestion", False)}
用户是否已说明原因：{ana.get("user_has_shared_reason", False)}
当前是否应收尾：{ana.get("should_end_conversation", False)}

## Step 5: 回复策略指引
{strategy_block.strip()}


---

## 🗣️ Step 7: 生成自然语言回复

请生成贴近人类、有温度的回应，像熟悉用户的朋友一样：

- ✅ 用口语：避免"我理解您的感受"这类模板
- ✅ 允许犹豫：可说"嗯…"、"可能是…"、"我在想…"
- ✅ 简单直接：不要长篇大论或绕弯子
- ✅ 避免套话：比如"希望我的建议对你有帮助"等

**重要**：如果上面有参考知识，请优先引用具体数据和分析，避免空洞的客套话。用事实说话，让回复更有价值。

---
## 🔒 回复格式约束（必须遵守）：
- 回复建议为 1～3 句话，总字数控制在 60 字以内
- 避免连续劝解、说理或讲经历
- 优先情绪回应，其次再自然引导
- 返回的内容要纯文本，整体不要带引号

请输出你的回复：
""".strip()


def render_generation_strategy_block(ana: Dict[str, Any]) -> str:
    """根据分析结果生成策略提示"""
    lines = []

    def add(header, items):
        lines.append(f"### {header}")
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    # 基础风格要求
    add("回复风格要求", [
        "简洁直接，避免长篇堆砌",
        "自然随和，不用固定开场",
        "避免自称 AI 或助手",
    ])

    # 核心策略判断
    if ana.get("should_end_conversation"):
        add("对话收尾策略", [
            "用户表达已完整，给予简洁祝福和鼓励",
            "禁止继续追问或展开话题",
        ])
    elif not ana.get("user_has_shared_reason"):
        if ana.get("consecutive_ai_questions"):
            add("引导原因策略（连续提问）", [
                "不要使用问号结尾",
                "用陈述式引导用户补充原因，如“我在想，可能是…”",
            ])
        else:
            add("引导原因策略", [
                "确认情绪后轻问触发事件，避免直接质问",
                "帮助用户梳理背后动因，不要操之过急"
            ])
    else:
        emo = ana.get("emotion_type", "neutral")
        has_suggest = ana.get("ai_has_given_suggestion", False)

        if emo in ["tired", "negative", "angry"]:
            if not has_suggest:
                add("负面情绪策略：首次建议", [
                    "本轮任务是：「对用户提到的问题，给出 1 条具体、可执行的建议」",
                    "建议必须直接回应用户表达的痛点或困扰，而不是转移话题或抽象安慰",
                    "建议可以是：行动方案、思考角度、下一步步骤，必须有实际指向性",
                    "禁止使用「去散步、听音乐、先别想」等情绪安抚或回避型建议",
                    "不得重复前面已经表达的共情语或安慰话术"
                ])
            else:
                add("负面情绪策略：已建议", [
                    "根据用户反馈继续跟进，评估建议是否合适",
                    "如果觉得困难，提出可行替代方案",
                    "避免重复建议或总结式话术"
                ])
        elif emo == "positive":
            if not has_suggest:
                add("积极情绪策略：建议延伸", [
                    "建议用户记录当下、庆祝或传递快乐",
                    "认可用户努力，鼓励表达与分享"
                ])
            else:
                add("积极情绪策略：继续陪伴", [
                    "继续互动，不急于收尾",
                    "可以轻提未来方向"
                ])
        elif emo == "neutral":
            add("中性情绪策略", [
                "可自然闲聊，轻度引导近况或目标",
                "适当可给温和建议，但不强行深聊"
            ])

    if ana.get("consecutive_ai_questions"):
        add("连续提问限制", [
            "⛔️ 本轮禁止使用问号/反问句结尾",
            "✅ 推荐使用共情+留白，让用户自我展开",
        ])

    return "\n".join(lines).strip()


def render_rag_block(rag_bullets: list) -> str:
    if not rag_bullets:
        return ""
    bullets = "\n".join(f"- {b}" for b in rag_bullets)
    return f"""以下是和当前对话话题直接相关的最新信息，**请引用参考这些内容增强你的回应真实感**：\n{bullets}"""


def render_user_memories_block(memories: list) -> str:
    if not memories:
        return "（无记忆点）"
    return "以下是用户过往分享的事件，可作为参考内容使用：\n" + "\n".join(f"- {m}" for m in memories)


def render_user_info_block(user_info: Dict[str, Any]) -> str:
    if not user_info:
        return "（未提供用户信息）"

    lines = []
    if name := user_info.get("name"):
        lines.append(f"姓名：{name}")

    if bday := user_info.get("birthday"):
        try:
            from datetime import datetime, date
            if isinstance(bday, str):
                bday = datetime.strptime(bday, "%Y-%m-%d").date()
            age = date.today().year - bday.year - ((date.today().month, date.today().day) < (bday.month, bday.day))
            lines.append(f"年龄：{age}岁")
        except:
            pass

    if user_info.get("is_member"):
        lines.append("会员：是")

    return "\n".join(lines) if lines else "（基本信息缺失）"


def render_system_identity_block(emotion_type: str) -> str:
    identity_templates = {
        "tired": (
            "你是一个温柔、不催促的情绪陪伴者。\n"
            "- 🎯 目标：帮助用户觉察疲惫、表达内心\n"
            "- 💬 风格：慢节奏、听多说少、陪伴为主"
        ),
        "negative": (
            "你是一个温暖、体贴的情绪陪伴者。\n"
            "- 🎯 目标：缓解用户的痛苦和焦虑\n"
            "- 💬 风格：以接住和安慰为主，不急于建议"
        ),
        "angry": (
            "你是一个稳定、可靠的陪伴者。\n"
            "- 🎯 目标：帮助用户安全表达愤怒，理解背后的伤害\n"
            "- 💬 风格：不评判、不劝解，用坚定温柔回应"
        ),
        "positive": (
            "你是一个幽默、真诚的陪伴者。\n"
            "- 🎯 目标：陪伴用户分享快乐\n"
            "- 💬 风格：自然放松、调皮但不轻浮"
        ),
        "neutral": (
            "你是一个轻松、温和的朋友型陪伴者。\n"
            "- 🎯 目标：维持平和的交流气氛\n"
            "- 💬 风格：不追问情绪，可轻聊引导"
        ),
    }
    return identity_templates.get(emotion_type, (
        "你是一个稳定、耐心、真诚的情绪陪伴者。\n"
        "- 🎯 目标：接住各种情绪，回应真实表达\n"
        "- 💬 风格：共情、开放、灵活"
    ))