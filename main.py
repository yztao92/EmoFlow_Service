from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from llm.chat import get_chat_response
from vectorstore.load_vectorstore import load_vectorstores, get_retriever

app = FastAPI()

# 启动时加载全部向量库
load_vectorstores()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        # ✅ 根据 moodScore 选择分类
        mood = request.moodScore
        if mood < 4:
            category = "act"
        else:
            category = "happiness_trap"

        print(f"[请求内容] query = {prompt}")
        retriever = get_retriever(category)
        result = get_chat_response(prompt, retriever)

        print(f"[响应内容] result = {result}")
        return {"response": result}
    except Exception as e:
        import traceback
        print(f"[ERROR] 聊天接口处理失败: {e}")
        traceback.print_exc()
        return {"error": str(e)}