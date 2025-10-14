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
        - birthday: 用户生日（可选）
        注意：订阅状态通过订阅验证接口管理，不在此处更新
    """
    name: Optional[str] = None  # 用户姓名，可选字段
    email: Optional[str] = None  # 用户邮箱，可选字段
    birthday: Optional[date] = None  # 用户生日，可选字段

class UserResponse(BaseModel):
    """
    用户信息响应模型
    功能：返回给前端的用户信息格式
    
    字段说明：
        - id: 用户ID
        - name: 用户姓名
        - email: 用户邮箱
        - heart: 用户心数值
        - birthday: 用户生日
        - subscription_status: 订阅状态
        - subscription_expires_at: 订阅过期时间
        注意：记忆点数据现在存储在journals表的memory_point字段中
    """
    id: int  # 用户ID
    name: Optional[str] = None  # 用户姓名
    email: Optional[str] = None  # 用户邮箱
    heart: int  # 用户心数值
    birthday: Optional[date] = None  # 用户生日
    subscription_status: str  # 订阅状态
    subscription_expires_at: Optional[datetime] = None  # 订阅过期时间

# ==================== 订阅相关模型 ====================
class SubscriptionVerifyRequest(BaseModel):
    """
    订阅验证请求模型
    功能：验证Apple订阅收据的数据格式
    """
    receipt_data: str  # Base64编码的收据数据
    password: Optional[str] = None  # App Store Connect的共享密钥（可选）

class SubscriptionStatusResponse(BaseModel):
    """
    订阅状态响应模型
    功能：返回用户订阅状态信息
    """
    subscription_status: str  # 订阅状态
    subscription_product_id: Optional[str] = None  # 订阅产品ID
    subscription_expires_at: Optional[datetime] = None  # 订阅到期时间
    auto_renew_status: bool  # 自动续费状态
    subscription_environment: str  # 订阅环境

class AppleWebhookNotification(BaseModel):
    """
    Apple服务器通知模型
    功能：处理Apple的服务器通知
    """
    notification_type: str  # 通知类型
    subtype: Optional[str] = None  # 子类型
    notification_uuid: str  # 通知UUID
    data: dict  # 通知数据

class TestLoginRequest(BaseModel):
    """
    测试登录请求模型
    功能：为Apple测试人员提供测试账号登录
    """
    username: str  # 测试用户名
    password: str  # 测试密码

class DeleteAccountRequest(BaseModel):
    """
    删除账户请求模型
    功能：验证删除账户请求的数据格式
    """
    confirm_deletion: bool  # 确认删除标志，必须为True才能删除

class DeleteAccountResponse(BaseModel):
    """
    删除账户响应模型
    功能：返回删除账户操作的结果
    """
    success: bool  # 删除是否成功
    message: str  # 操作结果消息
    deleted_data: dict  # 删除的数据统计 