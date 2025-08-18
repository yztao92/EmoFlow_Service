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

# 导入项目内部模块
from prompts.prompt_flow_controller import chat_once  # 新编排：分析→检索→生成
from prompts.chat_analysis import analyze_turn        # 新增：规则机驱动的分析
from dialogue.state_tracker import StateTracker       # 对话状态跟踪器
from database_models import init_db, SessionLocal, User, Journal  # 数据库模型

from dotenv import load_dotenv
load_dotenv()  # 加载 .env 环境变量文件

# ==================== JWT 认证配置 ====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-fallback-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# ==================== Apple 登录配置 ====================
APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_CLIENT_ID = "Nick-Studio.EmoFlow"
apple_keys = []

# ==================== 日志配置 ====================
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ==================== 环境变量检查 ====================
required_env_vars = ["QIANWEN_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")

# ==================== FastAPI 应用初始化 ====================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请限定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==================== 全局状态管理 ====================
session_states: Dict[str, StateTracker] = {}
scheduler = BackgroundScheduler()

# ==================== 应用启动事件 ====================
@app.on_event("startup")
def on_startup():
    init_db()
    global apple_keys
    apple_keys = requests.get(APPLE_PUBLIC_KEYS_URL).json()["keys"]

    # 初始化 embedding（非必须）
    try:
        from llm.qwen_embedding_factory import get_qwen_embedding_model
        _ = get_qwen_embedding_model()
    except Exception as e:
        logging.warning(f"⚠️ Embedding模型初始化失败: {e}")
        logging.warning("⚠️ 知识检索功能可能无法正常使用")

    start_heart_reset_scheduler()

