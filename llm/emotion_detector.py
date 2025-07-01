# File: llm/emotion_detector.py

from transformers import pipeline

# 初始化多分类情绪识别模型（7 类）
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=False
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

def detect_emotion(text: str) -> str:
    """
    多分类情绪分析，返回 'happy','sad','angry','neutral' 五类。
    """
    result = emotion_classifier(text)[0]
    orig = result["label"].lower()
    return LABEL_MAP.get(orig, "neutral")