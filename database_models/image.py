# File: database_models/image.py
# 功能：图片数据模型定义
# 实现：使用SQLAlchemy ORM，存储用户上传的图片信息

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from .database import Base

# ==================== 图片模型 ====================
class Image(Base):
    """
    图片数据模型
    功能：存储用户上传的图片信息，包括分析结果和关联关系
    
    字段说明：
        - id: 主键，图片唯一标识
        - user_id: 外键，关联用户ID
        - filename: 文件名
        - file_path: 文件存储路径
        - file_size: 文件大小（字节）
        - mime_type: 文件MIME类型
        - width: 图片宽度
        - height: 图片高度
        - analysis_result: qwen-vl-plus分析结果（JSON格式）
        - session_id: 关联的聊天会话ID
        - journal_id: 关联的日记ID（如果有）
        - created_at: 创建时间
        - updated_at: 更新时间
        - user: 关联的用户对象（多对一关系）
    """
    __tablename__ = "images"  # 数据库表名
    
    # 主键字段
    id = Column(Integer, primary_key=True, index=True)  # 图片ID，主键，建立索引
    
    # 外键字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不可为空
    
    # 文件信息字段
    filename = Column(String(255), nullable=False)  # 文件名，不可为空
    file_path = Column(String(500), nullable=False)  # 文件存储路径，不可为空
    file_size = Column(Integer, nullable=False)  # 文件大小（字节），不可为空
    mime_type = Column(String(100), nullable=False)  # 文件MIME类型，不可为空
    
    # 图片属性字段
    width = Column(Integer, nullable=True)  # 图片宽度，可为空
    height = Column(Integer, nullable=True)  # 图片高度，可为空
    
    # 分析结果字段
    analysis_result = Column(Text, nullable=True)  # qwen-vl-plus分析结果，JSON格式，可为空
    
    # 关联信息字段
    session_id = Column(String(255), nullable=True)  # 关联的聊天会话ID，可为空
    journal_id = Column(Integer, nullable=True)  # 关联的日记ID，可为空
    
    # 时间戳字段
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))  # 创建时间，东八区
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), onupdate=lambda: datetime.now(timezone(timedelta(hours=8))))  # 更新时间，东八区
    
    # 关联关系：图片属于某个用户
    user = relationship("User", back_populates="images")