# ==================== 定时任务管理 ====================
def reset_all_users_heart():
    try:
        logging.info("🕛 开始执行定时任务：重置所有用户的heart值")
        db: Session = SessionLocal()
        try:
            total_users = db.query(User).count()
            db.query(User).update({"heart": 100})
            db.commit()
            logging.info(f"✅ 定时任务执行成功：已重置 {total_users} 个用户的heart值为100")
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 定时任务执行失败：{e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logging.error(f"❌ 定时任务执行异常：{e}")

def start_heart_reset_scheduler():
    try:
        scheduler.add_job(
            func=reset_all_users_heart,
            trigger=CronTrigger(hour=0, minute=0),
            id="heart_reset_job",
            name="每日重置用户heart值",
            replace_existing=True
        )
        scheduler.start()
        logging.info("✅ Heart重置定时任务已启动：每天凌晨00:00执行")
    except Exception as e:
        logging.error(f"❌ 启动定时任务失败：{e}")

@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()
        logging.info("✅ 定时任务调度器已关闭")

# ==================== 基础路由 ====================
@app.get("/")
def read_root():
    return {"message": "EmoFlow 服务运行中"}

# ==================== Apple 登录认证模块 ====================
class AppleLoginRequest(BaseModel):
    identity_token: str
    full_name: Optional[str] = None
    email: Optional[str] = None

@app.post("/auth/apple")
def login_with_apple(req: AppleLoginRequest):
    try:
        logging.info(f"🔍 收到 Apple 登录请求: identity_token长度={len(req.identity_token)}, full_name='{req.full_name}', email='{req.email}'")
        import base64
        try:
            token_bytes = base64.b64decode(req.identity_token)
            token = token_bytes.decode('utf-8')
        except:
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
        email = req.email or decoded.get("email")
        name = req.full_name

        db: Session = SessionLocal()
        user = db.query(User).filter(User.apple_user_id == apple_user_id).first()
        if not user:
            user = User(apple_user_id=apple_user_id, email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            updated = False
            if req.email and req.email != user.email:
                user.email = req.email; updated = True
            if req.full_name and req.full_name != user.name:
                user.name = req.full_name; updated = True
            if updated:
                db.commit(); db.refresh(user)

        token_data = {
            "sub": str(user.id),
            "apple_user_id": user.apple_user_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
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

# ==================== 用户资料管理模块 ====================
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

@app.put("/user/profile")
def update_user_profile(request: UpdateProfileRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"🔧 收到用户资料更新请求: user_id={user_id}, name='{request.name}', email='{request.email}'")
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        updated = False
        if request.name is not None and request.name != user.name:
            user.name = request.name; updated = True
        if request.email is not None and request.email != user.email:
            user.email = request.email; updated = True
        if updated:
            db.commit(); db.refresh(user); logging.info(f"✅ 用户资料更新成功: user_id={user_id}")

        return {"status": "ok", "message": "用户资料更新成功" if updated else "用户资料无变化",
                "user": {"id": user.id, "name": user.name, "email": user.email}}
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
                "user": {"id": user.id, "name": user.name, "email": user.email, "heart": user.heart}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取用户资料失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")

# ==================== 用户心数管理模块 ====================
class UpdateHeartRequest(BaseModel):
    heart: int

@app.put("/user/heart")
def update_user_heart(request: UpdateHeartRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"🔧 收到用户心数更新请求: user_id={user_id}, heart={request.heart}")
        if request.heart < 0:
            raise HTTPException(status_code=400, detail="心数值不能为负数")
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.heart = request.heart
        db.commit(); db.refresh(user)
        logging.info(f"✅ 用户心数更新成功: user_id={user_id}, heart={user.heart}")
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

# ==================== 聊天模块 ====================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]
    emotion: Optional[str] = None  # 暂未使用

class ManualJournalRequest(BaseModel):
    title: str
    content: str
    emotion: Optional[str] = None

class UpdateJournalRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    emotion: Optional[str] = None

@app.post("/chat")
def chat_with_user(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    logging.info(f"收到 /chat 请求，用户ID: {user_id}")
    try:
        # Heart 扣减
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

        # 会话状态
        session_key = f"user_{user_id}_{request.session_id}"
        state = session_states.setdefault(session_key, StateTracker())
        if not hasattr(state, "last_stage"):
            state.last_stage = None

        # 提取用户最新消息
        user_messages = [m for m in request.messages if m.role == "user"]
        user_query = user_messages[-1].content if user_messages else ""

        # 打印输入
        db: Session = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        db.close()
        if user_messages:
            logging.info(f"[CHAT] 用户ID: {user_id}，昵称: {u.name if u else ''}，输入: {user_query}")
        else:
            logging.info(f"[CHAT] 用户ID: {user_id}，昵称: {u.name if u else ''}，无输入")

        # 轮次与上下文
        round_index = len(user_messages)
        context_summary = state.summary(last_n=10)

        # 启发式信号
        explicit_close_phrases = ("先这样", "改天聊", "下次再聊", "谢谢就到这", "收工", "结束", "先到这")
        new_topic_phrases      = ("另外", "换个话题", "说个别的", "还有一件事", "顺便", "对了")
        target_resolved_phrases= ("明白了", "搞定了", "已经解决", "了解了", "知道了", "可以了")
        uq = user_query or ""
        explicit_close  = any(p in uq for p in explicit_close_phrases)
        new_topic       = any(p in uq for p in new_topic_phrases)
        target_resolved = any(p in uq for p in target_resolved_phrases)

        # 分析：LLM 语义理解 + 规则机派生
        analysis = analyze_turn(
            round_index=round_index,
            state_summary=context_summary,
            question=user_query,
            last_stage=getattr(state, "last_stage", None),
            explicit_close=explicit_close,
            new_topic=new_topic,
            target_resolved=target_resolved,
        )

        # 生成：按分析结果→（可选检索）→生成
        gen_result = chat_once(analysis, context_summary, user_query)
        if isinstance(gen_result, dict):
            answer = gen_result.get("answer") or gen_result.get("response") or ""
        else:
            answer = gen_result or ""

        # 写入对话历史
        state.update_message("user", user_query)
        state.update_message("assistant", answer)
        try:
            state.last_stage = analysis.get("stage", getattr(state, "last_stage", None))
        except Exception:
            pass

        # 更新 heart 显示
        db: Session = SessionLocal()
        try:
            current_user = db.query(User).filter(User.id == user_id).first()
            current_heart = current_user.heart if current_user else 0
        except Exception as e:
            logging.error(f"❌ 获取用户heart值失败: {e}")
            current_heart = 0
        finally:
            db.close()

        # 去除首尾引号（保险）
        if isinstance(answer, str) and len(answer) >= 2 and answer[0] == answer[-1] and answer[0] in ['"', '“', '”', "'"]:
            answer = answer[1:-1]

        # 调试日志
        try:
            logging.info(f"[ANALYSIS] stage={analysis.get('stage')} intent={analysis.get('intent')} "
                         f"ask_slot={analysis.get('ask_slot')} pace={analysis.get('pace')} "
                         f"reply_length={analysis.get('reply_length')}")
        except Exception:
            pass

        return {
            "response": {
                "answer": answer,
                "references": [],
                "user_heart": current_heart
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 聊天接口处理失败: {e}")
        return {
            "response": {
                "answer": "抱歉，系统暂时无法处理您的请求，请稍后再试。",
                "references": []
            }
        }

# ==================== 日记生成模块 ====================
@app.post("/journal/generate")
def generate_journal(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 收到生成心情日记请求：用户ID={user_id}, 请求={request.json()}")
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            if user.heart < 4:
                raise HTTPException(status_code=403, detail="心数不足，无法生成日记，请等待明天重置或充值")
            user.heart -= 4
            db.commit(); db.refresh(user)
            logging.info(f"💔 用户 {user.name} (ID: {user_id}) 生成日记消耗4个heart，剩余: {user.heart}")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 更新用户heart值失败: {e}")
            raise HTTPException(status_code=500, detail="系统错误，请稍后再试")
        finally:
            db.close()

        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        from prompts.journal_prompts import get_journal_generation_prompt
        user_emotion = request.emotion or "平和"
        journal_system_prompt = get_journal_generation_prompt(emotion=user_emotion, chat_history=prompt)

        from llm.llm_factory import chat_with_qwen_llm
        journal_result = chat_with_qwen_llm(journal_system_prompt)
        journal_text = journal_result.get("answer", "今天的心情有点复杂，暂时说不清楚。")

        def text_to_smart_html(text):
            paragraphs = text.split('\n\n')
            html_parts = []
            for p in paragraphs:
                p = p.strip()
                if p:
                    lines = p.split('\n')
                    if any(line.strip().startswith(('•', '-', '*')) for line in lines):
                        for line in lines:
                            line = line.strip()
                            if line:
                                if line.startswith(('•', '-', '*')):
                                    html_parts.append(f"<li>{line[1:].strip()}</li>")
                                else:
                                    html_parts.append(f"<p>{line}</p>")
                    elif p.startswith(('1.', '2.', '3.', '4.', '5.')) or '：' in p[:10]:
                        html_parts.append(f"<h3>{p}</h3>")
                    else:
                        html_parts.append(f"<p>{p}</p>")
            body_content = '\n'.join(html_parts)
            complete_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 20px;
            font-weight: 300;
            line-height: 1.3;
            margin: 0;
            padding: 0;
            text-align: center;
        }}
        .text-left {{ text-align: left; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        strong, b {{ font-weight: 600; }}
        em, i {{ font-style: italic; }}
        p {{ margin: 0; padding: 0; }}
        br {{ line-height: 1.3; }}
    </style>
</head>
<body>
    {body_content}
</body>
</html>'''
            return complete_html

        journal_html = text_to_smart_html(journal_text)

        title_system_prompt = f"""请根据以下心情日记内容，生成一个简洁、有情感、不超过10个字的标题。标题要体现日记的主要情感和主题：\n-----------\n{journal_text}\n-----------"""
        title_result = chat_with_qwen_llm(title_system_prompt)
        title = title_result.get("answer", "今日心情")
        title = title.strip().replace('"', '').replace('"', '')
        if len(title) > 10:
            title = title[:10] + "..."

        db: Session = SessionLocal()
        try:
            try:
                messages_json = json.dumps([{"role": m.role, "content": m.content} for m in request.messages], ensure_ascii=False)
            except Exception as json_error:
                logging.warning(f"⚠️ 消息格式转换失败，使用原始格式: {json_error}")
                messages_json = json.dumps([{"role": getattr(m, 'role', 'unknown'), "content": getattr(m, 'content', str(m))} for m in request.messages], ensure_ascii=False)

            from utils.html_processor import process_journal_content
            processed_content = process_journal_content(journal_html)

            journal_entry = Journal(
                user_id=user_id,
                title=title,
                content=journal_text,
                content_html=processed_content['content_html'],
                content_plain=processed_content['content_plain'],
                content_format=processed_content['content_format'],
                is_safe=processed_content['is_safe'],
                messages=messages_json,
                session_id=request.session_id,
                emotion=request.emotion
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

        db: Session = SessionLocal()
        try:
            current_user = db.query(User).filter(User.id == user_id).first()
            current_heart = current_user.heart if current_user else 0
        except Exception as e:
            logging.error(f"❌ 获取用户heart值失败: {e}")
            current_heart = 0
        finally:
            db.close()

        return {
            "journal": journal_text,
            "content_html": processed_content['content_html'],
            "content_plain": processed_content['content_plain'],
            "content_format": processed_content['content_format'],
            "is_safe": processed_content['is_safe'],
            "title": title,
            "journal_id": journal_entry.id if 'journal_entry' in locals() else None,
            "emotion": request.emotion,
            "status": "success",
            "user_heart": current_heart
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 心情日记生成失败: {e}")
        return {
            "journal": "生成失败",
            "title": "今日心情",
            "journal_id": None,
            "emotion": request.emotion if hasattr(request, 'emotion') else None,
            "status": "error"
        }

# ==================== 手动创建日记模块 ====================
@app.post("/journal/create")
def create_manual_journal(request: ManualJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 收到手动创建日记请求：用户ID={user_id}, 标题={request.title}")
        title = request.title.strip().replace('"', '').replace('"', '')
        if len(title) > 50:
            title = title[:50] + "..."

        from utils.html_processor import process_journal_content
        processed_content = process_journal_content(request.content)

        db: Session = SessionLocal()
        try:
            journal_entry = Journal(
                user_id=user_id,
                title=title,
                content=processed_content['content'],
                content_html=processed_content['content_html'],
                content_plain=processed_content['content_plain'],
                content_format=processed_content['content_format'],
                is_safe=processed_content['is_safe'],
                messages="[]",
                session_id="manual",
                emotion=request.emotion
            )
            db.add(journal_entry)
            db.commit()
            db.refresh(journal_entry)
            logging.info(f"✅ 手动日记已保存到数据库，ID: {journal_entry.id}")
        except Exception as db_error:
            logging.error(f"❌ 保存手动日记到数据库失败: {db_error}")
            db.rollback()
            raise
        finally:
            db.close()

        return {
            "journal_id": journal_entry.id,
            "title": title,
            "content": processed_content['content'],
            "content_html": processed_content['content_html'],
            "content_plain": processed_content['content_plain'],
            "content_format": processed_content['content_format'],
            "is_safe": processed_content['is_safe'],
            "emotion": request.emotion,
            "status": "success"
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 手动日记创建失败: {e}")
        return {
            "journal_id": None,
            "title": request.title if hasattr(request, 'title') else "",
            "content": request.content if hasattr(request, 'content') else "",
            "content_html": "",
            "content_plain": "",
            "content_format": "html",
            "is_safe": False,
            "emotion": request.emotion if hasattr(request, 'emotion') else None,
            "status": "error"
        }

# ==================== 日记管理模块 ====================
@app.get("/journal/list")
def get_user_journals(user_id: int = Depends(get_current_user), limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        journals = db.query(Journal).filter(Journal.user_id == user_id).order_by(
            Journal.created_at.desc()
        ).offset(offset).limit(limit).all()

        journal_list = []
        for journal in journals:
            messages = []
            if journal.messages:
                try:
                    messages = json.loads(journal.messages)
                except json.JSONDecodeError:
                    messages = []
            journal_list.append({
                "id": journal.id,
                "title": journal.title,
                "content": journal.content,
                "content_html": journal.content_html,
                "content_plain": journal.content_plain,
                "content_format": journal.content_format,
                "is_safe": journal.is_safe,
                "messages": messages,
                "session_id": journal.session_id,
                "emotion": journal.emotion,
                "created_at": journal.created_at.isoformat() if journal.created_at else None,
                "updated_at": journal.updated_at.isoformat() if journal.updated_at else None
            })

        total_count = db.query(Journal).filter(Journal.user_id == user_id).count()
        db.close()

        return {"status": "success", "journals": journal_list, "total": total_count, "limit": limit, "offset": offset}
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取用户日记列表失败: {e}")
        return {"status": "error", "journals": [], "total": 0, "message": "获取日记列表失败"}

@app.get("/journal/{journal_id}")
def get_journal_detail(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        db: Session = SessionLocal()
        journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")

        messages = []
        if journal.messages:
            try:
                messages = json.loads(journal.messages)
            except json.JSONDecodeError:
                messages = []

        journal_data = {
            "id": journal.id,
            "title": journal.title,
            "content": journal.content,
            "content_html": journal.content_html,
            "content_plain": journal.content_plain,
            "content_format": journal.content_format,
            "is_safe": journal.is_safe,
            "messages": messages,
            "session_id": journal.session_id,
            "emotion": journal.emotion,
            "created_at": journal.created_at.isoformat() if journal.created_at else None,
            "updated_at": journal.updated_at.isoformat() if journal.updated_at else None
        }
        db.close()
        return {"status": "success", "journal": journal_data}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取日记详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取日记详情失败")

@app.put("/journal/{journal_id}")
def update_journal(journal_id: int, request: UpdateJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 收到更新日记请求：用户ID={user_id}, 日记ID={journal_id}")
        db: Session = SessionLocal()
        journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")

        updated_fields = []
        if request.title is not None:
            title = request.title.strip().replace('"', '').replace('"', '')
            if len(title) > 50:
                title = title[:50] + "..."
            journal.title = title; updated_fields.append("title")

        if request.content is not None:
            from utils.html_processor import process_journal_content
            processed_content = process_journal_content(request.content)
            journal.content = processed_content['content']
            journal.content_html = processed_content['content_html']
            journal.content_plain = processed_content['content_plain']
            journal.content_format = processed_content['content_format']
            journal.is_safe = processed_content['is_safe']
            updated_fields.append("content")

        if request.emotion is not None:
            journal.emotion = request.emotion; updated_fields.append("emotion")

        from datetime import timezone, timedelta as _td
        journal.updated_at = datetime.now(timezone(_td(hours=8)))
        db.commit(); db.refresh(journal); db.close()

        logging.info(f"✅ 日记更新成功，更新字段: {updated_fields}")
        return {
            "status": "success",
            "journal_id": journal.id,
            "title": journal.title,
            "content": journal.content,
            "content_html": journal.content_html,
            "content_plain": journal.content_plain,
            "content_format": journal.content_format,
            "is_safe": journal.is_safe,
            "emotion": journal.emotion,
            "updated_fields": updated_fields,
            "message": "日记更新成功"
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
        journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        db.delete(journal); db.commit(); db.close()
        return {"status": "success", "message": "日记删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 删除日记失败: {e}")
        raise HTTPException(status_code=500, detail="删除日记失败")