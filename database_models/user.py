# File: database_models/user.py
# 功能：用户数据模型定义
# 实现：使用SQLAlchemy ORM，支持Apple登录认证

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from sqlalchemy.orm import relationship
from .database import Base

# ==================== 用户模型 ====================
class User(Base):
    """
    用户数据模型
    功能：存储用户基本信息，支持Apple登录认证和订阅管理
    
    字段说明：
        - id: 主键，用户唯一标识
        - apple_user_id: Apple用户ID，用于Apple登录认证
        - email: 用户邮箱（可选）
        - name: 用户姓名（可选）
        - heart: 用户心数值，初始值为100
        - birthday: 用户生日，可为空
        - subscription_status: 订阅状态（active/expired/cancelled/inactive）
        - subscription_product_id: 订阅产品ID
        - subscription_expires_at: 订阅到期时间
        - original_transaction_id: 原始交易ID
        - latest_receipt: 最新收据数据
        - auto_renew_status: 自动续费状态
        - subscription_environment: 订阅环境（sandbox/production）
        - journals: 关联的日记列表（一对多关系）
        注意：记忆点数据现在存储在journals表的memory_point字段中
    """
    __tablename__ = "users"  # 数据库表名
    
    # 主键字段
    id = Column(Integer, primary_key=True, index=True)  # 用户ID，主键，建立索引
    
    # Apple登录相关字段
    apple_user_id = Column(String, unique=True, index=True)  # Apple用户ID，唯一，建立索引
    
    # 用户基本信息字段
    email = Column(String, nullable=True)  # 用户邮箱，可为空
    name = Column(String, nullable=True)  # 用户姓名，可为空
    heart = Column(Integer, default=100, nullable=False)  # 用户心数值，默认100，不可为空
    
    # 用户信息字段
    birthday = Column(Date, nullable=True)  # 用户生日，可为空
    
    # Apple 订阅相关字段
    subscription_status = Column(String, default="inactive", nullable=False)  # 订阅状态：active, expired, cancelled, inactive
    subscription_product_id = Column(String, nullable=True)  # 订阅产品ID
    subscription_expires_at = Column(DateTime, nullable=True)  # 订阅到期时间
    original_transaction_id = Column(String, nullable=True)  # 原始交易ID
    latest_receipt = Column(String, nullable=True)  # 最新收据数据
    auto_renew_status = Column(Boolean, default=False, nullable=False)  # 自动续费状态
    subscription_environment = Column(String, default="sandbox", nullable=False)  # 订阅环境：sandbox, production
    
    # 关联关系：一个用户可以有多个日记、多个聊天会话和多个图片
    journals = relationship("Journal", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    images = relationship("Image", back_populates="user") 