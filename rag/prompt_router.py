# File: rag/prompt_router.py
# 功能：根据用户情绪自动路由到不同风格的Prompt模板
# 实现：基于情绪类型选择最适合的对话风格

from llm.emotion_detector import detect_emotion  # 导入情绪检测函数

def route_prompt_by_emotion(emotion: str) -> str:
    """
    根据情绪返回对应的风格 prompt key
    
    参数：
        emotion (str): 检测到的情绪类型
        参数来源：llm.emotion_detector.detect_emotion() 函数返回的情绪标签
        可能的值：happy, sad, angry, tired, neutral
    
    返回：
        str: 对应的Prompt风格key
        返回值说明：
        - "light_expand": 开心/正向场景，轻松扩展风格
        - "cheer_and_push": 疲惫/无力场景，鼓励推动风格  
        - "co_regret": 悲伤/愤怒场景，共情安慰风格
        - "default": 兜底风格，用于未识别情绪或日常泛用场景
    
    路由逻辑：
        - happy/neutral → light_expand (轻松扩展)
        - tired → cheer_and_push (鼓励推动)
        - sad/angry → co_regret (共情安慰)
        - 其他情况 → default (兜底)
    """
    if emotion in ["happy", "neutral"]:
        return "light_expand"  # 开心和中性情绪使用轻松扩展风格
    elif emotion == "tired":
        return "cheer_and_push"  # 疲惫情绪使用鼓励推动风格
    elif emotion in ["sad", "angry"]:
        return "co_regret"  # 悲伤和愤怒情绪使用共情安慰风格
    else:
        return "default"  # 其他情况使用兜底风格
