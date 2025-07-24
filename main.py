# File: main.py

import os
import logging
import requests
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from jose import jwt, jwk
from jose.utils import base64url_decode
from datetime import datetime, timedelta

from rag.rag_chain import run_rag_chain
from llm.deepseek_wrapper import DeepSeekLLM
from llm.emotion_detector import detect_emotion
from dialogue.state_tracker import StateTracker
from models import init_db, SessionLocal, User, Journal

from dotenv import load_dotenv
load_dotenv()

# JWT 配置项
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-fallback-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7

# Apple 配置
APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_CLIENT_ID = "Nick-Studio.EmoFlow"  # 替换为你的服务 ID

# Apple 公钥缓存
apple_keys = []

# 日志配置
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 检查必要环境变量
required_env_vars = ["DEEPSEEK_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")

# 初始化 DeepSeek LLM
_deepseek_llm = DeepSeekLLM()

def deepseek_chat_llm(prompt: str) -> dict:
    """使用 DeepSeek 生成回复"""
    try:
        from langchain_core.messages import HumanMessage
        response_text = _deepseek_llm._call([HumanMessage(content=prompt)])
        return {"answer": response_text}
    except Exception as e:
        logging.error(f"[❌ ERROR] DeepSeek LLM 调用失败: {e}")
        return {"answer": "生成失败"}

# FastAPI 初始化
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 启动时加载数据库 & Apple 公钥
session_states: Dict[str, StateTracker] = {}

@app.on_event("startup")
def on_startup():
    init_db()
    global apple_keys
    apple_keys = requests.get(APPLE_PUBLIC_KEYS_URL).json()["keys"]
    logger.info("✅ Apple 公钥加载成功")

@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

# ---------------------- Apple 登录认证 ----------------------

class AppleLoginRequest(BaseModel):
    identity_token: str
    full_name: Optional[str] = None
    email: Optional[str] = None

