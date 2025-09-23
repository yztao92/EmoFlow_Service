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
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# —— 新编排：分析→（可选检索）→生成
from prompts.prompt_flow_controller import chat_once
from prompts.chat_analysis import analyze_turn
from dialogue.state_tracker import StateTracker
from dialogue.session_manager import session_manager
from services.image_service import image_service
from database_models import init_db, SessionLocal, User, Journal, ChatSession, Image
from database_models.schemas import UpdateProfileRequest, SubscriptionVerifyRequest, SubscriptionStatusResponse, AppleWebhookNotification, TestLoginRequest
from subscription.apple_subscription import (
    verify_receipt_with_apple, parse_subscription_info, update_user_subscription, 
    get_user_subscription_status, handle_apple_webhook_notification, AppleSubscriptionError
)

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
    start_cache_cleanup_scheduler()
    start_image_cleanup_scheduler()

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

def clear_search_cache():
    """清空搜索缓存目录"""
    try:
        import os
        import shutil
        cache_dir = "search_cache"
        
        if os.path.exists(cache_dir):
            # 删除目录下的所有文件
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            logging.info("🧹 搜索缓存清理完成：已清空所有缓存文件")
        else:
            logging.info("🧹 搜索缓存目录不存在，无需清理")
            
    except Exception as e:
        logging.error(f"❌ 缓存清理失败：{e}")

def start_cache_cleanup_scheduler():
    """启动缓存清理定时任务"""
    try:
        scheduler.add_job(
            func=clear_search_cache,
            trigger=CronTrigger(hour=0, minute=0),
            id="cache_cleanup_job",
            name="每日清理搜索缓存",
            replace_existing=True,
        )
        logging.info("✅ 缓存清理任务已启动：每天00:00执行")
    except Exception as e:
        logging.error(f"❌ 启动缓存清理任务失败：{e}")

