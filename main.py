from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from llm.chat import get_chat_response
from vectorstore.load_vectorstore import load_vectorstores

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

# 支持两种请求体格式：旧版 moodScore 或 新版 emotions
class ChatRequest(BaseModel):
    # 旧版兼容
    moodScore: Optional[float] = None

    # 新版情绪列表，直接接收前端传来的 ["happy", "sad", ...]
    emotions: Optional[List[str]] = None

    messages: List[Message]

@app.post("/chat")
def chat_with_user(request: ChatRequest) -> Dict[str, Any]:
    try:
        # 🌟 先打印接收到的原始 JSON，方便调试
        print("\n🔔 收到请求：", request.json())

        # 🧠 计算分类 category
        if request.moodScore is not None:
            category = "act" if request.moodScore < 4 else "happiness_trap"
            print(f"🔍 [moodScore 分类] moodScore={request.moodScore} → {category}")
        elif request.emotions:
            # 简单示例：如果是"angry"，走 act，否则 happiness_trap
            if "angry" in request.emotions:
                category = "act"
            else:
                category = "happiness_trap"
            print(f"🔍 [emotions 分类] emotions={request.emotions} → {category}")
        else:
            category = "act"
            print("🔍 [分类默认] 没有传 moodScore/emotions，默认 act")

        # 📨 拼接 Prompt
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        print(f"📨 [拼接 Prompt]\n{prompt}")

        # 🤖 调用 AI
        result = get_chat_response(prompt, category)

        # ✅ 构造返回
        answer = result.get("answer", "很抱歉，AI 暂时没有给出回应。")
        references = result.get("references", [])

        # 🌟 最终返回格式，FastAPI 会自动转成 JSON
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
        # 一定返回合法 JSON
        return {
            "response": {
                "answer": "发生错误，AI 无法完成响应。",
                "references": []
            }
        }