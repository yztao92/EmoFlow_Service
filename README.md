# EmoFlow - 情绪陪伴助手

一个基于大语言模型的智能情绪陪伴系统，能够识别用户情绪并提供个性化的心理支持。

## 功能特性

- 🤖 智能情绪识别：自动分析用户情绪状态
- 💬 个性化对话：基于情绪状态提供定制化回复
- 📚 知识检索：RAG系统提供专业心理知识支持
- 📝 心情日记：自动生成个人心情总结
- 🔄 状态跟踪：维护对话上下文和用户状态

## 技术架构

- **后端框架**: FastAPI
- **大语言模型**: DeepSeek Chat + 智谱AI
- **向量数据库**: FAISS
- **嵌入模型**: 智谱AI Embedding
- **情绪识别**: Transformers (DistilRoBERTa)

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd EmoFlow

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境配置

创建 `.env` 文件并配置以下环境变量：

```env
# API Keys
ZHIPUAI_API_KEY=your_zhipu_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Vector Store Configuration
VECTORSTORE_BASE=data/vectorstore_by_summary

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 3. 构建向量库

```bash
cd embedding
python build_vectorstore.py
```

### 4. 启动服务

```bash
python start_server.py
```

服务将在 `http://localhost:8000` 启动

## API 接口

### 聊天接口

```http
POST /chat
Content-Type: application/json

{
  "session_id": "unique_session_id",
  "messages": [
    {"role": "user", "content": "我今天心情不太好"}
  ]
}
```

### 心情日记生成

```http
POST /journal/generate
Content-Type: application/json

{
  "session_id": "unique_session_id",
  "messages": [
    {"role": "user", "content": "今天真的很累"},
    {"role": "assistant", "content": "听起来你今天承受了不少压力"},
    {"role": "user", "content": "晚上想早点睡"}
  ]
}
```

## 项目结构

```
EmoFlow/
├── main.py                 # FastAPI 主应用
├── requirements.txt        # 依赖包列表
├── start_server.py        # 服务器启动脚本
├── llm/                   # 大语言模型相关
│   ├── deepseek_wrapper.py
│   ├── zhipu_llm.py
│   ├── zhipu_embedding.py
│   └── emotion_detector.py
├── rag/                   # RAG 检索增强生成
│   ├── rag_chain.py
│   └── prompts.py
├── dialogue/              # 对话管理
│   └── state_tracker.py
├── vectorstore/           # 向量数据库
│   └── load_vectorstore.py
├── embedding/             # 向量库构建
│   └── build_vectorstore.py
├── data/                  # 数据文件
│   └── vectorstore_by_summary/
└── test/                  # 测试文件
    ├── test_chat.py
    └── test.py
```

## 开发说明

### 添加新的情绪类型

1. 在 `llm/emotion_detector.py` 中更新 `LABEL_MAP`
2. 确保向量库中包含对应情绪的数据
3. 更新 `rag/prompts.py` 中的提示词

### 自定义提示词

编辑 `rag/prompts.py` 文件中的 `RAG_PROMPT` 来调整AI的回复风格和行为。

## 故障排除

### 常见问题

1. **向量库不存在**
   - 运行 `python embedding/build_vectorstore.py`

2. **API密钥错误**
   - 检查 `.env` 文件中的API密钥配置

3. **依赖包缺失**
   - 运行 `pip install -r requirements.txt`

## 许可证

MIT License 