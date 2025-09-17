# File: test_subscription_api.py
# 功能：测试 Apple 订阅 API 接口
# 使用方法：python test_subscription_api.py

import requests
import json
import base64
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
TEST_RECEIPT = "test_receipt_data"  # 这里应该是真实的 Base64 收据数据
test_jwt_token = None  # 测试JWT token

def test_subscription_apis():
    """测试订阅相关 API"""
    
    print("🧪 开始测试 Apple 订阅 API...")
    
    # 注意：这些测试需要有效的 JWT token 和真实的收据数据
    # 这里只是展示 API 调用方式

def test_auth_apis():
    """测试认证相关 API"""
    
    print("🧪 开始测试认证 API...")
    
    # 测试登录接口
    print("\n1️⃣ 测试登录接口...")
    test_login_data = {
        "username": "review@test.com",
        "password": "Review1234!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/test",
            json=test_login_data,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 如果登录成功，保存JWT token用于后续测试
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                global test_jwt_token
                test_jwt_token = data.get("jwt")
                print(f"   ✅ 获取到JWT token: {test_jwt_token[:20]}...")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

def test_subscription_apis_with_auth():
    """使用认证测试订阅相关 API"""
    
    print("🧪 开始测试需要认证的订阅 API...")
    
    # 先获取测试JWT token
    test_auth_apis()
    
    if not test_jwt_token:
        print("❌ 无法获取JWT token，跳过需要认证的测试")
        return
    
    headers = {
        "Authorization": f"Bearer {test_jwt_token}",
        "Content-Type": "application/json"
    }
    
    # 1. 测试订阅验证接口
    print("\n1️⃣ 测试订阅验证接口...")
    verify_data = {
        "receipt_data": base64.b64encode(TEST_RECEIPT.encode()).decode(),
        "password": "your_shared_secret"  # 可选
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/subscription/verify",
            headers=headers,
            json=verify_data,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 2. 测试订阅状态查询接口
    print("\n2️⃣ 测试订阅状态查询接口...")
    try:
        response = requests.get(
            f"{BASE_URL}/subscription/status",
            headers=headers,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 3. 测试订阅刷新接口
    print("\n3️⃣ 测试订阅刷新接口...")
    try:
        response = requests.post(
            f"{BASE_URL}/subscription/refresh",
            headers=headers,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 4. 测试获取订阅产品列表接口
    print("\n4️⃣ 测试获取订阅产品列表接口...")
    try:
        response = requests.get(
            f"{BASE_URL}/subscription/products",
            headers=headers,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 5. 测试订阅恢复接口
    print("\n5️⃣ 测试订阅恢复接口...")
    try:
        response = requests.post(
            f"{BASE_URL}/subscription/restore",
            headers=headers,
            json=verify_data,  # 使用相同的收据数据
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 6. 测试 Apple 服务器通知接口
    print("\n6️⃣ 测试 Apple 服务器通知接口...")
    webhook_data = {
        "notification_type": "DID_RENEW",
        "subtype": None,
        "notification_uuid": "12345678-1234-1234-1234-123456789012",
        "data": {
            "app_apple_id": 123456789,
            "bundle_id": "com.yourapp",
            "environment": "Sandbox",
            "signed_transaction_info": "test_transaction_info",
            "signed_renewal_info": "test_renewal_info"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/subscription/webhook",
            json=webhook_data,
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n✅ 测试完成！")
    print("\n📝 注意事项：")
    print("   - 需要先启动服务: uvicorn main:app --host 0.0.0.0 --port 8000")
    print("   - 需要有效的 JWT token 进行认证")
    print("   - 需要真实的 Apple 收据数据进行验证")

def show_api_endpoints():
    """显示所有订阅相关的 API 端点"""
    
    print("\n📋 Apple 订阅 API 端点列表：")
    print("=" * 50)
    
    endpoints = [
        {
            "method": "POST",
            "path": "/auth/test",
            "description": "测试登录接口（Apple测试人员专用）",
            "auth": "无需认证"
        },
        {
            "method": "POST",
            "path": "/subscription/verify",
            "description": "验证 Apple 订阅收据",
            "auth": "需要 JWT token"
        },
        {
            "method": "GET", 
            "path": "/subscription/status",
            "description": "查询用户订阅状态",
            "auth": "需要 JWT token"
        },
        {
            "method": "POST",
            "path": "/subscription/refresh", 
            "description": "刷新用户订阅状态",
            "auth": "需要 JWT token"
        },
        {
            "method": "GET",
            "path": "/subscription/products",
            "description": "获取订阅产品列表",
            "auth": "需要 JWT token"
        },
        {
            "method": "POST",
            "path": "/subscription/restore",
            "description": "恢复订阅购买",
            "auth": "需要 JWT token"
        },
        {
            "method": "POST",
            "path": "/subscription/webhook",
            "description": "处理 Apple 服务器通知",
            "auth": "无需认证（Apple 服务器调用）"
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n{endpoint['method']} {endpoint['path']}")
        print(f"   描述: {endpoint['description']}")
        print(f"   认证: {endpoint['auth']}")

if __name__ == "__main__":
    show_api_endpoints()
    test_auth_apis()
    test_subscription_apis_with_auth()

