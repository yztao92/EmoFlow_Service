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
    功能：存储用户基本信息，支持Apple登录认证
    
    字段说明：
        - id: 主键，用户唯一标识
        - apple_user_id: Apple用户ID，用于Apple登录认证
        - email: 用户邮箱（可选）
        - name: 用户姓名（可选）
        - heart: 用户心数值，初始值为20
        - is_member: 是否为会员，默认False
        - birthday: 用户生日，可为空
        - membership_expires_at: 会员过期时间，可为空
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
    
    # 会员相关字段
    is_member = Column(Boolean, default=False, nullable=False)  # 是否为会员，默认False
    birthday = Column(Date, nullable=True)  # 用户生日，可为空
    membership_expires_at = Column(DateTime, nullable=True)  # 会员过期时间，可为空
    
    # 关联关系：一个用户可以有多个日记
    journals = relationship("Journal", back_populates="user") 