# File: database_models/chat_session.py
# 功能：聊天会话数据模型定义
# 实现：使用SQLAlchemy ORM，存储用户聊天会话状态

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from .database import Base

# ==================== 聊天会话模型 ====================
class ChatSession(Base):
    """
    聊天会话数据模型
    功能：存储用户的聊天会话状态，包括对话历史和当前状态
    
    字段说明：
        - id: 主键，会话唯一标识
        - user_id: 外键，关联用户ID
        - session_id: 会话ID（前端传入）
        - state_data: 会话状态数据（JSON格式存储StateTracker数据）
        - current_image_id: 当前会话的图片ID（如果有）
        - is_active: 会话是否活跃
        - created_at: 创建时间
        - updated_at: 更新时间
        - user: 关联的用户对象（多对一关系）
    """
    __tablename__ = "chat_sessions"  # 数据库表名
    
    # 主键字段
    id = Column(Integer, primary_key=True, index=True)  # 会话ID，主键，建立索引
    
    # 外键字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不可为空
    
    # 会话标识字段
    session_id = Column(String(255), nullable=False)  # 会话ID，前端传入，不可为空
    
    # 状态数据字段
    state_data = Column(Text, nullable=True)  # 会话状态数据，JSON格式存储，可为空
    current_image_id = Column(String(255), nullable=True)  # 当前会话的图片ID，可为空
    
    # 状态字段
    is_active = Column(Boolean, default=True)  # 会话是否活跃，默认为True
    
    # 时间戳字段
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))  # 创建时间，东八区
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), onupdate=lambda: datetime.now(timezone(timedelta(hours=8))))  # 更新时间，东八区
    
    # 关联关系：会话属于某个用户
    user = relationship("User", back_populates="chat_sessions")
    
    # 唯一约束：同一用户的同一session_id只能有一个活跃会话
    __table_args__ = (
        {"extend_existing": True}
    )
