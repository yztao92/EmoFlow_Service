# File: database_models/journal.py
# 功能：日记数据模型定义
# 实现：使用SQLAlchemy ORM，存储用户心情日记

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from .database import Base

# ==================== 日记模型 ====================
class Journal(Base):
    """
    日记数据模型
    功能：存储用户的心情日记，包含对话历史和情绪信息
    
    字段说明：
        - id: 主键，日记唯一标识
        - user_id: 外键，关联用户ID
        - title: 日记标题
        - content: 日记内容（向后兼容，保留原字段）
        - content_html: 净化后的HTML内容
        - content_plain: 纯文本内容备份
        - content_format: 内容格式（html, markdown, plain）
        - is_safe: 安全标识
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
    
    # 日记内容字段（向后兼容）
    title = Column(String, nullable=False)  # 日记标题，不可为空
    content = Column(Text, nullable=False)  # 日记内容，不可为空（向后兼容）
    
    # 新的安全内容字段
    content_html = Column(Text, nullable=True)  # 净化后的HTML内容
    content_plain = Column(Text, nullable=True)  # 纯文本内容备份
    content_format = Column(String, default='html')  # 内容格式
    is_safe = Column(Boolean, default=False)  # 安全标识
    
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