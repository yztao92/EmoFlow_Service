import re

# 示例 LLM 情绪判断接口函数（需你接入真实模型/服务）
def llm_emotion_api(msg: str) -> str:
    """
    调用大模型 API 判断情绪，仅返回 happy/sad/angry/tired/neutral 之一。
    这里是示意函数，你需接入实际 LLM 识别接口。
    """
    # 示例返回
    return "neutral"


def detect_emotion(msg: str) -> str:
    """
    根据规则或 LLM 检测用户输入情绪。
    优先使用关键词规则，规则无法命中则使用 LLM fallback。
    """
    msg = msg.strip().lower()

    happy_keywords = r"开心|高兴|爽|放假|赚到了|升职|中奖|顺利|早下班|轻松|如愿|愉快|得劲|躺赢|美滋滋|幸福|解放|自由|美好|满意|哈哈+|笑死|放松|心情好|喜悦|甜|舒服|满意|顺心|值得|有趣|喜欢|真香"
    sad_keywords = r"难过|失落|伤心|心碎|沮丧|低落|绝望|想哭|崩溃|无助|被动|失望|郁闷|遗憾|痛苦|麻了|烦闷|愁|心情差|迷茫|不开心|凄凉|烦恼|孤独|抑郁|无力|想放弃|伤感|没希望|眼泪|苦"
    angry_keywords = r"气死|生气|愤怒|火大|暴躁|崩溃|烦人|受够了|不爽|怒|忍不了|真无语|骂人|爆炸|烦死|疯了|什么玩意|操|服了|受气|欺负|挑衅|讨厌|狗东西|不讲理|怒火|发火|恼火|翻脸|吐槽|脾气|怒气|不耐烦"
    tired_keywords = r"累|疲惫|搞不动|没力气|困|压力大|倦|撑不住|不想动|太难了|躺平|没精神|撑不下去|快倒了|乏|身心俱疲|筋疲力尽|虚脱|提不起劲|没状态|想睡|耗尽|无力|打不起精神|死气沉沉|拖延|没活力|不行了|懒得|倦怠|麻木|烦闷"
    
    if re.search(happy_keywords, msg):
        return "happy"
    elif re.search(sad_keywords, msg):
        return "sad"
    elif re.search(angry_keywords, msg):
        return "angry"
    elif re.search(tired_keywords, msg):
        return "tired"

    # fallback to LLM
    return llm_emotion_api(msg)


# Prompt 路由器，根据情绪分配对应的 prompt 类型
def route_prompt_by_emotion(emotion: str) -> str:
    """
    根据情绪返回对应的风格 prompt key
    """
    if emotion in ["happy", "neutral"]:
        return "light_expand"
    elif emotion in ["tired"]:
        return "cheer_and_push"
    elif emotion in ["sad", "angry"]:
        return "co_regret"
    else:
        return "default"