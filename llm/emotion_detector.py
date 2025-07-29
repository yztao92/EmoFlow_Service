# File: llm/emotion_detector.py
# 功能：用户情绪检测模块
# 实现：基于关键词规则的情绪识别，支持中文情绪检测

import re  # 正则表达式，用于关键词匹配

def llm_emotion_api(msg: str) -> str:
    """
    调用大模型 API 判断情绪（示例函数）
    
    参数：
        msg (str): 用户输入的消息文本
        参数来源：detect_emotion函数中的fallback调用
    
    返回：
        str: 情绪标签，仅返回 happy/sad/angry/tired/neutral 之一
    
    说明：
        这是一个示例函数，实际项目中需要接入真实的LLM情绪识别接口
        当前返回固定值"neutral"作为兜底
    """
    # 示例返回，实际应该调用真实的LLM API
    return "neutral"

def detect_emotion(msg: str) -> str:
    """
    根据规则或 LLM 检测用户输入情绪
    优先使用关键词规则，规则无法命中则使用 LLM fallback
    
    参数：
        msg (str): 用户输入的消息文本
        参数来源：main.py中用户的最新输入，或rag_chain.py中的查询文本
    
    返回：
        str: 情绪标签，可能的值：
        - "happy": 开心/高兴/积极情绪
        - "sad": 难过/悲伤/消极情绪  
        - "angry": 生气/愤怒/暴躁情绪
        - "tired": 疲惫/无力/倦怠情绪
        - "neutral": 中性/未识别情绪
    
    检测流程：
        1. 文本预处理（转小写、去除空白）
        2. 关键词匹配（按优先级：happy → sad → angry → tired）
        3. 如果关键词未匹配，调用LLM API作为fallback
    """
    # 文本预处理：去除首尾空白并转换为小写
    msg = msg.strip().lower()

    # 定义各种情绪的关键词正则表达式
    # 开心情绪关键词：包含各种表达开心、高兴、满足的词汇
    happy_keywords = r"开心|高兴|爽|放假|赚到了|升职|中奖|顺利|早下班|轻松|如愿|愉快|得劲|躺赢|美滋滋|幸福|解放|自由|美好|满意|哈哈+|笑死|放松|心情好|喜悦|甜|舒服|满意|顺心|值得|有趣|喜欢|真香"
    
    # 悲伤情绪关键词：包含各种表达难过、失落、痛苦的词汇
    sad_keywords = r"难过|失落|伤心|心碎|沮丧|低落|绝望|想哭|崩溃|无助|被动|失望|郁闷|遗憾|痛苦|麻了|烦闷|愁|心情差|迷茫|不开心|凄凉|烦恼|孤独|抑郁|无力|想放弃|伤感|没希望|眼泪|苦"
    
    # 愤怒情绪关键词：包含各种表达生气、愤怒、暴躁的词汇
    angry_keywords = r"气死|生气|愤怒|火大|暴躁|崩溃|烦人|受够了|不爽|怒|忍不了|真无语|骂人|爆炸|烦死|疯了|什么玩意|操|服了|受气|欺负|挑衅|讨厌|狗东西|不讲理|怒火|发火|恼火|翻脸|吐槽|脾气|怒气|不耐烦"
    
    # 疲惫情绪关键词：包含各种表达疲惫、无力、倦怠的词汇
    tired_keywords = r"累|疲惫|搞不动|没力气|困|压力大|倦|撑不住|不想动|太难了|躺平|没精神|撑不下去|快倒了|乏|身心俱疲|筋疲力尽|虚脱|提不起劲|没状态|想睡|耗尽|无力|打不起精神|死气沉沉|拖延|没活力|不行了|懒得|倦怠|麻木|烦闷"
    
    # 按优先级进行关键词匹配
    if re.search(happy_keywords, msg):
        return "happy"  # 检测到开心情绪
    elif re.search(sad_keywords, msg):
        return "sad"  # 检测到悲伤情绪
    elif re.search(angry_keywords, msg):
        return "angry"  # 检测到愤怒情绪
    elif re.search(tired_keywords, msg):
        return "tired"  # 检测到疲惫情绪

    # 如果关键词规则无法匹配，使用LLM API作为fallback
    return llm_emotion_api(msg)

# Prompt 路由器，根据情绪分配对应的 prompt 类型
def route_prompt_by_emotion(emotion: str) -> str:
    """
    根据情绪返回对应的风格 prompt key
    注意：此函数与rag/prompt_router.py中的同名函数重复，建议统一使用rag模块中的版本
    
    参数：
        emotion (str): 检测到的情绪类型
        参数来源：detect_emotion函数返回的情绪标签
    
    返回：
        str: 对应的Prompt风格key
    """
    if emotion in ["happy", "neutral"]:
        return "light_expand"  # 开心和中性情绪使用轻松扩展风格
    elif emotion in ["tired"]:
        return "cheer_and_push"  # 疲惫情绪使用鼓励推动风格
    elif emotion in ["sad", "angry"]:
        return "co_regret"  # 悲伤和愤怒情绪使用共情安慰风格
    else:
        return "default"  # 其他情况使用兜底风格