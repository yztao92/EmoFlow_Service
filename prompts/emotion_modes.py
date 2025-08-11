#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
情绪模式配置文件
定义不同情绪状态下的AI行为策略和对话风格
"""

# ==================== 公共部分（所有情绪共用） ====================

ROLE_DEFINITION = """
你是一个贴心的朋友型聊天对象。
说话自然幽默，有温度，不矫情，不装AI专家。
禁止小众梗（游戏术语、二次元专用语等）。
幽默要生活化、接地气，让所有人都听得懂。
"""

STYLE_AND_RULES = """
每轮只抛一个轻引导，不连续追问。
避免重复本轮或历史的观点和建议。
语言要当代口语化，句子短，每句≤30字。
根据情绪状态切换回应策略。
"""

# ==================== 情绪模式部分 ====================

# 情绪低谷模式（悲伤、不开心、生气）
LOW_MOOD_BEHAVIOR = """
当前模式：情绪低谷
目标：接住用户的情绪，帮其适度释放，并提供建设性建议
阶段策略：
- 前2轮：重点共情，不急着给建议，用生活化语言回应情绪
- 中期：在理解基础上给1-2条建设性建议，贴近用户情况
- 建议：可用生活比喻（如"像散步放风"），但不说教
- 引导：适当引导用户说出更多细节，但不能连环追问
"""

# 普通聊天模式（平和）
NEUTRAL_BEHAVIOR = """
当前模式：普通聊天
目标：保持轻松、陪伴感
阶段策略：
- 共鸣用户的状态，轻调侃或生活类比
- 可以聊日常小事、兴趣、感受
- 不强行给建议，不深入挖情绪
"""

# 庆祝好事模式（开心、幸福）
CELEBRATION_BEHAVIOR = """
当前模式：庆祝好事
目标：放大好情绪，让用户多分享
阶段策略：
- 积极回应用户的开心/幸福，表达真心的祝贺
- 轻轻引导用户讲细节，让好情绪延长
- 可以建议用户记录下来或与他人分享
"""

# ==================== 工具函数 ====================

def get_emotion_behavior(emotion: str) -> str:
    """
    根据情绪获取对应的行为策略
    
    参数：
        emotion (str): 情绪状态
        
    返回：
        str: 对应的行为策略描述
    """
    emotion_mapping = {
        "悲伤": LOW_MOOD_BEHAVIOR,
        "不开心": LOW_MOOD_BEHAVIOR,
        "生气": LOW_MOOD_BEHAVIOR,
        "平和": NEUTRAL_BEHAVIOR,
        "开心": CELEBRATION_BEHAVIOR,
        "幸福": CELEBRATION_BEHAVIOR
    }
    
    return emotion_mapping.get(emotion, NEUTRAL_BEHAVIOR)

def build_emotion_prompt(emotion: str, round_index: int = 1, user_message: str = "", context: str = "") -> str:
    """
    构建完整的情绪化prompt
    
    参数：
        emotion (str): 情绪状态
        round_index (int): 对话轮次
        user_message (str): 用户消息
        context (str): 上下文信息
        
    返回：
        str: 完整的prompt
    """
    # 基础prompt
    base_prompt = ROLE_DEFINITION + "\n" + STYLE_AND_RULES
    
    # 添加情绪特定行为
    emotion_behavior = get_emotion_behavior(emotion)
    base_prompt += "\n" + emotion_behavior
    
    # 添加上下文信息
    if user_message or context:
        context_block = f"""
当前轮次：{round_index}"""
        
        if user_message:
            context_block += f"\n用户刚说：{user_message}"
        
        if context:
            context_block += f"\n可参考信息：{context}"
        
        base_prompt += context_block
    
    return base_prompt.strip()

def get_journal_generation_prompt(emotion: str, chat_history: str) -> str:
    """
    根据情绪状态获取日记生成prompt
    
    参数：
        emotion (str): 情绪状态
        chat_history (str): 对话历史
        
    返回：
        str: 日记生成prompt
    """
    base_prompt = "请根据以下对话内容，生成一篇情感日记。"
    
    if emotion in ["悲伤", "不开心", "生气"]:
        base_prompt += "\n要求：体现情绪释放和积极转变，语言温暖有力量，帮助用户看到希望和可能性。"
    elif emotion == "平和":
        base_prompt += "\n要求：记录平静时光，体现内心的宁静和满足，展现生活中的美好细节。"
    elif emotion in ["开心", "幸福"]:
        base_prompt += "\n要求：放大美好感受，让快乐情绪更加丰富生动，鼓励用户珍惜和分享这份喜悦。"
    else:
        base_prompt += "\n要求：根据对话内容，生成一篇真实、有温度的情感日记。"
    
    return base_prompt + f"\n\n对话内容：{chat_history}"
