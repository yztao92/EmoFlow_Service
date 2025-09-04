# File: database_models/schemas.py
# 功能：数据验证模型定义
# 实现：使用Pydantic进行数据验证和序列化

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

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

class UpdateProfileRequest(BaseModel):
    """
    用户资料更新请求的数据验证模型
    功能：验证用户资料更新的数据格式
    
    字段说明：
        - name: 用户姓名（可选）
        - email: 用户邮箱（可选）
        - is_member: 是否为会员（可选）
        - birthday: 用户生日（可选）
        - membership_expires_at: 会员过期时间（可选）
        注意：记忆点数据现在存储在journals表的memory_point字段中
    """
    name: Optional[str] = None  # 用户姓名，可选字段
    email: Optional[str] = None  # 用户邮箱，可选字段
    is_member: Optional[bool] = None  # 是否为会员，可选字段
    birthday: Optional[date] = None  # 用户生日，可选字段
    membership_expires_at: Optional[datetime] = None  # 会员过期时间，可选字段

class UserResponse(BaseModel):
    """
    用户信息响应模型
    功能：返回给前端的用户信息格式
    
    字段说明：
        - id: 用户ID
        - name: 用户姓名
        - email: 用户邮箱
        - heart: 用户心数值
        - is_member: 是否为会员
        - birthday: 用户生日
        - membership_expires_at: 会员过期时间
        注意：记忆点数据现在存储在journals表的memory_point字段中
    """
    id: int  # 用户ID
    name: Optional[str] = None  # 用户姓名
    email: Optional[str] = None  # 用户邮箱
    heart: int  # 用户心数值
    is_member: bool  # 是否为会员
    birthday: Optional[date] = None  # 用户生日
    membership_expires_at: Optional[datetime] = None  # 会员过期时间 