# 状态摘要数据流程图

## 📊 数据来源总览

```
前端请求 → main.py → StateTracker → RAG Chain → LLM
```

## 🔄 详细数据流

### 1. 前端数据输入
```json
{
  "session_id": "5FC012F3-8553-4BC0-8AF9-6BE4FF4D0C76",
  "messages": [
    {"role": "assistant", "content": "好像有点生气了？我可以陪你说说看～"},
    {"role": "user", "content": "我好无语啊"}
  ]
}
```

### 2. 数据提取和处理

#### 2.1 对话历史提取
```python
# main.py 第 58-60 行
for m in request.messages:
    state.update_message(m.role, m.content)
```

**数据来源**: `request.messages` 数组
**存储位置**: `StateTracker.history` 列表
**格式**: `[(role, content), (role, content), ...]`

#### 2.2 情绪检测
```python
# main.py 第 65-67 行
emotion = detect_emotion(user_query)
state.update_emotion(emotion)
```

**数据来源**: 用户最新消息 `user_query`
**检测方法**: 
- 中文关键词检测 (`detect_emotion_chinese`)
- 英文模型检测 (`emotion_classifier`)
**存储位置**: `StateTracker.state["current_emotion"]`

#### 2.3 轮次计算
```python
# main.py 第 70-72 行
user_messages = [m for m in request.messages if m.role == "user"]
round_index = len(user_messages)
```

**数据来源**: 过滤后的用户消息数量
**用途**: 决定检索文档数量和策略

### 3. 状态摘要生成

#### 3.1 基础摘要 (当前实现)
```python
# dialogue/state_tracker.py 第 50-72 行
def summary(self, last_n: int = 3) -> str:
    lines: List[str] = []
    
    # 对话历史
    for role, content in self.history[-2 * last_n:]:
        speaker = "用户" if role == "user" else "AI"
        lines.append(f"• {speaker}: {content}")
    
    # 状态信息
    lines.append(f"当前情绪：{self.state['current_emotion']}")
    lines.append(f"最近使用技术：{self.state['technique_stack'][-last_n:]}")
    lines.append(f"用户价值观：{self.state['user_values']}")
    
    return "【对话历史及状态】\n" + "\n".join(lines)
```

#### 3.2 增强摘要 (建议实现)
```python
# dialogue/enhanced_state_tracker.py
def summary(self, last_n: int = 3) -> str:
    # 包含更多信息：
    # - 情绪变化趋势
    # - 用户关注的问题
    # - 实际使用的干预技术
    # - 用户价值观提取
```

### 4. 数据传递到 RAG Chain

```python
# main.py 第 78-83 行
answer = run_rag_chain(
    emotion=emotion,
    query=user_query,
    round_index=round_index,
    state_summary=context_summary  # 这里传递状态摘要
)
```

### 5. Prompt 中的使用

```python
# rag/rag_chain.py 第 58-65 行
prompt = RAG_PROMPT.format(
    emotion=emotion,
    round_index=round_index,
    state_summary=state_summary,  # 注入到 prompt 中
    context=context,
    question=query
)
```

## 📋 数据字段说明

### 当前实现的数据字段

| 字段 | 来源 | 更新时机 | 用途 |
|------|------|----------|------|
| `history` | 前端消息 | 每次请求 | 对话历史 |
| `current_emotion` | 情绪检测 | 每次用户消息 | 当前情绪状态 |
| `technique_stack` | 未使用 | 未实现 | 干预技术记录 |
| `user_values` | 未使用 | 未实现 | 用户价值观 |
| `technique_results` | 未使用 | 未实现 | 技术效果评估 |

### 建议增强的数据字段

| 字段 | 来源 | 更新时机 | 用途 |
|------|------|----------|------|
| `emotion_history` | 情绪检测 | 每次用户消息 | 情绪变化趋势 |
| `user_concerns` | 文本提取 | 每次用户消息 | 用户关注问题 |
| `conversation_topics` | 文本分析 | 每次消息 | 对话主题 |
| `technique_usage` | AI回复分析 | 每次AI回复 | 实际使用技术 |

## 🔧 改进建议

### 1. 立即改进
- 实现 `EnhancedStateTracker` 替换当前版本
- 添加情绪变化趋势分析
- 实现用户价值观自动提取

### 2. 中期改进
- 添加对话主题识别
- 实现干预技术效果评估
- 增加用户画像构建

### 3. 长期改进
- 集成更复杂的NLP分析
- 添加多模态情绪识别
- 实现个性化策略推荐 