def cleanup_unreferenced_images():
    """清理未被日记引用的图片文件"""
    try:
        logging.info("🕛 开始执行：清理未被日记引用的图片文件")
        
        # 获取被日记引用的图片文件名
        db: Session = SessionLocal()
        try:
            # 查询所有日记中的图片ID
            journals = db.query(Journal).filter(Journal.images.isnot(None)).all()
            
            referenced_image_ids = set()
            for journal in journals:
                if journal.images:
                    # 解析逗号分隔的图片ID
                    image_ids = journal.images.split(",")
                    for image_id in image_ids:
                        try:
                            referenced_image_ids.add(int(image_id.strip()))
                        except ValueError:
                            logging.warning(f"⚠️ 无效的图片ID: {image_id}")
            
            # 根据图片ID查询文件名
            if referenced_image_ids:
                images = db.query(Image.filename).filter(Image.id.in_(referenced_image_ids)).all()
                referenced_filenames = {img.filename for img in images}
                logging.info(f"📊 找到 {len(referenced_filenames)} 个被引用的图片文件名")
            else:
                referenced_filenames = set()
                logging.info("📊 没有图片被日记引用")
            
        finally:
            db.close()
        
        # 获取文件系统中的所有图片文件名
        upload_dir = "uploads/images"
        if not os.path.exists(upload_dir):
            logging.warning(f"⚠️ 上传目录不存在: {upload_dir}")
            return
        
        filesystem_filenames = set()
        for user_dir in os.listdir(upload_dir):
            user_path = os.path.join(upload_dir, user_dir)
            if os.path.isdir(user_path):
                for filename in os.listdir(user_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        filesystem_filenames.add(filename)
        
        # 找出未被引用的图片文件
        unreferenced_filenames = filesystem_filenames - referenced_filenames
        
        logging.info(f"📊 统计结果:")
        logging.info(f"   - 文件系统图片数: {len(filesystem_filenames)}")
        logging.info(f"   - 被日记引用数: {len(referenced_filenames)}")
        logging.info(f"   - 未被引用数: {len(unreferenced_filenames)}")
        
        if not unreferenced_filenames:
            logging.info("✅ 所有图片都被日记引用，无需清理")
            return
        
        # 计算可释放的存储空间
        total_size = 0
        for user_dir in os.listdir(upload_dir):
            user_path = os.path.join(upload_dir, user_dir)
            if os.path.isdir(user_path):
                for filename in unreferenced_filenames:
                    file_path = os.path.join(user_path, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        
        logging.info(f"💾 可释放存储空间: {total_size / 1024 / 1024:.2f} MB")
        
        # 删除未被引用的图片文件
        deleted_count = 0
        failed_count = 0
        freed_space = 0
        
        for filename in sorted(unreferenced_filenames):
            # 在所有用户目录中查找并删除文件
            for user_dir in os.listdir(upload_dir):
                user_path = os.path.join(upload_dir, user_dir)
                if os.path.isdir(user_path):
                    file_path = os.path.join(user_path, filename)
                    if os.path.exists(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_count += 1
                            freed_space += file_size
                            logging.info(f"🗑️ 删除文件: {filename} ({file_size} bytes)")
                            break  # 找到并删除后跳出循环
                        except Exception as e:
                            logging.error(f"❌ 删除失败 {filename}: {e}")
                            failed_count += 1
        
        logging.info(f"✅ 图片清理完成: 成功 {deleted_count} 个，失败 {failed_count} 个")
        logging.info(f"💾 释放空间: {freed_space / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        logging.error(f"❌ 图片清理任务异常：{e}")

def start_image_cleanup_scheduler():
    """启动图片清理定时任务"""
    try:
        scheduler.add_job(
            func=cleanup_unreferenced_images,
            trigger=CronTrigger(hour=3, minute=0),
            id="image_cleanup_job",
            name="每日清理未引用图片",
            replace_existing=True,
        )
        if not scheduler.running:
            scheduler.start()
        logging.info("✅ 图片清理任务已启动：每天03:00执行")
    except Exception as e:
        logging.error(f"❌ 启动图片清理任务失败：{e}")

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

# ==================== 测试登录 ====================
@app.post("/auth/test")
def test_login(request: TestLoginRequest):
    """
    测试登录接口
    专门为Apple测试人员提供的测试账号登录
    """
    try:
        logging.info(f"🧪 测试登录: username={request.username}")
        
        # 验证测试账号
        if request.username != "review@test.com" or request.password != "Review1234!":
            logging.warning(f"❌ 测试登录失败: 无效的测试账号")
            raise HTTPException(status_code=401, detail="无效的测试账号")
        
        # 查找或创建测试用户
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "review@test.com").first()
            
            if not user:
                # 创建测试用户
                user = User(
                    name="Apple Reviewer",
                    email="review@test.com",
                    heart=1000,  # 给测试用户充足的心数
                    subscription_status="inactive",  # 普通会员，无订阅状态
                    subscription_product_id=None,
                    subscription_expires_at=None,
                    auto_renew_status=False,
                    subscription_environment="sandbox"
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logging.info(f"✅ 创建测试用户: user_id={user.id}")
            else:
                # 更新现有测试用户为普通会员状态
                user.subscription_status = "inactive"
                user.subscription_product_id = None
                user.subscription_expires_at = None
                user.auto_renew_status = False
                user.heart = 1000  # 确保有足够的心数
                db.commit()
                db.refresh(user)
                logging.info(f"✅ 更新测试用户为普通会员: user_id={user.id}")
            
            # 生成JWT令牌
            expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
            to_encode = {"sub": str(user.id), "exp": expire}
            jwt_token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            
            logging.info(f"✅ 测试登录成功: user_id={user.id}")
            
            return {
                "status": "success",
                "message": "测试登录成功",
                "jwt": jwt_token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "heart": user.heart,
                    "subscription_status": user.subscription_status,
                    "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                    "is_member": user.subscription_status == "active"
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 测试登录异常: {e}")
        raise HTTPException(status_code=500, detail="测试登录失败，请稍后再试")

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
        logging.info(f"🔧 更新资料: user_id={user_id}, name='{request.name}', email='{request.email}', birthday={request.birthday}")
        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        updated = False
        if request.name is not None and request.name != user.name:
            user.name = request.name; updated = True
        if request.email is not None and request.email != user.email:
            user.email = request.email; updated = True
        if request.birthday is not None and request.birthday != user.birthday:
            user.birthday = request.birthday; updated = True

        if updated:
            db.commit(); db.refresh(user)

        return {"status": "ok",
                "message": "用户资料更新成功" if updated else "用户资料无变化",
                "user": {"id": user.id, "name": user.name, "email": user.email, "heart": user.heart, "birthday": user.birthday, "subscription_status": user.subscription_status, "subscription_expires_at": user.subscription_expires_at}}
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
                "user": {"id": user.id, "name": user.name, "email": user.email, "heart": user.heart, "birthday": user.birthday, "subscription_status": user.subscription_status, "subscription_expires_at": user.subscription_expires_at}}
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
    user_message: str  # 用户最新消息
    emotion: Optional[str] = None  # 该字段不影响分析链路
    has_image: bool = False  # 是否有图片
    image_data: Optional[str] = None  # Base64编码的图片数据（单张）

class GenerateJournalRequest(BaseModel):
    session_id: str
    emotion: Optional[str] = None

class ManualJournalRequest(BaseModel):
    content: str
    emotion: Optional[str] = None
    has_image: bool = False  # 是否有图片
    image_data: Optional[List[str]] = None  # Base64编码的图片数据列表

class UpdateJournalRequest(BaseModel):
    content: Optional[str] = None
    emotion: Optional[str] = None
    has_image: bool = False  # 是否有图片
    # 增量更新图片字段
    keep_image_ids: Optional[List[int]] = None  # 保留的图片ID列表
    add_image_data: Optional[List[str]] = None  # 新增的图片Base64数据列表

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

        # 2) 获取或创建会话状态
        state = session_manager.get_or_create_session(user_id, request.session_id)

        # 3) 处理图片上传（如果有）
        image_analysis = None
        logging.info(f"🔍 检查图片上传: has_image={request.has_image}, image_data长度={len(request.image_data) if request.image_data else 0}")
        
        if request.has_image and request.image_data:
            try:
                logging.info(f"📷 开始处理图片上传...")
                # 解码Base64图片数据
                import base64
                image_data = base64.b64decode(request.image_data.split(',')[1] if ',' in request.image_data else request.image_data)
                logging.info(f"📷 图片数据解码成功，大小: {len(image_data)} bytes")
                
                # 保存并分析图片
                result = image_service.save_image(
                    image_data=image_data,
                    user_id=user_id,
                    session_id=request.session_id,
                    original_filename="uploaded_image.jpg"
                )
                
                if result["success"]:
                    image_analysis = result["analysis"]
                    logging.info(f"✅ 图片分析完成: {image_analysis.get('summary', '')[:50]}...")
                else:
                    logging.error(f"❌ 图片处理失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                logging.error(f"❌ 图片处理异常: {e}")
                import traceback
                traceback.print_exc()
        else:
            logging.info(f"📷 没有图片上传")

        # 4) 构造用户消息
        user_query = request.user_message
        if image_analysis:
            # 将图片分析结果作为用户消息的一部分（用于LLM处理）
            image_summary = f"[图片分析] {image_analysis.get('summary', '用户上传了一张图片')}"
            user_query = f"{user_query}\n\n{image_summary}" if user_query else image_summary

        # 获取用户信息并打印
        db: Session = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        db.close()
        
        logging.info(f"用户昵称: {u.name}")
        logging.info(f"用户输入: {user_query}")
        logging.info("=" * 60)

        # 4) 轮次与摘要
        round_index = state.get_round_count() + 1  # 当前轮次
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
        
        analysis = analyze_turn(
            state_summary=context_summary,
            question=user_query,
            round_index=round_index,
            session_id=request.session_id
        )

        # 7) 生成：分析→（可选RAG）→生成
        # 构造用户信息字典
        user_info = {
            "name": u.name,
            "birthday": u.birthday,
            "heart": u.heart,
            "is_member": u.subscription_status == "active"  # 使用订阅状态判断是否为会员
        } if u else {}
        
        # 获取当前时间（包含周几）
        now = datetime.now()
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = weekdays[now.weekday()]
        current_time = now.strftime(f"%Y年%m月%d日 {weekday} %H:%M")
        
        answer = chat_once(analysis, context_summary, user_query, current_time=current_time, user_id=user_id, user_info=user_info, session_id=request.session_id)

        # 8) 更新会话历史
        # 如果有图片分析结果，将分析结果合并到用户消息中
        if image_analysis:
            # 构造包含图片分析的用户消息
            if request.user_message:
                user_message_with_image = f"{request.user_message}\n\n[上传一张图片]：{image_analysis.get('summary', '用户上传了一张图片')}"
            else:
                user_message_with_image = f"[上传一张图片]：{image_analysis.get('summary', '用户上传了一张图片')}"
            state.update_message("user", user_message_with_image)
        else:
            # 没有图片时，直接保存用户消息
            state.update_message("user", user_query)
        
        # 保存AI回复
        state.update_message("assistant", answer)
        
        # 9) 保存会话状态到数据库
        try:
            session_manager.save_session(user_id, request.session_id, state)
        except Exception as e:
            logging.error(f"❌ 保存会话状态失败: {e}")

        # 10) 返回当前heart
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

# ==================== 图片访问 ====================
def get_current_user_from_auth(authorization: str = Header(..., alias="Authorization")) -> int:
    try:
        # 支持 "Bearer <token>" 格式
        if authorization.startswith("Bearer "):
            token = authorization[7:]  # 移除 "Bearer " 前缀
        else:
            token = authorization
        
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的 Token")

@app.get("/api/images/user_{user_id}/{filename}")
def get_image(user_id: int, filename: str, current_user_id: int = Depends(get_current_user_from_auth)):
    """
    获取用户图片
    """
    try:
        # 验证权限（只能访问自己的图片）
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权限访问该图片")
        
        # 构建图片路径
        image_path = f"uploads/images/user_{user_id}/{filename}"
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 获取文件MIME类型
        import mimetypes
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"  # 默认类型
        
        # 返回图片文件
        from fastapi.responses import FileResponse
        return FileResponse(
            path=image_path,
            media_type=mime_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取图片失败: {e}")
        raise HTTPException(status_code=500, detail="获取图片失败")

# ==================== 日记生成 ====================
@app.post("/journal/generate")
def generate_journal(request: GenerateJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
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

        # 获取会话历史
        state = session_manager.get_or_create_session(user_id, request.session_id)
        context_summary = state.summary(last_n=1000)  # 获取完整对话历史

        # 收集会话中的图片ID
        session_images = []
        try:
            db: Session = SessionLocal()
            images = db.query(Image).filter(
                Image.user_id == user_id,
                Image.session_id == request.session_id
            ).all()
            session_images = [str(img.id) for img in images]
            db.close()
            logging.info(f"📷 会话中的图片ID: {session_images}")
        except Exception as e:
            logging.warning(f"⚠️ 获取会话图片失败: {e}")

        from prompts.journal_prompts import get_journal_generation_prompt
        user_emotion = request.emotion or "平和"
        journal_system_prompt = get_journal_generation_prompt(emotion=user_emotion, chat_history=context_summary)

        from llm.llm_factory import chat_with_qwen_llm
        journal_result = chat_with_qwen_llm(journal_system_prompt)
        journal_text = journal_result.get("answer", "今天的心情有点复杂，暂时说不清楚。")

        # 入库
        db: Session = SessionLocal()
        try:
            journal_entry = Journal(
                user_id=user_id,
                content=journal_text,
                session_id=request.session_id,  # 使用请求中的会话ID
                emotion=request.emotion,
                images=",".join(session_images) if session_images else None,
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

        # 生成图片URL列表
        image_urls = []
        if session_images:
            for image_id in session_images:
                try:
                    db: Session = SessionLocal()
                    image = db.query(Image).filter(Image.id == int(image_id)).first()
                    if image:
                        image_urls.append(f"/api/images/user_{image.user_id}/{image.filename}")
                    db.close()
                except Exception as e:
                    logging.warning(f"⚠️ 获取图片URL失败: {e}")

        return {
            "journal_id": journal_entry.id,
            "content": journal_text,
            "emotion": request.emotion,
            "images": session_images if session_images else [],
            "image_urls": image_urls if image_urls else [],
            "status": "success",
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 生成日记失败: {e}")
        return {
            "journal_id": None,
            "content": "",
            "emotion": request.emotion if hasattr(request, "emotion") else None,
            "images": [],
            "image_urls": [],
            "status": "error",
        }

# ==================== 日记管理 ====================
@app.get("/journal/list")
def get_journal_list(page: int = 1, limit: int = 10, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取用户日记列表
    """
    try:
        db: Session = SessionLocal()
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 获取日记总数
        total = db.query(Journal).filter(Journal.user_id == user_id).count()
        
        # 获取日记列表
        journals = db.query(Journal).filter(Journal.user_id == user_id)\
            .order_by(Journal.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        # 处理每篇日记的图片信息
        journal_list = []
        for journal in journals:
            image_urls = []
            if journal.images:
                image_ids = journal.images.split(",")
                for image_id in image_ids:
                    try:
                        image = db.query(Image).filter(Image.id == int(image_id)).first()
                        if image:
                            image_urls.append(f"/api/images/user_{image.user_id}/{image.filename}")
                    except Exception as e:
                        logging.warning(f"⚠️ 获取图片URL失败: {e}")
            
            journal_list.append({
                "journal_id": journal.id,
                "content": journal.content,
                "emotion": journal.emotion,
                "images": journal.images.split(",") if journal.images else [],
                "image_urls": image_urls if image_urls else [],
                "created_at": journal.created_at.isoformat()
            })
        
        db.close()
        
        return {
            "status": "success",
            "data": {
                "journals": journal_list,
                "total": total,
                "page": page,
                "limit": limit
            }
        }
        
    except Exception as e:
        logging.error(f"❌ 获取日记列表失败: {e}")
        return {
            "status": "error",
            "message": "获取日记列表失败"
        }

@app.get("/journal/{journal_id}")
def get_journal_detail(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取单篇日记详情
    """
    try:
        db: Session = SessionLocal()
        
        # 获取日记
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        # 处理图片信息
        image_urls = []
        if journal.images:
            image_ids = journal.images.split(",")
            for image_id in image_ids:
                try:
                    image = db.query(Image).filter(Image.id == int(image_id)).first()
                    if image:
                        image_urls.append(f"/api/images/user_{image.user_id}/{image.filename}")
                except Exception as e:
                    logging.warning(f"⚠️ 获取图片URL失败: {e}")
        
        db.close()
        
        return {
            "status": "success",
            "data": {
                "journal_id": journal.id,
                "content": journal.content,
                "emotion": journal.emotion,
                "images": journal.images.split(",") if journal.images else [],
                "image_urls": image_urls if image_urls else [],
                "created_at": journal.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取日记详情失败: {e}")
        return {
            "status": "error",
            "message": "获取日记详情失败"
        }

@app.delete("/journal/{journal_id}")
def delete_journal(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    删除日记
    """
    try:
        db: Session = SessionLocal()
        
        # 获取日记
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        # 删除关联的图片文件
        if journal.images:
            image_ids = journal.images.split(",")
            for image_id in image_ids:
                try:
                    image = db.query(Image).filter(Image.id == int(image_id)).first()
                    if image:
                        # 删除图片文件
                        import os
                        if os.path.exists(image.file_path):
                            os.remove(image.file_path)
                        # 删除图片记录
                        db.delete(image)
                except Exception as e:
                    logging.warning(f"⚠️ 删除图片失败: {e}")
        
        # 删除日记记录
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
        logging.error(f"❌ 删除日记失败: {e}")
        return {
            "status": "error",
            "message": "删除日记失败"
        }

# ==================== 手动日记 ====================
@app.post("/journal/create")
def create_manual_journal(request: ManualJournalRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        logging.info(f"\n📝 手动日记：user={user_id}")
        
        # 处理图片上传（如果有）
        session_images = []
        if request.has_image and request.image_data:
            try:
                logging.info(f"📷 开始处理手动日记图片上传，共{len(request.image_data)}张图片...")
                
                for i, image_data_b64 in enumerate(request.image_data):
                    try:
                        # 解码Base64图片数据
                        import base64
                        image_data = base64.b64decode(image_data_b64.split(',')[1] if ',' in image_data_b64 else image_data_b64)
                        logging.info(f"📷 图片{i+1}数据解码成功，大小: {len(image_data)} bytes")
                        
                        # 保存并分析图片
                        result = image_service.save_image(
                            image_data=image_data,
                            user_id=user_id,
                            session_id="manual",  # 手动日记使用固定的session_id
                            original_filename=f"manual_journal_image_{i+1}.jpg"
                        )
                        
                        if result["success"]:
                            session_images.append(str(result["image_id"]))
                            logging.info(f"✅ 手动日记图片{i+1}保存成功: {result['image_id']}")
                        else:
                            logging.error(f"❌ 手动日记图片{i+1}处理失败: {result.get('error', '未知错误')}")
                            
                    except Exception as e:
                        logging.error(f"❌ 手动日记图片{i+1}处理异常: {e}")
                        import traceback
                        traceback.print_exc()
                        
            except Exception as e:
                logging.error(f"❌ 手动日记图片处理异常: {e}")
                import traceback
                traceback.print_exc()

        db: Session = SessionLocal()
        try:
            journal_entry = Journal(
                user_id=user_id,
                content=request.content,
                session_id="manual",
                emotion=request.emotion,
                images=",".join(session_images) if session_images else None,
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

        # 生成图片URL列表
        image_urls = []
        if session_images:
            for image_id in session_images:
                try:
                    db: Session = SessionLocal()
                    image = db.query(Image).filter(Image.id == int(image_id)).first()
                    if image:
                        image_urls.append(f"/api/images/user_{image.user_id}/{image.filename}")
                    db.close()
                except Exception as e:
                    logging.warning(f"⚠️ 获取图片URL失败: {e}")

        return {
            "journal_id": journal_entry.id,
            "content": request.content,
            "emotion": request.emotion,
            "images": session_images if session_images else [],
            "image_urls": image_urls if image_urls else [],
            "status": "success",
        }

    except Exception as e:
        logging.error(f"[❌ ERROR] 手动日记创建失败: {e}")
        return {
            "journal_id": None,
            "content": request.content if hasattr(request, "content") else "",
            "emotion": request.emotion if hasattr(request, "emotion") else "",
            "images": [],
            "image_urls": [],
            "status": "error",
        }

# ==================== 日记更新 ====================

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
        
        # 更新内容
        if request.content is not None:
            j.content = request.content
            updated_fields.append("content")

        # 更新情绪
        if request.emotion is not None:
            j.emotion = request.emotion
            updated_fields.append("emotion")

        # 处理图片增量更新
        if request.has_image:
            try:
                logging.info(f"📷 开始处理日记图片增量更新...")
                
                # 获取当前图片ID列表
                current_image_ids = []
                if j.images:
                    current_image_ids = [int(id) for id in j.images.split(",")]
                
                # 1. 删除不在保留列表中的图片
                keep_ids = set(request.keep_image_ids or [])
                deleted_count = 0
                
                for image_id in current_image_ids:
                    if image_id not in keep_ids:
                        try:
                            old_image = db.query(Image).filter(Image.id == image_id).first()
                            if old_image:
                                # 删除图片文件
                                import os
                                if os.path.exists(old_image.file_path):
                                    os.remove(old_image.file_path)
                                # 删除图片记录
                                db.delete(old_image)
                                deleted_count += 1
                                logging.info(f"🗑️ 删除图片: {image_id}")
                        except Exception as e:
                            logging.warning(f"⚠️ 删除图片 {image_id} 失败: {e}")
                
                # 2. 添加新图片
                new_image_ids = []
                if request.add_image_data:
                    logging.info(f"📷 开始添加 {len(request.add_image_data)} 张新图片...")
                    for i, image_data_b64 in enumerate(request.add_image_data):
                        try:
                            # 解码Base64图片数据
                            import base64
                            image_data = base64.b64decode(image_data_b64.split(',')[1] if ',' in image_data_b64 else image_data_b64)
                            logging.info(f"📷 新图片{i+1}数据解码成功，大小: {len(image_data)} bytes")
                            
                            # 保存并分析图片
                            result = image_service.save_image(
                                image_data=image_data,
                                user_id=user_id,
                                session_id=j.session_id or "manual",
                                original_filename=f"updated_journal_image_{i+1}.jpg"
                            )
                            
                            if result["success"]:
                                new_image_ids.append(result["image_id"])
                                logging.info(f"✅ 新图片{i+1}保存成功: {result['image_id']}")
                            else:
                                logging.error(f"❌ 新图片{i+1}处理失败: {result.get('error', '未知错误')}")
                                
                        except Exception as e:
                            logging.error(f"❌ 新图片{i+1}处理异常: {e}")
                            import traceback
                            traceback.print_exc()
                
                # 3. 更新图片字段：保留的图片 + 新增的图片
                final_image_ids = list(keep_ids) + new_image_ids
                j.images = ",".join(map(str, final_image_ids)) if final_image_ids else None
                updated_fields.append("images")
                
                logging.info(f"✅ 图片增量更新完成:")
                logging.info(f"   - 删除图片: {deleted_count} 张")
                logging.info(f"   - 保留图片: {len(keep_ids)} 张")
                logging.info(f"   - 新增图片: {len(new_image_ids)} 张")
                logging.info(f"   - 最终图片: {len(final_image_ids)} 张")
                
            except Exception as e:
                logging.error(f"❌ 图片增量更新异常: {e}")
                import traceback
                traceback.print_exc()
        elif request.has_image is False:
            # 如果明确设置为没有图片，删除所有图片
            if j.images:
                old_image_ids = j.images.split(",")
                for image_id in old_image_ids:
                    try:
                        old_image = db.query(Image).filter(Image.id == int(image_id)).first()
                        if old_image:
                            # 删除图片文件
                            import os
                            if os.path.exists(old_image.file_path):
                                os.remove(old_image.file_path)
                            # 删除图片记录
                            db.delete(old_image)
                    except Exception as e:
                        logging.warning(f"⚠️ 删除图片失败: {e}")
                
                j.images = None
                updated_fields.append("images")
                logging.info("✅ 已删除所有图片")

        from datetime import timezone, timedelta as _td
        j.updated_at = datetime.now(timezone(_td(hours=8)))

        db.commit(); db.refresh(j); db.close()
        logging.info(f"✅ 日记更新成功，字段: {updated_fields}")

        # 生成图片URL列表
        image_urls = []
        if j.images:
            image_ids = j.images.split(",")
            for image_id in image_ids:
                try:
                    db: Session = SessionLocal()
                    image = db.query(Image).filter(Image.id == int(image_id)).first()
                    if image:
                        image_urls.append(f"/api/images/user_{image.user_id}/{image.filename}")
                    db.close()
                except Exception as e:
                    logging.warning(f"⚠️ 获取图片URL失败: {e}")

        return {
            "status": "success",
            "journal_id": j.id,
            "content": j.content,
            "emotion": j.emotion,
            "images": j.images.split(",") if j.images else [],
            "image_urls": image_urls,
            "updated_fields": updated_fields,
            "message": "日记更新成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 更新日记失败: {e}")
        return {"status": "error", "message": "更新日记失败"}

@app.get("/journal/{journal_id}/history")
def get_journal_history(journal_id: int, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取日记关联的对话历史
    """
    try:
        db: Session = SessionLocal()
        j = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if not j:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        # 获取对话历史
        history = []
        if j.session_id:
            state = session_manager.get_or_create_session(user_id, j.session_id)
            history = state.history
        
        db.close()
        return {
            "status": "success", 
            "journal_id": journal_id,
            "session_id": j.session_id,
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[❌ ERROR] 获取日记对话历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话历史失败")


# ==================== Apple 订阅 ====================
@app.post("/subscription/verify")
def verify_subscription(request: SubscriptionVerifyRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    验证 Apple 订阅收据
    """
    try:
        logging.info(f"🔍 验证订阅: user_id={user_id}")
        
        # 1. 向 Apple 验证收据（先尝试沙盒环境）
        try:
            apple_response = verify_receipt_with_apple(
                receipt_data=request.receipt_data,
                password=request.password,
                use_sandbox=True
            )
        except AppleSubscriptionError as e:
            if "收据是生产收据" in str(e):
                # 如果是生产收据，尝试生产环境
                logging.info("🔄 尝试生产环境验证")
                apple_response = verify_receipt_with_apple(
                    receipt_data=request.receipt_data,
                    password=request.password,
                    use_sandbox=False
                )
            else:
                raise e
        
        # 2. 解析订阅信息
        subscription_info = parse_subscription_info(apple_response)
        
        # 3. 更新用户订阅状态
        db: Session = SessionLocal()
        try:
            environment = "production" if not apple_response.get("environment", "").lower() == "sandbox" else "sandbox"
            user = update_user_subscription(
                db=db,
                user_id=user_id,
                subscription_info=subscription_info,
                receipt_data=request.receipt_data,
                environment=environment
            )
            
            return {
                "status": "success",
                "message": "订阅验证成功",
                "subscription": {
                    "status": user.subscription_status,
                    "product_id": user.subscription_product_id,
                    "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                    "auto_renew": user.auto_renew_status,
                    "environment": user.subscription_environment,
                    "is_member": user.subscription_status == "active"
                }
            }
            
        finally:
            db.close()
            
    except AppleSubscriptionError as e:
        logging.error(f"❌ 订阅验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"❌ 订阅验证异常: {e}")
        raise HTTPException(status_code=500, detail="订阅验证失败，请稍后再试")

@app.get("/subscription/status")
def get_subscription_status(user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取用户订阅状态
    """
    try:
        logging.info(f"📊 查询订阅状态: user_id={user_id}")
        
        db: Session = SessionLocal()
        try:
            subscription_info = get_user_subscription_status(db, user_id)
            
            return {
                "status": "success",
                "subscription": subscription_info
            }
            
        finally:
            db.close()
            
    except AppleSubscriptionError as e:
        logging.error(f"❌ 查询订阅状态失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"❌ 查询订阅状态异常: {e}")
        raise HTTPException(status_code=500, detail="查询订阅状态失败")

@app.post("/subscription/webhook")
def handle_subscription_webhook(notification: AppleWebhookNotification) -> Dict[str, Any]:
    """
    处理 Apple 服务器通知
    注意：这个接口不需要用户认证，因为它是 Apple 服务器直接调用的
    """
    try:
        logging.info(f"📨 收到 Apple 通知: type={notification.notification_type}")
        
        # 处理通知
        result = handle_apple_webhook_notification(notification.dict())
        
        return {
            "status": "success",
            "message": "通知处理完成"
        }
        
    except Exception as e:
        logging.error(f"❌ 处理 Apple 通知失败: {e}")
        raise HTTPException(status_code=500, detail="通知处理失败")

@app.post("/subscription/refresh")
def refresh_subscription_status(user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    刷新用户订阅状态（重新验证最新收据）
    """
    try:
        logging.info(f"🔄 刷新订阅状态: user_id={user_id}")
        
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            if not user.latest_receipt:
                raise HTTPException(status_code=400, detail="用户没有订阅记录")
            
            # 重新验证收据
            try:
                apple_response = verify_receipt_with_apple(
                    receipt_data=user.latest_receipt,
                    use_sandbox=(user.subscription_environment == "sandbox")
                )
            except AppleSubscriptionError as e:
                if "收据是生产收据" in str(e) and user.subscription_environment == "sandbox":
                    # 尝试生产环境
                    apple_response = verify_receipt_with_apple(
                        receipt_data=user.latest_receipt,
                        use_sandbox=False
                    )
                else:
                    raise e
            
            # 解析并更新订阅信息
            subscription_info = parse_subscription_info(apple_response)
            environment = "production" if not apple_response.get("environment", "").lower() == "sandbox" else "sandbox"
            
            user = update_user_subscription(
                db=db,
                user_id=user_id,
                subscription_info=subscription_info,
                receipt_data=user.latest_receipt,
                environment=environment
            )
            
            return {
                "status": "success",
                "message": "订阅状态刷新成功",
                "subscription": {
                    "status": user.subscription_status,
                    "product_id": user.subscription_product_id,
                    "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                    "auto_renew": user.auto_renew_status,
                    "environment": user.subscription_environment,
                    "is_member": user.subscription_status == "active"
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except AppleSubscriptionError as e:
        logging.error(f"❌ 刷新订阅状态失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"❌ 刷新订阅状态异常: {e}")
        raise HTTPException(status_code=500, detail="刷新订阅状态失败")

@app.get("/subscription/products")
def get_subscription_products(user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取订阅产品列表
    """
    try:
        logging.info(f"🔍 获取订阅产品列表: user_id={user_id}")
        
        # 定义可用的订阅产品
        products = [
            {
                "id": "monthly",
                "name": "包月",
                "price": "¥12",
                "daily_price": "仅需¥0.40/天",
                "period": "monthly",
                "period_display": "每月",
                "apple_product_id": "com.yztao92.EmoFlow.subscription.monthly",
                "is_popular": False,
                "sort_order": 1
            },
            {
                "id": "yearly",
                "name": "包年",
                "price": "¥98.00",
                "daily_price": "仅需¥0.27/天",
                "period": "yearly",
                "period_display": "每年",
                "apple_product_id": "com.yztao92.EmoFlow.subscription.yearly",
                "is_popular": True,
                "sort_order": 2
            }
        ]
        
        # 按 sort_order 排序
        products.sort(key=lambda x: x["sort_order"])
        
        logging.info(f"✅ 成功获取订阅产品列表: 共{len(products)}个产品")
        
        return {
            "status": "success",
            "message": "获取产品列表成功",
            "products": products
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 获取订阅产品列表异常: {e}")
        raise HTTPException(status_code=500, detail="获取产品列表失败")

@app.post("/subscription/restore")
def restore_subscription(request: SubscriptionVerifyRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    恢复订阅购买
    用于用户重新安装应用后恢复之前的订阅
    """
    try:
        logging.info(f"🔄 恢复订阅购买: user_id={user_id}")
        
        # 1. 向 Apple 验证收据（先尝试沙盒环境）
        try:
            apple_response = verify_receipt_with_apple(
                receipt_data=request.receipt_data,
                password=request.password,
                use_sandbox=True
            )
        except AppleSubscriptionError as e:
            if "收据是生产收据" in str(e):
                # 如果是生产收据，尝试生产环境
                logging.info("🔄 尝试生产环境验证")
                apple_response = verify_receipt_with_apple(
                    receipt_data=request.receipt_data,
                    password=request.password,
                    use_sandbox=False
                )
            else:
                raise e
        
        # 2. 解析订阅信息
        subscription_info = parse_subscription_info(apple_response)
        
        # 3. 更新用户订阅状态
        db: Session = SessionLocal()
        try:
            environment = "production" if not apple_response.get("environment", "").lower() == "sandbox" else "sandbox"
            user = update_user_subscription(
                db=db,
                user_id=user_id,
                subscription_info=subscription_info,
                receipt_data=request.receipt_data,
                environment=environment
            )
            
            return {
                "status": "success",
                "message": "恢复购买成功",
                "subscription": {
                    "status": user.subscription_status,
                    "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                    "product_id": user.subscription_product_id,
                    "auto_renew": user.auto_renew_status,
                    "environment": user.subscription_environment,
                    "is_member": user.subscription_status == "active"
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except AppleSubscriptionError as e:
        logging.error(f"❌ 恢复订阅失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"❌ 恢复订阅异常: {e}")
        raise HTTPException(status_code=500, detail="恢复订阅失败，请稍后再试")