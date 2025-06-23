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

@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

# 定义消息结构
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    moodScore: float
    messages: List[Message]

@app.post("/chat")
def chat_with_user(request: ChatRequest):
    try:
        # 🧠 打印情绪分数
        print(f"\n🧠 [请求情绪分数] moodScore = {request.moodScore}")

        # 🔍 决定知识库分类
        category = "act" if request.moodScore < 4 else "happiness_trap"
        print(f"🔍 [使用知识库分类] category = {category}")

        # 📨 拼接 Prompt
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        print(f"📨 [拼接 Prompt]\n{prompt}")

        # 🤖 获取 AI 响应
        result = get_chat_response(prompt, category)

        # ✅ 输出 answer
        answer = result.get("answer", "很抱歉，AI 暂时没有给出回应。")
        print(f"\n🤖 [AI 回答内容]\n{answer}")

        # ✅ 输出引用
        references = result.get("references", [])
        print(f"\n📚 [引用内容片段]")
        for i, ref in enumerate(references):
            print(f" - [{i+1}] {ref}")

        # 返回给前端
        return {
            "response": {
                "answer": answer,
                "references": references
            }
        }

    except Exception as e:
        import traceback
        print(f"[❌ ERROR] 聊天接口处理失败: {e}")
        traceback.print_exc()
        return {
            "response": {
                "answer": "发生错误，AI 无法完成响应。",
                "references": []
            }
        }