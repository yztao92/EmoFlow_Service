from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm.chat import get_chat_response
from vectorstore.load_vectorstore import load_vectorstore

app = FastAPI()

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

@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
def chat_with_user(request: ChatRequest):
    try:
        print(f"[请求内容] query = {request.query}")
        result = get_chat_response(request.query)
        print(f"[响应内容] result = {result}")
        return result
    except Exception as e:
        print(f"[ERROR] 聊天接口处理失败: {e}")
        return {"error": str(e)}