# File: main.py
# 功能：EmoFlow 情绪陪伴助手的主应用入口
# 包含：FastAPI 应用、用户认证、聊天接口、日记功能等核心API

import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from jose import jwt, jwk
from jose.utils import base64url_decode
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# —— 新编排：分析→（可选检索）→生成
from prompts.prompt_flow_controller import chat_once
from prompts.chat_analysis import analyze_turn
from dialogue.state_tracker import StateTracker
from database_models import init_db, SessionLocal, User, Journal
from database_models.schemas import UpdateProfileRequest

from dotenv import load_dotenv
load_dotenv()

# ==================== JWT 认证 ====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-fallback-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# ==================== Apple 登录配置 ====================
APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_CLIENT_ID = "Nick-Studio.EmoFlow"
apple_keys = []

# ==================== 日志 ====================
for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ==================== 环境变量检查 ====================
required_env_vars = ["QIANWEN_API_KEY"]
missing = [v for v in required_env_vars if not os.getenv(v)]
if missing:
    raise ValueError(f"缺少必需的环境变量: {', '.join(missing)}")

# ==================== FastAPI 初始化 ====================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产请限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局状态 & 定时任务 ====================
session_states: Dict[str, StateTracker] = {}
scheduler = BackgroundScheduler()

@app.on_event("startup")
def on_startup():
    init_db()
    global apple_keys
    apple_keys = requests.get(APPLE_PUBLIC_KEYS_URL).json()["keys"]

    # 可选：初始化 embedding
    try:
        from llm.qwen_embedding_factory import get_qwen_embedding_model
        _ = get_qwen_embedding_model()
    except Exception as e:
        logging.warning(f"⚠️ Embedding模型初始化失败: {e}")
        logging.warning("⚠️ 检索功能可能不可用（不影响聊天主流程）")

    start_heart_reset_scheduler()

