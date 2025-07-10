# File: main.py

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from rag.rag_chain import run_rag_chain
from llm.zhipu_llm import zhipu_chat_llm
from llm.emotion_detector import detect_emotion
from dialogue.state_tracker import StateTracker

# 日志配置，确保多进程/热重载下也能输出日志
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)

# 检查必需的环境变量
required_env_vars = ["ZHIPUAI_API_KEY", "DEEPSEEK_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")

# 会话状态存储：key 用 session_id，value 为 StateTracker 实例
session_states: Dict[str, StateTracker] = {}

# 创建 FastAPI 实例
app = FastAPI()

# 允许所有跨域请求，便于前端/移动端调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """根路由，健康检查用"""
    return {"message": "EmoFlow 服务运行中"}

# 定义消息结构体
class Message(BaseModel):
    role: str
    content: str

# 定义聊天请求结构体
class ChatRequest(BaseModel):
    session_id: str                     # 唯一会话 ID
    messages: List[Message]             # 消息历史

@app.post("/chat")
def chat_with_user(request: ChatRequest) -> Dict[str, Any]:
    logging.info("收到 /chat 请求")  # 只要有请求 hit 到 /chat，这行日志一定会输出
    try:
        logging.info(f"\n🔔 收到请求：{request.json()}")
        state = session_states.setdefault(request.session_id, StateTracker())

        # 直接用前端传来的消息覆盖历史，避免重复
        state.history = [(m.role, m.content) for m in request.messages]

        # 3) 获取最新一条用户提问
        user_query = request.messages[-1].content
        logging.info(f"📨 [用户提问] {user_query}")

        # 4) 情绪识别并更新状态
        emotion = detect_emotion(user_query)
        state.update_emotion(emotion)
        logging.info(f"🔍 [emotion] 检测到情绪 → {emotion}")

        # 5) 统计第几轮用户发言
        user_messages = [m for m in request.messages if m.role == "user"]
        round_index = len(user_messages)
        logging.info(f"🔁 [轮次] 用户发言轮次：{round_index}")

        # 6) 生成并打印状态摘要（包括历史对话与当前状态）
        context_summary = state.summary(last_n=3)
        logging.info(f"📝 [状态摘要]\n{context_summary}")

        # brief_summary = state.generate_brief_summary(llm=zhipu_chat_llm)
        # logging.info(f"📌 [简要摘要 brief_summary] {brief_summary}")
        

        # 7) 调用 RAG Chain，并把状态摘要传进去，生成 AI 回复
        answer = run_rag_chain(
            emotion=emotion,
            query=user_query,
            round_index=round_index,
            state_summary=context_summary
            # brief_summary=brief_summary
        )

        # 8) 记录 AI 回复到历史中
        state.update_message("assistant", answer)

        return {
            "response": {
                "answer": answer,
                "references": []
            }
        }

    except ValueError as e:
        logging.error(f"[❌ ERROR] 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"[❌ ERROR] 聊天接口处理失败: {e}")
        return {
            "response": {
                "answer": "抱歉，系统暂时无法处理您的请求，请稍后再试。",
                "references": []
            }
        }

@app.post("/journal/generate")
def generate_journal(request: ChatRequest) -> Dict[str, Any]:
    """根据对话内容生成心情日记"""
    try:
        logging.info(f"\n📝 收到生成心情日记请求：{request.json()}")

        # 拼接所有历史消息为 prompt
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        system_prompt = f"""你是用户的情绪笔记助手，请根据以下对话内容，以"我"的视角，总结一段今天的心情日记。\n注意要自然、有情感，不要提到对话或 AI，只写个人的感受和经历：\n-----------\n{prompt}\n-----------"""

        # 调用 LLM 生成日记
        result = zhipu_chat_llm(system_prompt)
        journal = result.get("answer", "今天的心情有点复杂，暂时说不清楚。")

        return {"journal": journal}

    except Exception as e:
        logging.error(f"[❌ ERROR] 心情日记生成失败: {e}")
        return {"journal": "生成失败"}