# File: subscription/apple_subscription.py
# 功能：Apple 订阅验证和处理逻辑
# 实现：处理 Apple StoreKit 订阅验证、状态管理等功能

import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database_models.user import User

logger = logging.getLogger(__name__)

# Apple 验证服务器 URL
APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"

# 订阅状态常量
SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_EXPIRED = "expired"
SUBSCRIPTION_STATUS_CANCELLED = "cancelled"
SUBSCRIPTION_STATUS_INACTIVE = "inactive"

class AppleSubscriptionError(Exception):
    """Apple 订阅相关异常"""
    pass

def verify_receipt_with_apple(receipt_data: str, password: Optional[str] = None, use_sandbox: bool = True) -> Dict[str, Any]:
    """
    向 Apple 服务器验证收据
    
    Args:
        receipt_data: Base64 编码的收据数据
        password: App Store Connect 共享密钥（可选）
        use_sandbox: 是否使用沙盒环境
    
    Returns:
        Apple 服务器返回的验证结果
        
    Raises:
        AppleSubscriptionError: 验证失败时抛出
    """
    url = APPLE_SANDBOX_URL if use_sandbox else APPLE_PRODUCTION_URL
    
    payload = {
        "receipt-data": receipt_data,
        "exclude-old-transactions": True
    }
    
    if password:
        payload["password"] = password
    
    try:
        logger.info(f"🔍 向 Apple 验证收据: url={url}, sandbox={use_sandbox}")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ Apple 验证响应: status={result.get('status')}")
        
        # 检查状态码
        status = result.get('status', 0)
        if status == 21007:
            # 21007 表示收据是沙盒收据，但我们在生产环境验证
            raise AppleSubscriptionError("21007: 收据是沙盒收据")
        elif status == 21008:
            # 21008 表示收据是生产收据，但我们在沙盒环境验证
            raise AppleSubscriptionError("21008: 收据是生产收据")
        elif status != 0:
            # 其他错误状态码
            raise AppleSubscriptionError(f"Apple 验证失败: status={status}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Apple 验证请求失败: {e}")
        raise AppleSubscriptionError(f"Apple 验证请求失败: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Apple 验证响应解析失败: {e}")
        raise AppleSubscriptionError(f"Apple 验证响应解析失败: {e}")