def reset_all_users_heart():
    try:
        logging.info("🕛 开始执行：重置所有用户heart值")
        db: Session = SessionLocal()
        try:
            total = db.query(User).count()
            db.query(User).update({"heart": 100})
            db.commit()
            logging.info(f"✅ 已重置 {total} 个用户heart=100")
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 定时任务失败：{e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logging.error(f"❌ 定时任务异常：{e}")

def start_heart_reset_scheduler():
    try:
        scheduler.add_job(
            func=reset_all_users_heart,
            trigger=CronTrigger(hour=0, minute=0),
            id="heart_reset_job",
            name="每日重置用户heart值",
            replace_existing=True,
        )
        scheduler.start()
        logging.info("✅ Heart重置任务已启动：每天00:00执行")
    except Exception as e:
        logging.error(f"❌ 启动定时任务失败：{e}")

@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()
        logging.info("✅ 定时任务调度器已关闭")

# ==================== 健康检查 ====================
@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

# ==================== Apple 登录 ====================
class AppleLoginRequest(BaseModel):
    identity_token: str
    full_name: Optional[str] = None
    email: Optional[str] = None

@app.post("/auth/apple")
def login_with_apple(req: AppleLoginRequest):
    try:
        logging.info(f"🔍 Apple 登录: token_len={len(req.identity_token)}, name='{req.full_name}', email='{req.email}'")
        import base64
        try:
            token_bytes = base64.b64decode(req.identity_token)
            token = token_bytes.decode("utf-8")
        except Exception:
            token = req.identity_token

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]
        key_data = next((k for k in apple_keys if k["kid"] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Apple 公钥未找到")

        public_key = jwk.construct(key_data)
        message, encoded_sig = token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode())
        if not public_key.verify(message.encode(), decoded_sig):
            raise HTTPException(status_code=401, detail="无效签名")

        decoded = jwt.decode(
            token,
            key=public_key.to_pem().decode(),
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,
            issuer=APPLE_ISSUER,
        )

        apple_user_id = decoded["sub"]
        email = req.email or decoded.get("email")
        name = req.full_name

        db: Session = SessionLocal()
        user = db.query(User).filter(User.apple_user_id == apple_user_id).first()
        if not user:
            user = User(apple_user_id=apple_user_id, email=email, name=name)
            db.add(user); db.commit(); db.refresh(user)
        else:
            updated = False
            if req.email and req.email != user.email:
                user.email = req.email; updated = True
            if req.full_name and req.full_name != user.name:
                user.name = req.full_name; updated = True
            if updated:
                db.commit(); db.refresh(user)

        token_data = {"sub": str(user.id), "apple_user_id": user.apple_user_id,
                      "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)}
        token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        return {"status": "ok", "token": token, "user_id": user.id, "email": user.email, "name": user.name}
    except Exception as e:
        logging.error(f"❌ Apple 登录失败: {e}")
        raise HTTPException(status_code=401, detail="Apple 登录验证失败")

def get_current_user(token: str = Header(...)) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的 Token")

# ==================== 用户资料 ====================
# 使用database_models.schemas中的UpdateProfileRequest

@app.put("/user/profile")
def update_user_profile(request: UpdateProfileRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"🔧 更新资料: user_id={user_id}, name='{request.name}', email='{request.email}', is_member={request.is_member}, birthday={request.birthday}, membership_expires_at={request.membership_expires_at}")
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        updated = False
        if request.name is not None and request.name != user.name:
            user.name = request.name; updated = True
        if request.email is not None and request.email != user.email:
            user.email = request.email; updated = True
        if request.is_member is not None and request.is_member != user.is_member:
            user.is_member = request.is_member; updated = True
        if request.birthday is not None and request.birthday != user.birthday:
            user.birthday = request.birthday; updated = True

        if request.membership_expires_at is not None and request.membership_expires_at != user.membership_expires_at:
            user.membership_expires_at = request.membership_expires_at; updated = True
        if updated:
            db.commit(); db.refresh(user)

        return {"status": "ok",
                "message": "用户资料更新成功" if updated else "用户资料无变化",
                "user": {"id": user.id, "name": user.name, "email": user.email, "heart": user.heart, "is_member": user.is_member, "birthday": user.birthday, "membership_expires_at": user.membership_expires_at}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 用户资料更新失败: {e}")
        raise HTTPException(status_code=500, detail="用户资料更新失败")

@app.get("/user/profile")
def get_user_profile(user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"status": "ok",
                "user": {"id": user.id, "name": user.name, "email": user.email, "heart": user.heart, "is_member": user.is_member, "birthday": user.birthday, "membership_expires_at": user.membership_expires_at}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取用户资料失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")

# ==================== 心数 ====================
class UpdateHeartRequest(BaseModel):
    heart: int

@app.put("/user/heart")
def update_user_heart(request: UpdateHeartRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"🔧 更新heart: user_id={user_id}, heart={request.heart}")
        if request.heart < 0:
            raise HTTPException(status_code=400, detail="心数值不能为负数")
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.heart = request.heart
        db.commit(); db.refresh(user)
        return {"status": "ok", "message": "心数更新成功", "user": {"id": user.id, "heart": user.heart}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 更新用户心数失败: {e}")
        raise HTTPException(status_code=500, detail="更新用户心数失败")

@app.get("/user/heart")
def get_user_heart(user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"status": "ok", "user": {"id": user.id, "heart": user.heart}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取用户心数失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户心数失败")

# ==================== 聊天 ====================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]
    emotion: Optional[str] = None  # 该字段不影响分析链路

class ManualJournalRequest(BaseModel):
    content: str
    emotion: Optional[str] = None

class UpdateJournalRequest(BaseModel):
    content: Optional[str] = None
    emotion: Optional[str] = None

@app.post("/chat")
def chat_with_user(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info("=" * 60)
        logging.info("💬 聊天接口调用")
        logging.info("=" * 60)
        logging.info(f"用户ID: {user_id}")
        logging.info(f"会话ID: {request.session_id}")
        logging.info(f"情绪标签: {request.emotion}")
        
        # 1) Heart 扣减
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            if user.heart < 2:
                raise HTTPException(status_code=403, detail="心数不足，无法继续聊天，请等待明天重置或充值")
            user.heart -= 2
            db.commit(); db.refresh(user)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 更新用户heart值失败: {e}")
            raise HTTPException(status_code=500, detail="系统错误，请稍后再试")
        finally:
            db.close()

        # 2) 会话状态
        session_key = f"user_{user_id}_{request.session_id}"
        state = session_states.setdefault(session_key, StateTracker())

        # 3) 提取用户最新消息
        user_messages = [m for m in request.messages if m.role == "user"]
        user_query = user_messages[-1].content if user_messages else ""

        # 获取用户信息并打印
        db: Session = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        db.close()
        
        if user_messages:
            logging.info(f"用户昵称: {u.name}")
            logging.info(f"用户输入: {user_query}")
        else:
            logging.info(f"用户昵称: {u.name}")
            logging.info("用户输入: 无")
        
        logging.info("=" * 60)

        # 4) 轮次与摘要
        round_index = len(user_messages)
        context_summary = state.summary(last_n=1000)  # 显示全量对话历史

        # 5) 启发式信号
        explicit_close_phrases = ("先这样", "改天聊", "下次再聊", "谢谢就到这", "收工", "结束", "先到这")
        new_topic_phrases      = ("另外", "换个话题", "说个别的", "还有一件事", "顺便", "对了")
        target_resolved_phrases= ("明白了", "搞定了", "已经解决", "了解了", "知道了", "可以了")
        uq = user_query or ""
        explicit_close  = any(p in uq for p in explicit_close_phrases)
        new_topic       = any(p in uq for p in new_topic_phrases)
        target_resolved = any(p in uq for p in target_resolved_phrases)

        # 6) 分析：LLM 语义 + 规则机派生
        logging.info("=" * 50)
        logging.info("🚀 开始对话分析")
        logging.info("=" * 50)
        logging.info(f"轮次: {round_index}")
        logging.info(f"用户输入: {user_query}")
        logging.info(f"对话历史: {context_summary}")
        
        # 获取已搜索内容
        searched_content = ""
        if request.session_id:
            try:
                from llm.search_cache_manager import get_session_searched_content
                searched_content = get_session_searched_content(request.session_id)
            except Exception as e:
                logging.warning(f"[搜索优化] 获取已搜索内容失败: {e}")
        
        analysis = analyze_turn(
            state_summary=context_summary,
            question=user_query,
            round_index=round_index,
            searched_content=searched_content
        )

        # 7) 生成：分析→（可选RAG）→生成
        # 构造用户信息字典
        user_info = {
            "name": u.name,
            "birthday": u.birthday,
            "heart": u.heart,
            "is_member": u.is_member
        } if u else {}
        
        # 获取当前时间（包含周几）
        now = datetime.now()
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = weekdays[now.weekday()]
        current_time = now.strftime(f"%Y年%m月%d日 {weekday} %H:%M")
        
        answer = chat_once(analysis, context_summary, user_query, current_time=current_time, user_id=user_id, user_info=user_info, session_id=request.session_id)

        # 8) 写入历史
        state.update_message("user", user_query)
        state.update_message("assistant", answer)

        # 9) 返回当前heart
        db: Session = SessionLocal()
        try:
            cur = db.query(User).filter(User.id == user_id).first()
            current_heart = cur.heart if cur else 0
        except Exception as e:
            logging.error(f"❌ 获取用户heart值失败: {e}")
            current_heart = 0
        finally:
            db.close()

        # 调试输出
        try:
            logging.info(
                f"[ANALYSIS] stage={analysis.get('stage')} intent={analysis.get('intent')} "
                f"guidance_type={analysis.get('guidance_type', 'affirmative')} "
                f"pace={analysis.get('pace')} reply_length={analysis.get('reply_length')}")
        except Exception:
            pass

        return {"response": {"answer": answer, "references": [], "user_heart": current_heart}}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.exception("[❌ ERROR] 聊天接口处理失败（完整堆栈）：")
        return {"response": {"answer": "抱歉，系统暂时无法处理您的请求，请稍后再试。", "references": []}}

# ==================== 日记生成 ====================
@app.post("/journal/generate")
def generate_journal(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 生成日记：user={user_id}")
        # 扣heart
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            if user.heart < 4:
                raise HTTPException(status_code=403, detail="心数不足，无法生成日记，请等待明天重置或充值")
            user.heart -= 4
            db.commit(); db.refresh(user)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 更新heart失败: {e}")
            raise HTTPException(status_code=500, detail="系统错误，请稍后再试")
        finally:
            db.close()

        # 构造历史
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)

        from prompts.journal_prompts import get_journal_generation_prompt
        user_emotion = request.emotion or "平和"
        journal_system_prompt = get_journal_generation_prompt(emotion=user_emotion, chat_history=prompt)

        from llm.llm_factory import chat_with_qwen_llm
        journal_result = chat_with_qwen_llm(journal_system_prompt)
        journal_text = journal_result.get("answer", "今天的心情有点复杂，暂时说不清楚。")

        # 入库
        db: Session = SessionLocal()
        try:
            try:
                messages_json = json.dumps([{"role": m.role, "content": m.content} for m in request.messages], ensure_ascii=False)
            except Exception as je:
                logging.warning(f"⚠️ 消息JSON化失败：{je}，使用兜底格式")
                messages_json = json.dumps([{"role": getattr(m, "role", "unknown"), "content": getattr(m, "content", str(m))} for m in request.messages], ensure_ascii=False)

            journal_entry = Journal(
                user_id=user_id,
                content=journal_text,
                messages=messages_json,
                session_id=request.session_id,
                emotion=request.emotion,
            )
            db.add(journal_entry); db.commit(); db.refresh(journal_entry)
            logging.info(f"✅ 日记已保存 ID={journal_entry.id}")
            
            # 同步生成记忆点
            try:
                from memory import generate_memory_point_for_journal
                success = generate_memory_point_for_journal(journal_entry.id)
                if success:
                    logging.info(f"✅ 日记 {journal_entry.id} 记忆点生成成功")
                else:
                    logging.warning(f"⚠️ 日记 {journal_entry.id} 记忆点生成失败")
            except Exception as memory_e:
                logging.warning(f"⚠️ 记忆点生成失败: {memory_e}")
                
        except Exception as e:
            logging.error(f"❌ 保存日记失败：{e}")
            db.rollback(); raise
        finally:
            db.close()

        return {
            "journal_id": journal_entry.id,
            "content": journal_text,
            "emotion": request.emotion,
            "status": "success",
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 生成日记失败: {e}")
        return {
            "journal_id": None,
            "content": "",
            "emotion": request.emotion if hasattr(request, "emotion") else None,
            "status": "error",
        }

# ==================== 手动日记 ====================
@app.post("/journal/create")
def create_manual_journal(request: ManualJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 手动日记：user={user_id}")

        db: Session = SessionLocal()
        try:
            journal_entry = Journal(
                user_id=user_id,
                content=request.content,
                messages="[]",
                session_id="manual",
                emotion=request.emotion,
            )
            db.add(journal_entry); db.commit(); db.refresh(journal_entry)
            logging.info(f"✅ 手动日记已保存 ID={journal_entry.id}")
            
            # 同步生成记忆点
            try:
                from memory import generate_memory_point_for_journal
                success = generate_memory_point_for_journal(journal_entry.id)
                if success:
                    logging.info(f"✅ 手动日记 {journal_entry.id} 记忆点生成成功")
                else:
                    logging.warning(f"⚠️ 手动日记 {journal_entry.id} 记忆点生成失败")
            except Exception as memory_e:
                logging.warning(f"⚠️ 记忆点生成失败: {memory_e}")
                
        except Exception as e:
            logging.error(f"❌ 保存手动日记失败：{e}")
            db.rollback(); raise
        finally:
            db.close()

        return {
            "journal_id": journal_entry.id,
            "content": request.content,
            "emotion": request.emotion,
            "status": "success",
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 手动日记创建失败: {e}")
        return {
            "journal_id": None,
            "content": request.content if hasattr(request, "content") else "",
            "emotion": request.emotion if hasattr(request, "emotion") else "",
            "status": "error",
        }

# ==================== 日记管理 ====================
@app.get("/journal/list")
def get_user_journals(user_id: int = Depends(get_current_user), limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        journals = db.query(Journal).filter(Journal.user_id == user_id).order_by(
            Journal.created_at.desc()
        ).offset(offset).limit(limit).all()

        out = []
        for j in journals:
            try:
                messages = json.loads(j.messages) if j.messages else []
            except json.JSONDecodeError:
                messages = []
            out.append({
                "id": j.id, "content": j.content,
                "messages": messages, "session_id": j.session_id, "emotion": j.emotion,
                "memory_point": j.memory_point,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            })

        total = db.query(Journal).filter(Journal.user_id == user_id).count()
        db.close()
        return {"status": "success", "journals": out, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取日记列表失败: {e}")
        return {"status": "error", "journals": [], "total": 0, "message": "获取日记列表失败"}

@app.get("/journal/{journal_id}")
def get_journal_detail(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        j = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not j:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")

        try:
            messages = json.loads(j.messages) if j.messages else []
        except json.JSONDecodeError:
            messages = []

        data = {
            "id": j.id, "content": j.content,
            "messages": messages, "session_id": j.session_id, "emotion": j.emotion,
            "memory_point": j.memory_point,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
        }
        db.close()
        return {"status": "success", "journal": data}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取日记详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取日记详情失败")

@app.put("/journal/{journal_id}")
def update_journal(journal_id: int, request: UpdateJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 更新日记：user={user_id}, journal={journal_id}")
        db: Session = SessionLocal()
        j = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not j:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")

        updated_fields = []
        if request.content is not None:
            j.content = request.content
            updated_fields.append("content")

        if request.emotion is not None:
            j.emotion = request.emotion
            updated_fields.append("emotion")

        from datetime import timezone, timedelta as _td
        j.updated_at = datetime.now(timezone(_td(hours=8)))

        db.commit(); db.refresh(j); db.close()
        logging.info(f"✅ 日记更新成功，字段: {updated_fields}")

        return {
            "status": "success",
            "journal_id": j.id,
            "content": j.content,
            "emotion": j.emotion,
            "updated_fields": updated_fields,
            "message": "日记更新成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 更新日记失败: {e}")
        return {"status": "error", "message": "更新日记失败"}

@app.delete("/journal/{journal_id}")
def delete_journal(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        j = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not j:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        db.delete(j); db.commit(); db.close()
        return {"status": "success", "message": "日记删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 删除日记失败: {e}")
        raise HTTPException(status_code=500, detail="删除日记失败")