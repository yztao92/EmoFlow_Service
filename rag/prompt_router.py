# File: rag/prompt_router.py
# 功能：根据用户情绪自动路由到不同风格的Prompt模板
# 实现：基于情绪类型选择最适合的对话风格

def route_prompt_by_emotion(emotion: str) -> str:
    """
    根据情绪返回对应的风格 prompt key
    
    参数：
        emotion (str): 前端传入的情绪类型
        参数来源：前端传入的情绪值
        可能的值：happy, angry, sad, unhappy, peaceful, happiness
    
    返回：
        str: 对应的Prompt风格key
        返回值说明：
        - "light_expand": 开心/正向场景，轻松扩展风格
        - "cheer_and_push": 疲惫/无力场景，鼓励推动风格  
        - "co_regret": 悲伤/愤怒场景，共情安慰风格
        - "default": 兜底风格，用于未识别情绪或日常泛用场景
    
    路由逻辑：
        - happy/happiness/peaceful → light_expand (轻松扩展)
        - angry/sad/unhappy → co_regret (共情安慰)
        - 其他情况 → default (兜底)
    """
    # 正向情绪：使用轻松扩展风格
    if emotion in ["happy", "happiness", "peaceful"]:
        return "light_expand"
    # 负面情绪：使用共情安慰风格
    elif emotion in ["angry", "sad", "unhappy"]:
        return "co_regret"
    # 其他情况：使用兜底风格
    else:
        return "default"
