from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from llm.chat import get_chat_response
from vectorstore.load_vectorstore import load_vectorstore

app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时加载向量库
@app.on_event("startup")
def startup_event():
    print("🚀 正在加载知识库...")
    try:
        load_vectorstore()
        print("✅ 向量库加载完成")
    except Exception as e:
        print(f"❌ 向量库加载失败: {e}")

# 根路径返回健康信息
@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

# 定义消息结构
class Message(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str

# 定义聊天请求结构
class ChatRequest(BaseModel):
    moodScore: float
    messages: List[Message]

# 聊天接口
@app.post("/chat")
def chat_with_user(request: ChatRequest):
    try:
        print(f"[请求内容] moodScore = {request.moodScore}")
        for msg in request.messages:
            print(f" - {msg.role}: {msg.content}")

        # 拼接历史消息为 prompt
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])

        # 调用大模型
        result = get_chat_response(prompt)

        print(f"[响应内容] result = {result}")
        return {"response": result}
    except Exception as e:
        import traceback
        print(f"[ERROR] 聊天接口处理失败: {e}")
        traceback.print_exc()
        return {"error": str(e)}