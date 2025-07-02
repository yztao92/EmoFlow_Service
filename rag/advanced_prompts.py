# File: rag/advanced_prompts.py

# 危机关键词检测
CRISIS_KEYWORDS = {
    "自杀": ["自杀", "不想活了", "结束生命", "解脱", "死亡"],
    "自残": ["自残", "割腕", "伤害自己", "疼痛"],
    "绝望": ["绝望", "没有希望", "活不下去", "看不到未来"],
    "孤立": ["没人理解", "孤独", "被抛弃", "没人关心"]
}

# 情绪强度评估
EMOTION_INTENSITY = {
    "sad": {
        "mild": "轻微低落",
        "moderate": "明显悲伤", 
        "severe": "深度抑郁"
    },
    "angry": {
        "mild": "轻微不满",
        "moderate": "明显愤怒",
        "severe": "极度愤怒"
    },
    "happy": {
        "mild": "心情不错",
        "moderate": "明显开心",
        "severe": "非常兴奋"
    }
}

# 个性化回复模板
RESPONSE_TEMPLATES = {
    "crisis": {
        "immediate": "我听到你现在非常痛苦，你的感受很重要。请记住，你并不孤单，有很多人关心你。",
        "support": "如果你愿意，可以告诉我更多关于你的感受。我在这里陪伴你。",
        "resources": "如果你需要专业帮助，可以考虑联系心理咨询师或拨打心理热线。"
    },
    "emotional_support": {
        "sad": "我理解你现在的心情，这种感受是很正常的。每个人都会有低落的时候，你并不孤单。",
        "angry": "我能感受到你的愤怒，这种情绪是可以理解的。让我们一起来面对这个问题。",
        "happy": "看到你心情不错，我也为你感到高兴！继续保持这种积极的状态。"
    }
}

# 高级RAG Prompt
ADVANCED_RAG_PROMPT = """
你是一位专业的心理咨询师和情绪陪伴助手，具备丰富的心理学知识和共情能力。

## 用户状态分析
- **对话轮次**: 第 {round_index} 轮 ({round_strategy})
- **当前情绪**: {emotion} ({emotion_style})
- **情绪强度**: {emotion_intensity}
- **对话历史**: 
{state_summary}

## 专业知识参考
以下是与用户情绪相关的专业建议（请融入回复中，但不要直接引用）：
{context}

## 用户当前表达
{question}

## 危机评估
{crisis_assessment}

## 回复指导原则

### 1. 情绪适配策略
- **语调**: {tone}
- **方法**: {approach}
- **避免**: {avoid}

### 2. 回复结构要求
1. **共情阶段** (1-2句): 真实理解用户感受，避免表面化安慰
2. **支持阶段** (1-2句): 根据情绪类型和强度提供适当支持
3. **引导阶段** (1句): 温和引导用户继续表达或思考

### 3. 语言风格
- 自然口语化，像朋友间的真诚对话
- 避免专业术语、数字编号或格式化表达
- 保持温暖但不过度热情，专业但不冷漠
- 回复长度控制在3-5句话内

### 4. 特殊情况处理
- 如果检测到危机信号，优先关注用户安全并提供支持资源
- 如果用户情绪明显改善，可以适当总结和鼓励
- 如果用户需要具体建议，可以提供1-2个可操作的小建议

## 回复示例格式
```
[共情理解] 我理解你现在的感受...
[情绪支持] 这种[情绪描述]是很正常的...
[温和引导] 你愿意和我聊聊[相关话题]吗？
```

请根据以上指导生成一个自然、有温度、个性化的回复：
"""

# 危机检测函数
def detect_crisis(text: str) -> dict:
    """
    检测文本中是否包含危机信号
    """
    crisis_found = {}
    for crisis_type, keywords in CRISIS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                crisis_found[crisis_type] = True
                break
    
    return crisis_found

# 情绪强度评估函数
def assess_emotion_intensity(text: str, emotion: str) -> str:
    """
    基于文本内容和情绪类型评估情绪强度
    """
    intensity_indicators = {
        "mild": ["有点", "稍微", "一点点", "还好"],
        "moderate": ["很", "非常", "特别", "明显"],
        "severe": ["极度", "完全", "彻底", "崩溃", "绝望"]
    }
    
    for intensity, indicators in intensity_indicators.items():
        for indicator in indicators:
            if indicator in text:
                return EMOTION_INTENSITY.get(emotion, {}).get(intensity, "一般")
    
    return EMOTION_INTENSITY.get(emotion, {}).get("moderate", "一般") 