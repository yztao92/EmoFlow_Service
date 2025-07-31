# File: database_models/schemas.py
# 功能：数据验证模型定义
# 实现：使用Pydantic进行数据验证和序列化

from pydantic import BaseModel
from typing import Optional

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