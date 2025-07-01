# llm/emotion_detector.py
from transformers import pipeline

# 1）初始化：可换成你自己的模型或服务
emotion_classifier = pipeline("text-classification", model="uer/roberta-base-finetuned-jd-binary-seq")

# 2）对外接口
def detect_emotion(text: str) -> str:
    """
    返回一个情绪标签，如 'happy', 'sad', 'angry', 'tired'。
    """
    result = emotion_classifier(text)
    label = result[0]['label']
    # TODO: 将 label 映射到你的四个情绪
    mapping = {
        'LABEL_0': 'sad',
        'LABEL_1': 'happy',
    }
    return mapping.get(label, 'happy')