def parse_subscription_info(apple_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 Apple 验证响应中的订阅信息
    
    Args:
        apple_response: Apple 服务器返回的验证结果
        
    Returns:
        解析后的订阅信息字典
    """
    status = apple_response.get("status", -1)
    
    # Apple 状态码说明
    if status == 0:
        # 验证成功
        pass
    elif status == 21007:
        # 收据是沙盒收据，但发送到了生产环境
        raise AppleSubscriptionError("收据是沙盒收据，请使用沙盒环境验证")
    elif status == 21008:
        # 收据是生产收据，但发送到了沙盒环境
        raise AppleSubscriptionError("收据是生产收据，请使用生产环境验证")
    else:
        # 其他错误
        error_messages = {
            21000: "App Store 无法读取收据数据",
            21002: "收据数据格式错误",
            21003: "收据验证失败",
            21004: "共享密钥不匹配",
            21005: "收据服务器暂时不可用",
            21006: "收据有效但订阅已过期",
            21010: "收据无法被授权"
        }
        error_msg = error_messages.get(status, f"未知错误 (状态码: {status})")
        raise AppleSubscriptionError(f"Apple 验证失败: {error_msg}")
    
    receipt = apple_response.get("receipt", {})
    latest_receipt_info = apple_response.get("latest_receipt_info", [])
    
    if not latest_receipt_info:
        raise AppleSubscriptionError("收据中没有找到订阅信息")
    
    # 获取最新的订阅信息（通常是最后一个）
    latest_subscription = latest_receipt_info[-1]
    
    # 解析订阅信息
    subscription_info = {
        "product_id": latest_subscription.get("product_id"),
        "transaction_id": latest_subscription.get("transaction_id"),
        "original_transaction_id": latest_subscription.get("original_transaction_id"),
        "expires_date_ms": latest_subscription.get("expires_date_ms"),
        "expires_date": latest_subscription.get("expires_date"),
        "is_trial_period": latest_subscription.get("is_trial_period", "false") == "true",
        "is_in_intro_offer_period": latest_subscription.get("is_in_intro_offer_period", "false") == "true",
        "auto_renew_status": latest_subscription.get("auto_renew_status", "0") == "1",
        "environment": apple_response.get("environment", "Sandbox")
    }
    
    # 转换到期时间
    if subscription_info["expires_date_ms"]:
        expires_timestamp = int(subscription_info["expires_date_ms"]) / 1000
        subscription_info["expires_at"] = datetime.fromtimestamp(expires_timestamp, tz=timezone.utc)
    else:
        subscription_info["expires_at"] = None
    
    # 判断订阅状态
    now = datetime.now(timezone.utc)
    if subscription_info["expires_at"] and subscription_info["expires_at"] > now:
        subscription_info["status"] = SUBSCRIPTION_STATUS_ACTIVE
    else:
        subscription_info["status"] = SUBSCRIPTION_STATUS_EXPIRED
    
    logger.info(f"📋 解析订阅信息: product_id={subscription_info['product_id']}, "
                f"status={subscription_info['status']}, expires_at={subscription_info['expires_at']}")
    
    return subscription_info

def update_user_subscription(db: Session, user_id: int, subscription_info: Dict[str, Any], 
                           receipt_data: str, environment: str = "sandbox") -> User:
    """
    更新用户订阅信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        subscription_info: 解析后的订阅信息
        receipt_data: 原始收据数据
        environment: 订阅环境
        
    Returns:
        更新后的用户对象
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppleSubscriptionError("用户不存在")
    
    # 更新订阅信息
    user.subscription_status = subscription_info["status"]
    user.subscription_product_id = subscription_info["product_id"]
    user.subscription_expires_at = subscription_info["expires_at"]
    user.original_transaction_id = subscription_info["original_transaction_id"]
    user.latest_receipt = receipt_data
    user.auto_renew_status = subscription_info["auto_renew_status"]
    user.subscription_environment = environment
    
    # 注意：不再需要同步更新 is_member 和 membership_expires_at 字段
    # 这些字段已被删除，统一使用订阅字段管理
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ 用户订阅信息已更新: user_id={user_id}, status={user.subscription_status}")
    
    return user

def get_user_subscription_status(db: Session, user_id: int) -> Dict[str, Any]:
    """
    获取用户订阅状态
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户订阅状态信息
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppleSubscriptionError("用户不存在")
    
    # 检查订阅是否过期
    now = datetime.now(timezone.utc)
    if (user.subscription_expires_at and 
        user.subscription_status == SUBSCRIPTION_STATUS_ACTIVE and 
        user.subscription_expires_at <= now):
        # 订阅已过期，更新状态
        user.subscription_status = SUBSCRIPTION_STATUS_EXPIRED
        db.commit()
        db.refresh(user)
    
    return {
        "subscription_status": user.subscription_status,
        "subscription_product_id": user.subscription_product_id,
        "subscription_expires_at": user.subscription_expires_at,
        "auto_renew_status": user.auto_renew_status,
        "subscription_environment": user.subscription_environment,
        "is_member": user.subscription_status == SUBSCRIPTION_STATUS_ACTIVE  # 使用订阅状态判断是否为会员
    }

def handle_apple_webhook_notification(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理 Apple 服务器通知
    
    Args:
        notification_data: Apple 发送的通知数据
        
    Returns:
        处理结果
    """
    notification_type = notification_data.get("notification_type")
    data = notification_data.get("data", {})
    
    logger.info(f"📨 收到 Apple 通知: type={notification_type}")
    
    # 根据通知类型处理
    if notification_type == "SUBSCRIBED":
        # 新订阅
        logger.info("🆕 新订阅通知")
    elif notification_type == "DID_RENEW":
        # 订阅续费
        logger.info("🔄 订阅续费通知")
    elif notification_type == "DID_FAIL_TO_RENEW":
        # 续费失败
        logger.info("❌ 续费失败通知")
    elif notification_type == "DID_CANCEL":
        # 订阅取消
        logger.info("🚫 订阅取消通知")
    elif notification_type == "EXPIRED":
        # 订阅过期
        logger.info("⏰ 订阅过期通知")
    else:
        logger.warning(f"⚠️ 未知通知类型: {notification_type}")
    
    return {
        "status": "success",
        "message": f"通知处理完成: {notification_type}"
    }
