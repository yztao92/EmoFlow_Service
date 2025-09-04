# 记忆点在对话提示中的集成指南

## 概述

现在您可以将用户的记忆点集成到对话提示中，让AI更好地了解用户的背景、最近经历和情绪状态，从而提供更个性化和相关的回应。

## 功能特性

### 1. 记忆点检索
- **最新记忆点**: 获取用户最新的5个记忆点
- **情绪相关**: 根据情绪类型筛选相关记忆点
- **智能摘要**: 生成格式化的记忆点摘要

### 2. 对话提示集成
- **自动添加**: 在对话提示中自动包含用户记忆点
- **上下文增强**: 让AI了解用户的背景和经历
- **个性化回应**: 基于记忆点提供更贴切的建议

## 使用方法

### 1. 基本记忆点检索

#### 获取用户最新记忆点
```python
from memory import get_user_latest_memories

# 获取用户最新的5个记忆点
memories = get_user_latest_memories(user_id=1, limit=5)

# 输出示例:
# [
#   "坚持每日健身，通过举铁释放压力，获得身心放松与内心的平静",
#   "与老友重逢，共忆北京往事，虽异地难聚，但深厚情谊未变，内心感到踏实温暖",
#   ...
# ]
```

#### 根据情绪获取相关记忆点
```python
from memory import get_user_memories_by_emotion

# 获取用户"happy"情绪的记忆点
happy_memories = get_user_memories_by_emotion(user_id=1, emotion="happy", limit=3)

# 获取用户"peaceful"情绪的记忆点
peaceful_memories = get_user_memories_by_emotion(user_id=1, emotion="peaceful", limit=3)
```

#### 获取记忆点摘要
```python
from memory import get_user_memories_summary

# 获取格式化的记忆点摘要
summary = get_user_memories_summary(user_id=1, limit=5)

# 输出示例:
# 1. 坚持每日健身，通过举铁释放压力，获得身心放松与内心的平静
# 2. 与老友重逢，共忆北京往事，虽异地难聚，但深厚情谊未变，内心感到踏实温暖
# 3. 健身取得突破，卧推达到65kg 3*3，感到充实并体会到坚持付出的回报
# ...
```

### 2. 在对话提示中集成

#### 修改对话提示生成函数
```python
from memory import get_user_latest_memories
from prompts.chat_prompts_generator import build_final_prompt

def generate_chat_prompt(user_id: int, analysis_result: dict, state_summary: str, question: str):
    # 获取用户最新记忆点
    user_memories = get_user_latest_memories(user_id, limit=5)
    
    # 生成包含记忆点的提示
    final_prompt = build_final_prompt(
        ana=analysis_result,
        state_summary=state_summary,
        question=question,
        user_memories=user_memories  # 新增参数
    )
    
    return final_prompt
```

#### 提示词结构示例
```
# 角色与风格
你是一个温柔、细心、不催促的情绪陪伴者...

# 回应策略
** 核心策略 **
- 用户已经分享了具体原因，现在应该转向问题解决模式...

# 用户记忆点
以下是用户之前分享的记忆点，可以帮助更好地理解当前情绪：
1. 坚持每日健身，通过举铁释放压力，获得身心放松与内心的平静
2. 与老友重逢，共忆北京往事，虽异地难聚，但深厚情谊未变，内心感到踏实温暖
3. 健身取得突破，卧推达到65kg 3*3，感到充实并体会到坚持付出的回报

# 当前上下文摘要
## 用户情绪
peaceful
## 历史对话
...
## 当前用户输入
...

请根据上述角色设定和回应策略，给出合适的回复：
```

### 3. 高级用法

#### 根据当前情绪动态选择记忆点
```python
def get_contextual_memories(user_id: int, current_emotion: str):
    """根据当前情绪获取相关记忆点"""
    
    # 获取最新记忆点
    latest_memories = get_user_latest_memories(user_id, limit=3)
    
    # 获取情绪相关记忆点
    emotion_memories = get_user_memories_by_emotion(user_id, current_emotion, limit=2)
    
    # 合并并去重
    all_memories = latest_memories + emotion_memories
    unique_memories = list(dict.fromkeys(all_memories))  # 保持顺序的去重
    
    return unique_memories[:5]  # 返回最多5个
```

