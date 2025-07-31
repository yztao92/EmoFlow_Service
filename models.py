# File: models.py
# 功能：数据库模型定义，包含用户和日记的数据结构
# 实现：使用SQLAlchemy ORM，支持用户认证和日记管理

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine  # SQLAlchemy ORM组件
from sqlalchemy.ext.declarative import declarative_base  # 声明式基类
from sqlalchemy.orm import sessionmaker, relationship  # ORM会话和关系
from pydantic import BaseModel  # Pydantic数据验证
from typing import Optional  # 类型提示
from datetime import datetime, timezone, timedelta  # 时间处理

# ==================== 数据库配置 ====================
# SQLite数据库连接URL
# 参数来源：项目配置，使用本地SQLite文件存储
DATABASE_URL = "sqlite:///./database/users.db"

# 创建数据库引擎
# 参数说明：
# - DATABASE_URL: 数据库连接字符串
# - connect_args: SQLite特定参数，允许多线程访问
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建会话工厂
# 参数说明：
# - bind: 绑定到数据库引擎
# - autoflush: 禁用自动刷新
# - autocommit: 禁用自动提交
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 声明式基类
Base = declarative_base()

# ==================== 用户模型 ====================
class User(Base):
    """
    用户数据模型
    功能：存储用户基本信息，支持Apple登录认证
    
    字段说明：
        - id: 主键，用户唯一标识
        - apple_user_id: Apple用户ID，用于Apple登录认证
        - email: 用户邮箱（可选）
        - name: 用户姓名（可选）
        - journals: 关联的日记列表（一对多关系）
    """
    __tablename__ = "users"  # 数据库表名
    
    # 主键字段
    id = Column(Integer, primary_key=True, index=True)  # 用户ID，主键，建立索引
    
    # Apple登录相关字段
    apple_user_id = Column(String, unique=True, index=True)  # Apple用户ID，唯一，建立索引
    
    # 用户基本信息字段
    email = Column(String, nullable=True)  # 用户邮箱，可为空
    name = Column(String, nullable=True)  # 用户姓名，可为空
    
    # 关联关系：一个用户可以有多个日记
    journals = relationship("Journal", back_populates="user")

# ==================== 日记模型 ====================
class Journal(Base):
    """
    日记数据模型
    功能：存储用户的心情日记，包含对话历史和情绪信息
    
    字段说明：
        - id: 主键，日记唯一标识
        - user_id: 外键，关联用户ID
        - title: 日记标题
        - content: 日记内容
        - messages: 对话历史（JSON格式存储）
        - session_id: 关联的对话会话ID
        - emotion: 情绪标签
        - created_at: 创建时间
        - updated_at: 更新时间
        - user: 关联的用户对象（多对一关系）
    """
    __tablename__ = "journals"  # 数据库表名
    
    # 主键字段
    id = Column(Integer, primary_key=True, index=True)  # 日记ID，主键，建立索引
    
    # 外键字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不可为空
    
    # 日记内容字段
    title = Column(String, nullable=False)  # 日记标题，不可为空
    content = Column(Text, nullable=False)  # 日记内容，不可为空
    
    # 关联信息字段
    messages = Column(Text, nullable=True)  # 对话历史，JSON格式存储，可为空
    session_id = Column(String, nullable=True)  # 关联的对话会话ID，可为空
    emotion = Column(String, nullable=True)  # 情绪标签，可为空
    
    # 时间戳字段
    # 使用lambda函数确保每次创建时都获取当前时间
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))  # 创建时间，东八区
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), onupdate=lambda: datetime.now(timezone(timedelta(hours=8))))  # 更新时间，东八区
    
    # 关联关系：日记属于某个用户
    user = relationship("User", back_populates="journals")

# ==================== Pydantic模型 ====================
class AppleLoginRequest(BaseModel):
    """
    Apple登录请求的数据验证模型
    功能：验证Apple登录请求的数据格式
    
    字段说明：
        - identity_token: Apple身份令牌（必需）
        - full_name: 用户全名（可选）
        - email: 用户邮箱（可选）
    """
    identity_token: str  # Apple身份令牌，必需字段
    full_name: Optional[str] = None  # 用户全名，可选字段
    email: Optional[str] = None  # 用户邮箱，可选字段

# ==================== 数据库初始化 ====================
def init_db():
    """
    初始化数据库
    功能：创建所有数据库表结构
    
    说明：
        此函数在应用启动时调用，确保数据库表结构存在
        如果表已存在，不会重复创建
    """
    Base.metadata.create_all(bind=engine)  # 创建所有表结构