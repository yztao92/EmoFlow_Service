# File: main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from rag.rag_chain import run_rag_chain
from llm.zhipu_llm import zhipu_chat_llm
from llm.emotion_detector import detect_emotion
from dialogue.state_tracker import StateTracker

# 会话状态存储：key 用 session_id
session_states: Dict[str, StateTracker] = {}

app = FastAPI()

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
    session_id: str                     # 唯一会话 ID
    moodScore: Optional[float] = None
    emotions: Optional[List[str]] = None
    messages: List[Message]


@app.post("/chat")
def chat_with_user(request: ChatRequest) -> Dict[str, Any]:
    try:
        print("\n🔔 收到请求：", request.json())

        # 1) 获取或初始化对话状态
        state = session_states.setdefault(request.session_id, StateTracker())

        # 2) 先将请求中的所有历史消息都记录到 state.history
        for m in request.messages:
            state.update_message(m.role, m.content)

        # 3) 最新一条用户提问
        user_query = request.messages[-1].content
        print(f"📨 [用户提问] {user_query}")

        # 4) 情绪识别并更新状态
        emotion = detect_emotion(user_query)
        state.update_emotion(emotion)
        print(f"🔍 [emotion] 检测到情绪 → {emotion}")

        # 5) 统计第几轮用户发言
        user_messages = [m for m in request.messages if m.role == "user"]
        round_index = len(user_messages)
        print(f"🔁 [轮次] 用户发言轮次：{round_index}")

        # 6) 生成并打印状态摘要（包括历史对话与当前状态）
        context_summary = state.summary(last_n=3)
        print(f"📝 [状态摘要]\n{context_summary}")

        # 7) 调用 RAG Chain，并把状态摘要传进去
        answer = run_rag_chain(
            emotion=emotion,
            query=user_query,
            round_index=round_index,
            state_summary=context_summary
        )

        # 8) 记录 AI 回复到历史中
        state.update_message("assistant", answer)

        return {
            "response": {
                "answer": answer,
                "references": []
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


@app.post("/journal/generate")
def generate_journal(request: ChatRequest) -> Dict[str, Any]:
    try:
        print("\n📝 收到生成心情日记请求：", request.json())

        # 生成系统提示
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        system_prompt = (
            "你是用户的情绪笔记助手，请根据以下对话内容，以“我”的视角，总结一段今天的心情日记。\n"
            "注意要自然、有情感，不要提到对话或 AI，只写个人的感受和经历：\n"
            "-----------\n"
            f"{prompt}\n"
            "-----------"
        )

        result = zhipu_chat_llm(system_prompt)
        journal = result.get("answer", "今天的心情有点复杂，暂时说不清楚。")

        return {"journal": journal}

    except Exception as e:
        import traceback
        print(f"[❌ ERROR] 心情日记生成失败: {e}")
        traceback.print_exc()
        return {"journal": "生成失败"}