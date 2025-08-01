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

# 导入项目内部模块
from rag.rag_chain import run_rag_chain  # RAG 聊天链，用于生成AI回复
from dialogue.state_tracker import StateTracker  # 对话状态跟踪器
from database_models import init_db, SessionLocal, User, Journal  # 数据库模型

from dotenv import load_dotenv
load_dotenv()  # 加载 .env 环境变量文件

# ==================== JWT 认证配置 ====================
# JWT (JSON Web Token) 用于用户身份验证
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-fallback-dev-secret")  # JWT 密钥，从环境变量获取
JWT_ALGORITHM = "HS256"  # JWT 签名算法
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # JWT 过期时间：7天

# ==================== Apple 登录配置 ====================
# Apple Sign-In 认证相关配置
APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"  # Apple 公钥获取地址
APPLE_ISSUER = "https://appleid.apple.com"  # Apple 身份提供者
APPLE_CLIENT_ID = "Nick-Studio.EmoFlow"  # 应用的服务ID，用于验证 Apple 令牌

# Apple 公钥缓存，避免重复请求
apple_keys = []

# ==================== 日志配置 ====================
# 配置日志系统，确保在多进程环境下正常工作
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)  # 移除所有现有处理器，避免重复日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")  # 设置日志格式
logger = logging.getLogger(__name__)

# ==================== 环境变量检查 ====================
# 检查必需的环境变量是否已配置
required_env_vars = ["QIANWEN_API_KEY"]  # 必需的API密钥列表
missing_vars = [var for var in required_env_vars if not os.getenv(var)]  # 找出缺失的环境变量
if missing_vars:
    raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")  # 如果缺少必需变量则抛出异常

# ==================== LLM 初始化 ====================
# 现在主要使用千问LLM，DeepSeek作为备用
# 注意：DeepSeek LLM 实例在需要时通过 llm_factory 获取

# ==================== FastAPI 应用初始化 ====================
# 创建 FastAPI 应用实例
app = FastAPI()

# 添加 CORS 中间件，允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应限制具体域名）
    allow_credentials=True,  # 允许携带认证信息
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"]  # 允许所有请求头
)

# ==================== 全局状态管理 ====================
# 存储用户会话状态，key为session_id，value为StateTracker实例
session_states: Dict[str, StateTracker] = {}

# ==================== 应用启动事件 ====================
@app.on_event("startup")
def on_startup():
    """
    应用启动时执行的初始化函数
    功能：初始化数据库、加载Apple公钥
    """
    init_db()  # 初始化数据库表结构
    global apple_keys
    apple_keys = requests.get(APPLE_PUBLIC_KEYS_URL).json()["keys"]  # 获取Apple公钥列表
    logger.info("✅ Apple 公钥加载成功")

# ==================== 基础路由 ====================
@app.get("/")
def read_root():
    """
    根路径，用于健康检查
    返回：服务运行状态信息
    """
    return {"message": "EmoFlow 服务运行中"}

# ==================== Apple 登录认证模块 ====================

class AppleLoginRequest(BaseModel):
    """
    Apple 登录请求的数据模型
    参数来源：iOS 客户端发送的 Apple Sign-In 数据
    """
    identity_token: str  # Apple 身份令牌
    full_name: Optional[str] = None  # 用户全名（可选）
    email: Optional[str] = None  # 用户邮箱（可选）

