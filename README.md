# EmoFlow Service

一个基于情感识别的智能对话系统，提供个性化的心理支持和情感陪伴。

## 🌟 核心特性

- **情感识别**: 实时识别用户情绪状态
- **个性化回复**: 根据情绪调整回复风格和内容
- **知识检索**: 基于向量数据库的智能知识检索
- **对话记忆**: 维护对话历史和用户状态
- **多模态支持**: 支持文本、图片等多种输入形式

## 🏗️ 技术架构

### **AI模型栈**
- **Embedding模型**: 千问 `text-embedding-v4` - 文本向量化
- **LLM模型**: 千问 `qwen-turbo` - 对话生成
- **向量数据库**: FAISS - 高效相似度检索
- **元数据库**: SQLite - 存储文档元数据

### **核心组件**
- **FastAPI**: Web框架，提供RESTful API
- **JWT认证**: 用户身份验证
- **Supervisor**: 进程监控和自动重启
- **RAG系统**: 检索增强生成

## 📁 项目结构

```
EmoFlow_Service/
├── main.py                    # FastAPI主应用
├── database_models/           # 数据库模型定义
│   ├── __init__.py           # 模型包初始化
│   ├── database.py           # 数据库配置
│   ├── user.py               # 用户模型
│   ├── journal.py            # 日记模型
│   └── schemas.py            # 数据验证模型
├── rag/                       # RAG检索增强生成
│   ├── rag_chain.py          # RAG核心逻辑
│   ├── prompt_router.py      # Prompt路由
│   └── prompts.py            # Prompt模板
├── llm/                       # LLM相关
│   ├── llm_factory.py        # LLM工厂
│   ├── qwen_llm.py           # 千问LLM包装器
│   ├── qwen_embedding_factory.py # 千问Embedding
│   └── deepseek_wrapper.py   # DeepSeek备用LLM
├── vectorstore/               # 向量库
│   └── qwen_vectorstore.py   # 千问向量库检索
├── dialogue/                  # 对话管理
│   └── state_tracker.py      # 对话状态跟踪
├── supervisor/                # 进程管理
│   ├── emoflow_supervisor_simple.conf # Supervisor配置
│   ├── setup_supervisor.sh   # Supervisor安装脚本
│   ├── start_emoflow.sh      # 服务启动脚本
│   └── SUPERVISOR_README.md  # Supervisor使用说明
├── dataset/                   # 数据集
│   ├── faiss_index.bin       # FAISS向量库
│   └── metadata.db           # SQLite元数据库
├── services/                  # 业务服务
├── test/                      # 测试文件
├── logs/                      # 日志文件
├── venv/                      # 虚拟环境
├── requirements.txt           # 依赖文件
├── .env                       # 环境变量
└── README.md                  # 项目说明
```

## 🚀 快速开始

### **环境要求**
- Python 3.8+
- 千问API密钥
- 8GB+ 内存（推荐16GB）

### **安装步骤**

1. **克隆项目**
```bash
git clone <repository-url>
cd EmoFlow_Service
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
QIANWEN_API_KEY=your_qianwen_api_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
```

5. **启动服务**
```bash
# 开发模式
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式（使用Supervisor）
./supervisor/setup_supervisor.sh
```

## 🔧 配置说明

### **环境变量**
```bash
# 必需配置
QIANWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx  # 千问API密钥
JWT_SECRET_KEY=your_jwt_secret_key_here      # JWT密钥

# 可选配置
LOG_LEVEL=INFO                                # 日志级别
DATABASE_URL=sqlite:///database/emoflow.db   # 数据库URL
```

### **API密钥获取**
1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 开通千问服务
3. 创建API密钥
4. 将密钥填入 `.env` 文件

## 📚 API文档

### **主要接口**

#### **聊天接口**
```http
POST /chat
Content-Type: application/json

{
  "session_id": "session_123",
  "messages": [
    {"role": "user", "content": "我今天心情很糟糕"}
  ],
  "emotion": "sad"
}
```

#### **日记生成**
```http
POST /journal/generate
Authorization: Bearer <jwt_token>

{
  "session_id": "session_123",
  "messages": [...]
}
```

#### **Apple登录**
```http
POST /auth/apple
Content-Type: application/json

{
  "identity_token": "apple_identity_token",
  "full_name": "用户姓名",
  "email": "user@example.com"
}
```

## 🔄 系统流程

### **完整对话流程**
```
用户输入 → 千问Embedding → FAISS检索 → 千问LLM生成 → 用户回复
```

1. **用户输入**: 接收用户问题和情绪
2. **向量化**: 使用千问 `text-embedding-v4` 生成向量
3. **检索**: 在FAISS向量库中检索相似文档
4. **生成**: 使用千问 `qwen-turbo` 生成回复
5. **返回**: 返回个性化回复给用户

### **状态管理**
- **对话历史**: 维护完整的对话记录
- **情绪跟踪**: 记录用户情绪变化
- **技术使用**: 跟踪AI使用的心理干预技术

## 🛠️ 开发指南

### **添加新的LLM**
1. 在 `llm/` 目录下创建新的LLM包装器
2. 在 `llm_factory.py` 中添加对应的工厂函数
3. 更新配置和文档

### **扩展向量库**
1. 准备新的文档数据
2. 使用千问embedding模型生成向量
3. 更新FAISS索引和SQLite元数据库

### **自定义Prompt**
1. 在 `rag/prompts.py` 中添加新的Prompt模板
2. 在 `rag/prompt_router.py` 中添加路由规则
3. 测试新的Prompt效果

## 📊 性能指标

- **响应时间**: 平均 < 2秒
- **检索准确率**: > 85%
- **向量库规模**: 7388个文档
- **支持并发**: 100+ 并发用户

## 🔒 安全特性

- **JWT认证**: 安全的用户身份验证
- **API限流**: 防止恶意请求
- **数据加密**: 敏感数据加密存储
- **日志审计**: 完整的操作日志

## 📝 更新日志

### **v2.0.0** (2025-07-31)
- ✅ 升级到千问AI栈（Embedding + LLM）
- ✅ 移除情绪过滤，简化检索逻辑
- ✅ 优化向量库检索性能
- ✅ 添加备用LLM机制
- ✅ 清理过时文件，优化项目结构
- ✅ 整理Supervisor相关文件到独立文件夹

### **v1.0.0** (2025-07-14)
- 🎉 初始版本发布
- ✅ 基础聊天功能
- ✅ 情感识别系统
- ✅ RAG检索增强

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 邮箱: [your-email@example.com]

---

**EmoFlow Service** - 让AI更懂你的心 ❤️ 