# File: llm/emotion_detector.py

from transformers import pipeline
import re

# 初始化多分类情绪识别模型（7 类）
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=1
)

# 原始标签到五类映射
LABEL_MAP = {
    "joy":      "happy",
    "sadness":  "sad",
    "anger":    "angry",
    "disgust":  "angry",
    "fear":     "sad",     # 将恐惧/害怕归为悲伤
    "surprise": "neutral",
    "neutral":  "neutral"
}

# 中文情绪关键词检测
CHINESE_EMOTION_KEYWORDS = {
    "angry": ["生气", "愤怒", "恼火", "烦躁", "暴躁", "火大", "气死", "气人", "讨厌", "烦死了"],
    "sad": ["难过", "伤心", "悲伤", "痛苦", "沮丧", "失落", "绝望", "想哭", "心情不好", "郁闷"],
    "happy": ["开心", "高兴", "快乐", "兴奋", "愉快", "心情好", "棒", "爽", "舒服", "满意"],
    "tired": ["累", "疲惫", "困", "想睡觉", "没精神", "乏力", "倦怠", "想休息"]
}

def detect_emotion_chinese(text: str) -> str:
    """
    基于中文关键词的情绪检测
    """
    text_lower = text.lower()
    
    # 统计每种情绪的关键词出现次数
    emotion_scores = {}
    for emotion, keywords in CHINESE_EMOTION_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            emotion_scores[emotion] = score
    
    # 返回得分最高的情绪
    if emotion_scores:
        return max(emotion_scores.items(), key=lambda x: x[1])[0]
    
    return None

def detect_emotion(text: str) -> str:
    """
    多分类情绪分析，返回 'happy','sad','angry','neutral','tired' 五类。
    优先使用中文关键词检测，如果检测不到则使用英文模型。
    """
    # 1. 首先尝试中文关键词检测
    chinese_emotion = detect_emotion_chinese(text)
    if chinese_emotion:
        return chinese_emotion
    
    # 2. 如果中文检测不到，使用英文模型
    try:
        results = emotion_classifier(text)  # top_k=1 返回嵌套列表
        if results and len(results) > 0 and len(results[0]) > 0:
            result = results[0][0]  # 取第一个结果中的第一个元素
            orig = result["label"].lower()
            return LABEL_MAP.get(orig, "neutral")
        else:
            return "neutral"  # 默认返回中性情绪
    except Exception as e:
        print(f"情绪检测模型调用失败: {e}")
        return "neutral"