@app.post("/auth/apple")
def login_with_apple(req: AppleLoginRequest):
    try:
        logging.info(f"🔍 收到 Apple 登录请求: identity_token长度={len(req.identity_token)}, full_name='{req.full_name}', email='{req.email}'")
        # 处理 Base64 编码的令牌
        import base64
        try:
            # 尝试解码 Base64
            token_bytes = base64.b64decode(req.identity_token)
            token = token_bytes.decode('utf-8')
        except:
            # 如果不是 Base64，直接使用原始字符串
            token = req.identity_token
            
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]
        key_data = next((k for k in apple_keys if k["kid"] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Apple 公钥未找到")

        public_key = jwk.construct(key_data)
        message, encoded_sig = token.rsplit('.', 1)
        decoded_sig = base64url_decode(encoded_sig.encode())

        if not public_key.verify(message.encode(), decoded_sig):
            raise HTTPException(status_code=401, detail="无效签名")

        decoded = jwt.decode(
            token,
            key=public_key.to_pem().decode(),
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,
            issuer=APPLE_ISSUER
        )

        apple_user_id = decoded["sub"]
        # 优先使用前端发送的邮箱，如果没有则使用令牌中的邮箱
        email = req.email or decoded.get("email")
        # 获取用户姓名
        name = req.full_name

        db: Session = SessionLocal()
        user = db.query(User).filter(User.apple_user_id == apple_user_id).first()
        if not user:
            user = User(apple_user_id=apple_user_id, email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # 如果是现有用户，更新信息（如果前端提供了新的信息）
            updated = False
            if req.email and req.email != user.email:
                user.email = req.email
                updated = True
            if req.full_name and req.full_name != user.name:
                user.name = req.full_name
                updated = True
            if updated:
                db.commit()
                db.refresh(user)

        token_data = {
            "sub": str(user.id),
            "apple_user_id": user.apple_user_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        return {
            "status": "ok",
            "token": token,
            "user_id": user.id,
            "email": user.email,
            "name": user.name or f"用户{user.id}"  # 如果没有姓名，使用默认用户名
        }

    except Exception as e:
        logging.error(f"❌ Apple 登录失败: {e}")
        raise HTTPException(status_code=401, detail="Apple 登录验证失败")

def get_current_user(token: str = Header(...)) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的 Token")

# ---------------------- 聊天模块 ----------------------

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]

@app.post("/chat")
def chat_with_user(request: ChatRequest) -> Dict[str, Any]:
    logging.info("收到 /chat 请求")
    try:
        logging.info(f"\n🔔 收到请求：{request.json()}")
        state = session_states.setdefault(request.session_id, StateTracker())
        state.history = [(m.role, m.content) for m in request.messages]
        user_query = request.messages[-1].content
        logging.info(f"📨 [用户提问] {user_query}")

        emotion = detect_emotion(user_query)
        state.update_emotion(emotion)
        logging.info(f"🔍 [emotion] 检测到情绪 → {emotion}")

        user_messages = [m for m in request.messages if m.role == "user"]
        round_index = len(user_messages)
        logging.info(f"🔁 [轮次] 用户发言轮次：{round_index}")

        context_summary = state.summary(last_n=3)
        logging.info(f"📝 [状态摘要]\n{context_summary}")

        answer = run_rag_chain(
            query=user_query,
            round_index=round_index,
            state_summary=context_summary
        )

        state.update_message("assistant", answer)

        return {
            "response": {
                "answer": answer,
                "references": []
            }
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 聊天接口处理失败: {e}")
        return {
            "response": {
                "answer": "抱歉，系统暂时无法处理您的请求，请稍后再试。",
                "references": []
            }
        }

@app.post("/journal/generate")
def generate_journal(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 收到生成心情日记请求：用户ID={user_id}, 请求={request.json()}")
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        
        # 生成日记内容
        journal_system_prompt = f"""你是用户的情绪笔记助手，请根据以下对话内容，以"我"的视角，总结一段今天的心情日记。\n注意要自然、有情感，不要提到对话或 AI，只写个人的感受和经历：\n-----------\n{prompt}\n-----------"""
        
        journal_result = deepseek_chat_llm(journal_system_prompt)
        journal = journal_result.get("answer", "今天的心情有点复杂，暂时说不清楚。")
        
        # 生成日记标题
        title_system_prompt = f"""请根据以下心情日记内容，生成一个简洁、有情感、不超过10个字的标题。标题要体现日记的主要情感和主题：\n-----------\n{journal}\n-----------"""
        
        title_result = deepseek_chat_llm(title_system_prompt)
        title = title_result.get("answer", "今日心情")
        
        # 清理标题，确保简洁
        title = title.strip().replace('"', '').replace('"', '')
        if len(title) > 10:
            title = title[:10] + "..."
        
        # 保存日记到数据库
        db: Session = SessionLocal()
        try:
            journal_entry = Journal(
                user_id=user_id,
                title=title,
                content=journal,
                session_id=request.session_id
            )
            db.add(journal_entry)
            db.commit()
            db.refresh(journal_entry)
            logging.info(f"✅ 日记已保存到数据库，ID: {journal_entry.id}")
        except Exception as db_error:
            logging.error(f"❌ 保存日记到数据库失败: {db_error}")
            db.rollback()
        finally:
            db.close()
        
        return {
            "journal": journal,
            "title": title,
            "journal_id": journal_entry.id if 'journal_entry' in locals() else None,
            "status": "success"
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 心情日记生成失败: {e}")
        return {
            "journal": "生成失败",
            "title": "今日心情",
            "journal_id": None,
            "status": "error"
        }

@app.get("/journal/list")
def get_user_journals(user_id: int = Depends(get_current_user), limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """获取用户的日记列表"""
    try:
        db: Session = SessionLocal()
        journals = db.query(Journal).filter(
            Journal.user_id == user_id
        ).order_by(
            Journal.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        journal_list = []
        for journal in journals:
            journal_list.append({
                "id": journal.id,
                "title": journal.title,
                "content": journal.content,
                "session_id": journal.session_id,
                "created_at": journal.created_at.isoformat() if journal.created_at else None,
                "updated_at": journal.updated_at.isoformat() if journal.updated_at else None
            })
        
        # 获取总数
        total_count = db.query(Journal).filter(Journal.user_id == user_id).count()
        
        db.close()
        
        return {
            "status": "success",
            "journals": journal_list,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取用户日记列表失败: {e}")
        return {
            "status": "error",
            "journals": [],
            "total": 0,
            "message": "获取日记列表失败"
        }

@app.get("/journal/{journal_id}")
def get_journal_detail(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """获取特定日记的详细信息"""
    try:
        db: Session = SessionLocal()
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        journal_data = {
            "id": journal.id,
            "title": journal.title,
            "content": journal.content,
            "session_id": journal.session_id,
            "created_at": journal.created_at.isoformat() if journal.created_at else None,
            "updated_at": journal.updated_at.isoformat() if journal.updated_at else None
        }
        
        db.close()
        
        return {
            "status": "success",
            "journal": journal_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取日记详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取日记详情失败")

@app.delete("/journal/{journal_id}")
def delete_journal(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """删除用户的日记"""
    try:
        db: Session = SessionLocal()
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        db.delete(journal)
        db.commit()
        db.close()
        
        return {
            "status": "success",
            "message": "日记删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 删除日记失败: {e}")
        raise HTTPException(status_code=500, detail="删除日记失败")