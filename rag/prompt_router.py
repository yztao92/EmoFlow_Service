from llm.emotion_detector import detect_emotion

def route_prompt_by_emotion(emotion: str) -> str:
    """
    根据情绪返回对应的风格 prompt key
    """
    if emotion in ["happy", "neutral"]:
        return "light_expand"
    elif emotion == "tired":
        return "cheer_and_push"
    elif emotion in ["sad", "angry"]:
        return "co_regret"
    else:
        return "default"