#### 智能记忆点筛选
```python
def get_smart_memories(user_id: int, question: str, limit: int = 5):
    """智能筛选与当前问题相关的记忆点"""
    
    # 获取最新记忆点
    memories = get_user_latest_memories(user_id, limit=limit * 2)
    
    # 这里可以添加更智能的筛选逻辑
    # 比如基于关键词匹配、情绪相关性等
    
    return memories[:limit]
```

## 集成到现有系统

### 1. 修改对话流程

在您现有的对话系统中，找到生成提示词的地方，添加记忆点检索：

```python
# 在对话处理函数中
def process_chat_message(user_id: int, message: str):
    # ... 现有的分析逻辑 ...
    
    # 获取用户记忆点
    user_memories = get_user_latest_memories(user_id, limit=5)
    
    # 生成包含记忆点的提示
    prompt = build_final_prompt(
        ana=analysis_result,
        state_summary=state_summary,
        question=message,
        user_memories=user_memories
    )
    
    # 调用LLM
    response = call_llm(prompt)
    
    return response
```

### 2. 在main.py中集成

如果您想在现有的API中集成，可以这样修改：

```python
@app.post("/chat")
def chat_endpoint(request: ChatRequest, user_id: int = Depends(get_current_user)):
    # ... 现有的聊天逻辑 ...
    
    # 获取用户记忆点
    from memory import get_user_latest_memories
    user_memories = get_user_latest_memories(user_id, limit=5)
    
    # 生成提示词时包含记忆点
    final_prompt = build_final_prompt(
        ana=analysis_result,
        state_summary=state_summary,
        question=request.message,
        user_memories=user_memories
    )
    
    # ... 继续处理 ...
```

## 效果示例

### 1. 没有记忆点的对话
**用户**: "我今天感觉有点累"
**AI**: "听起来你今天确实很疲惫，能告诉我发生了什么吗？"

### 2. 有记忆点的对话
**用户**: "我今天感觉有点累"
**AI**: "我注意到你最近一直在坚持健身，通过举铁来释放压力。今天感觉累，是不是健身强度太大，或者有其他事情让你感到疲惫？"

### 3. 记忆点带来的优势
- **个性化理解**: AI了解用户的健身习惯和压力管理方式
- **相关建议**: 可以结合用户的健身经验给出建议
- **情感连接**: 让用户感受到AI真正了解他们的生活

## 配置和优化

### 1. 记忆点数量
- **默认数量**: 5个记忆点
- **建议范围**: 3-7个
- **考虑因素**: 提示词长度、LLM处理能力、用户隐私

### 2. 记忆点筛选策略
- **时间优先**: 最新的记忆点
- **情绪相关**: 与当前情绪匹配的记忆点
- **主题相关**: 与当前话题相关的记忆点

### 3. 性能优化
- **缓存机制**: 可以缓存用户的记忆点
- **批量查询**: 减少数据库查询次数
- **智能更新**: 只在必要时更新记忆点

## 注意事项

### 1. 隐私保护
- 记忆点包含用户的个人信息
- 确保在安全的环境中处理
- 考虑用户是否愿意分享这些信息

### 2. 提示词长度
- 记忆点会增加提示词长度
- 监控LLM的token使用量
- 在必要时精简记忆点内容

### 3. 错误处理
- 如果记忆点获取失败，不影响正常对话
- 记录错误日志，便于排查问题
- 提供降级方案

## 总结

记忆点集成到对话提示中，可以显著提升AI的个性化程度和回应质量：

✅ **个性化体验**: AI了解用户的背景和经历  
✅ **相关建议**: 基于记忆点提供更贴切的建议  
✅ **情感连接**: 让用户感受到被理解和支持  
✅ **上下文增强**: 对话更加连贯和有深度  

通过合理使用记忆点，您的AI陪伴系统将变得更加智能和人性化！