@app.post("/auth/apple")
def login_with_apple(req: AppleLoginRequest):
    """
    Apple 登录认证接口
    功能：验证 Apple 身份令牌，创建或更新用户，返回JWT令牌
    
    参数：
        req (AppleLoginRequest): 包含 Apple 身份令牌和用户信息的请求对象
        参数来源：iOS 客户端的 Apple Sign-In 回调
    
    返回：
        dict: 包含用户信息和JWT令牌的响应
    """
    try:
        logging.info(f"🔍 收到 Apple 登录请求: identity_token长度={len(req.identity_token)}, full_name='{req.full_name}', email='{req.email}'")
        
        # 处理 Base64 编码的令牌
        import base64
        try:
            # 尝试解码 Base64 编码的令牌
            token_bytes = base64.b64decode(req.identity_token)
            token = token_bytes.decode('utf-8')
        except:
            # 如果不是 Base64，直接使用原始字符串
            token = req.identity_token
            
        # 解析 JWT 头部，获取密钥ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]  # 密钥ID
        
        # 从缓存的公钥中找到对应的密钥
        key_data = next((k for k in apple_keys if k["kid"] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Apple 公钥未找到")

        # 构造公钥并验证签名
        public_key = jwk.construct(key_data)
        message, encoded_sig = token.rsplit('.', 1)
        decoded_sig = base64url_decode(encoded_sig.encode())

        if not public_key.verify(message.encode(), decoded_sig):
            raise HTTPException(status_code=401, detail="无效签名")

        # 解码并验证 JWT 令牌
        decoded = jwt.decode(
            token,
            key=public_key.to_pem().decode(),
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,  # 验证受众
            issuer=APPLE_ISSUER  # 验证发行者
        )

        # 提取用户信息
        apple_user_id = decoded["sub"]  # Apple 用户唯一标识
        # 优先使用前端发送的邮箱，如果没有则使用令牌中的邮箱
        email = req.email or decoded.get("email")
        # 获取用户姓名
        name = req.full_name

        # 数据库操作：查找或创建用户
        db: Session = SessionLocal()
        user = db.query(User).filter(User.apple_user_id == apple_user_id).first()
        if not user:
            # 新用户：创建用户记录
            user = User(apple_user_id=apple_user_id, email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # 现有用户：更新信息（如果前端提供了新的信息）
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

        # 生成应用内部的 JWT 令牌
        token_data = {
            "sub": str(user.id),  # 用户ID
            "apple_user_id": user.apple_user_id,  # Apple用户ID
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)  # 过期时间
        }
        token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        return {
            "status": "ok",
            "token": token,  # 返回JWT令牌给客户端
            "user_id": user.id,
            "email": user.email,
            "name": user.name or f"用户{user.id}"  # 如果没有姓名，使用默认用户名
        }

    except Exception as e:
        logging.error(f"❌ Apple 登录失败: {e}")
        raise HTTPException(status_code=401, detail="Apple 登录验证失败")

def get_current_user(token: str = Header(...)) -> int:
    """
    从请求头中提取并验证JWT令牌，返回用户ID
    用于需要用户认证的接口
    
    参数：
        token (str): 从请求头 Authorization 中提取的JWT令牌
        参数来源：客户端在请求头中发送的JWT令牌
    
    返回：
        int: 用户ID
    
    异常：
        HTTPException: 令牌无效或过期时抛出401错误
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])  # 返回用户ID
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的 Token")

# ==================== 聊天模块 ====================

class Message(BaseModel):
    """
    聊天消息的数据模型
    参数来源：客户端发送的聊天消息
    """
    role: str  # 消息角色：user（用户）或 assistant（AI助手）
    content: str  # 消息内容

class ChatRequest(BaseModel):
    """
    聊天请求的数据模型
    参数来源：客户端发送的聊天请求
    """
    session_id: str  # 会话ID，用于标识对话会话
    messages: List[Message]  # 消息列表，包含完整的对话历史
    emotion: Optional[str] = None  # 情绪字段（可选），客户端可提供情绪信息

@app.post("/chat")
def chat_with_user(request: ChatRequest) -> Dict[str, Any]:
    """
    聊天接口：处理用户消息并返回AI回复
    
    参数：
        request (ChatRequest): 包含会话ID、消息历史和情绪信息的请求对象
        参数来源：客户端（iOS/Web）发送的聊天请求
    
    返回：
        Dict[str, Any]: 包含AI回复的响应对象
    """
    logging.info("收到 /chat 请求")
    try:
        logging.info(f"\n🔔 收到请求：{request.json()}")
        
        # 获取或创建会话状态跟踪器
        state = session_states.setdefault(request.session_id, StateTracker())
        
        # 更新对话历史（直接覆盖，避免重复）
        state.history = [(m.role, m.content) for m in request.messages]
        
        # 提取用户最新输入
        user_query = request.messages[-1].content
        logging.info(f"📨 [用户提问] {user_query}")

        # 使用前端传入的情绪，如果没有则默认为 neutral
        emotion = request.emotion or "neutral"
        state.update_emotion(emotion)
        logging.info(f"🔍 [emotion] 使用前端情绪 → {emotion}")

        # 计算对话轮次
        user_messages = [m for m in request.messages if m.role == "user"]
        round_index = len(user_messages)
        logging.info(f"🔁 [轮次] 用户发言轮次：{round_index}")

        # 生成对话状态摘要
        context_summary = state.summary(last_n=3)
        logging.info(f"📝 [状态摘要]\n{context_summary}")

        # 调用RAG链生成AI回复
        answer = run_rag_chain(
            query=user_query,  # 用户查询
            round_index=round_index,  # 对话轮次
            state_summary=context_summary,  # 状态摘要
            emotion=emotion  # 前端传入的情绪
        )

        # 更新AI回复到对话历史
        state.update_message("assistant", answer)

        return {
            "response": {
                "answer": answer,  # AI生成的回复
                "references": []  # 引用信息（当前为空）
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

# ==================== 日记生成模块 ====================

@app.post("/journal/generate")
def generate_journal(request: ChatRequest, user_id: int = Depends(get_current_user)) -> Dict[str, Any]:
    """
    生成心情日记接口：根据对话历史生成个人心情总结
    
    参数：
        request (ChatRequest): 包含对话历史的请求对象
        参数来源：客户端发送的日记生成请求
        user_id (int): 当前用户ID，通过JWT令牌自动获取
        参数来源：get_current_user 函数从JWT令牌中提取
    
    返回：
        Dict[str, Any]: 包含生成的日记内容和元信息的响应
    """
    try:
        logging.info(f"\n📝 收到生成心情日记请求：用户ID={user_id}, 请求={request.json()}")
        
        # 将对话历史转换为文本格式
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        
        # 生成日记内容的系统提示词
        journal_system_prompt = f"""你是用户的情绪笔记助手，请根据以下对话内容，以"我"的视角，总结一段今天的心情日记。\n注意要自然、有情感，不要提到对话或 AI，只写个人的感受和经历：\n-----------\n{prompt}\n-----------"""
        
        # 调用千问LLM生成日记内容
        from llm.llm_factory import chat_with_qwen_llm
        journal_result = chat_with_qwen_llm(journal_system_prompt)
        journal = journal_result.get("answer", "今天的心情有点复杂，暂时说不清楚。")
        
        # 生成日记标题的系统提示词
        title_system_prompt = f"""请根据以下心情日记内容，生成一个简洁、有情感、不超过10个字的标题。标题要体现日记的主要情感和主题：\n-----------\n{journal}\n-----------"""
        
        # 调用千问LLM生成日记标题
        title_result = chat_with_qwen_llm(title_system_prompt)
        title = title_result.get("answer", "今日心情")
        
        # 清理标题，确保简洁
        title = title.strip().replace('"', '').replace('"', '')
        if len(title) > 10:
            title = title[:10] + "..."
        
        # 保存日记到数据库
        db: Session = SessionLocal()
        try:
            # 将 messages 转换为 JSON 字符串存储，增加容错处理
            try:
                messages_json = json.dumps([{"role": m.role, "content": m.content} for m in request.messages], ensure_ascii=False)
            except Exception as json_error:
                logging.warning(f"⚠️ 消息格式转换失败，使用原始格式: {json_error}")
                # 如果转换失败，尝试直接使用原始数据
                messages_json = json.dumps([{"role": getattr(m, 'role', 'unknown'), "content": getattr(m, 'content', str(m))} for m in request.messages], ensure_ascii=False)
            
            # 创建日记记录
            journal_entry = Journal(
                user_id=user_id,  # 用户ID
                title=title,  # 日记标题
                content=journal,  # 日记内容
                messages=messages_json,  # 存储对话历史
                session_id=request.session_id,  # 关联的会话ID
                emotion=request.emotion  # 情绪信息
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
            "journal": journal,  # 生成的日记内容
            "title": title,  # 生成的日记标题
            "journal_id": journal_entry.id if 'journal_entry' in locals() else None,  # 日记ID
            "emotion": request.emotion,  # 情绪信息
            "status": "success"
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

# ==================== 日记管理模块 ====================

@app.get("/journal/list")
def get_user_journals(user_id: int = Depends(get_current_user), limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """
    获取用户的日记列表接口
    
    参数：
        user_id (int): 当前用户ID，通过JWT令牌自动获取
        参数来源：get_current_user 函数从JWT令牌中提取
        limit (int): 每页返回的日记数量，默认20
        参数来源：客户端请求参数
        offset (int): 分页偏移量，默认0
        参数来源：客户端请求参数
    
    返回：
        Dict[str, Any]: 包含日记列表和分页信息的响应
    """
    try:
        db: Session = SessionLocal()
        
        # 查询用户的日记，按创建时间倒序排列
        journals = db.query(Journal).filter(
            Journal.user_id == user_id
        ).order_by(
            Journal.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        journal_list = []
        for journal in journals:
            # 解析 messages JSON 字符串
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
                "messages": messages,  # 返回对话历史
                "session_id": journal.session_id,
                "emotion": journal.emotion,  # 返回情绪信息
                "created_at": journal.created_at.isoformat() if journal.created_at else None,
                "updated_at": journal.updated_at.isoformat() if journal.updated_at else None
            })
        
        # 获取用户日记总数
        total_count = db.query(Journal).filter(Journal.user_id == user_id).count()
        
        db.close()
        
        return {
            "status": "success",
            "journals": journal_list,  # 日记列表
            "total": total_count,  # 总数
            "limit": limit,  # 每页数量
            "offset": offset  # 偏移量
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
    """
    获取特定日记的详细信息接口
    
    参数：
        journal_id (int): 日记ID，从URL路径参数获取
        参数来源：客户端请求的URL路径
        user_id (int): 当前用户ID，通过JWT令牌自动获取
        参数来源：get_current_user 函数从JWT令牌中提取
    
    返回：
        Dict[str, Any]: 包含日记详细信息的响应
    """
    try:
        db: Session = SessionLocal()
        
        # 查询特定日记，确保只能访问自己的日记
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        # 解析 messages JSON 字符串
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
            "messages": messages,  # 返回对话历史
            "session_id": journal.session_id,
            "emotion": journal.emotion,  # 返回情绪信息
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
    """
    删除用户的日记接口
    
    参数：
        journal_id (int): 日记ID，从URL路径参数获取
        参数来源：客户端请求的URL路径
        user_id (int): 当前用户ID，通过JWT令牌自动获取
        参数来源：get_current_user 函数从JWT令牌中提取
    
    返回：
        Dict[str, Any]: 删除操作的结果
    """
    try:
        db: Session = SessionLocal()
        
        # 查询特定日记，确保只能删除自己的日记
        journal = db.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            db.close()
            raise HTTPException(status_code=404, detail="日记不存在")
        
        # 删除日记
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