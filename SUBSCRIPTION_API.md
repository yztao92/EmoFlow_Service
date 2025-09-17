# Apple 订阅 API 文档

## 概述

本文档描述了 EmoFlow 服务中 Apple 订阅相关的 API 接口。这些接口用于处理 iOS 应用的 App Store 订阅验证、状态管理和服务器通知。

## 环境配置

- **沙盒环境**: 用于开发和测试
- **生产环境**: 用于正式发布

## API 接口

### 1. 验证订阅收据

**接口**: `POST /subscription/verify`

**描述**: 验证 iOS 应用发送的 App Store 收据，并更新用户订阅状态。

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**请求体**:
```json
{
    "receipt_data": "base64_encoded_receipt_data",
    "password": "your_app_shared_secret"  // 可选
}
```

**响应示例**:
```json
{
    "status": "success",
    "message": "订阅验证成功",
    "subscription": {
        "status": "active",
        "product_id": "com.yourapp.monthly",
        "expires_at": "2024-02-01T00:00:00Z",
        "auto_renew": true,
        "environment": "sandbox",
        "is_member": true
    }
}
```

**错误响应**:
```json
{
    "detail": "Apple 验证失败: 收据数据格式错误"
}
```

### 2. 查询订阅状态

**接口**: `GET /subscription/status`

**描述**: 获取用户当前的订阅状态信息。

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
```

**响应示例**:
```json
{
    "status": "success",
    "subscription": {
        "subscription_status": "active",
        "subscription_product_id": "com.yourapp.monthly",
        "subscription_expires_at": "2024-02-01T00:00:00Z",
        "auto_renew_status": true,
        "subscription_environment": "sandbox",
        "is_member": true
    }
}
```

### 3. 刷新订阅状态

**接口**: `POST /subscription/refresh`

**描述**: 重新验证用户的最新收据，刷新订阅状态。

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
```

**响应示例**:
```json
{
    "status": "success",
    "message": "订阅状态刷新成功",
    "subscription": {
        "status": "active",
        "product_id": "com.yourapp.monthly",
        "expires_at": "2024-02-01T00:00:00Z",
        "auto_renew": true,
        "environment": "sandbox",
        "is_member": true
    }
}
```

### 4. 获取订阅产品列表

**接口**: `GET /subscription/products`

**描述**: 获取可用的订阅产品列表，用于前端展示购买选项。

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
```

**响应示例**:
```json
{
    "status": "success",
    "message": "获取产品列表成功",
    "products": [
        {
            "id": "monthly",
            "name": "包月",
            "price": "¥12",
            "daily_price": "仅需¥0.40/天",
            "period": "monthly",
            "period_display": "每月",
            "apple_product_id": "com.yztao92.EmoFlow.subscription.monthly",
            "is_popular": false,
            "sort_order": 1
        },
        {
            "id": "yearly",
            "name": "包年",
            "price": "¥98.00",
            "daily_price": "仅需¥0.27/天",
            "period": "yearly",
            "period_display": "每年",
            "apple_product_id": "com.yztao92.EmoFlow.subscription.yearly",
            "is_popular": true,
            "sort_order": 2
        }
    ]
}
```

### 5. 恢复订阅购买

**接口**: `POST /subscription/restore`

**描述**: 恢复用户之前的订阅购买，用于用户重新安装应用后恢复订阅状态。

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**请求体**:
```json
{
    "receipt_data": "base64_encoded_receipt_data",
    "password": "your_app_shared_secret"  // 可选
}
```

**响应示例**:
```json
{
    "status": "success",
    "message": "恢复购买成功",
    "subscription": {
        "status": "active",
        "expires_at": "2024-02-15T10:30:00Z",
        "product_id": "monthly",
        "auto_renew": true,
        "environment": "sandbox",
        "is_member": true
    }
}
```

**错误响应**:
```json
{
    "detail": "Apple 验证失败: 收据数据格式错误"
}
```

### 6. Apple 服务器通知

**接口**: `POST /subscription/webhook`

**描述**: 接收 Apple 服务器发送的订阅状态变化通知。

**注意**: 此接口不需要用户认证，由 Apple 服务器直接调用。

**请求体**:
```json
{
    "notification_type": "DID_RENEW",
    "subtype": null,
    "notification_uuid": "12345678-1234-1234-1234-123456789012",
    "data": {
        "app_apple_id": 123456789,
        "bundle_id": "com.yourapp",
        "environment": "Sandbox",
        "signed_transaction_info": "...",
        "signed_renewal_info": "..."
    }
}
```

**响应示例**:
```json
{
    "status": "success",
    "message": "通知处理完成"
}
```

## 订阅状态说明

| 状态 | 描述 |
|------|------|
| `active` | 订阅有效 |
| `expired` | 订阅已过期 |
| `cancelled` | 订阅已取消 |
| `inactive` | 无订阅 |

## 错误处理

### 常见错误码

| HTTP 状态码 | 描述 |
|-------------|------|
| 400 | 请求参数错误或 Apple 验证失败 |
| 401 | 用户未认证 |
| 404 | 用户不存在 |
| 500 | 服务器内部错误 |

### Apple 验证错误

| 状态码 | 描述 |
|--------|------|
| 21000 | App Store 无法读取收据数据 |
| 21002 | 收据数据格式错误 |
| 21003 | 收据验证失败 |
| 21004 | 共享密钥不匹配 |
| 21005 | 收据服务器暂时不可用 |
| 21006 | 收据有效但订阅已过期 |
| 21007 | 收据是沙盒收据，但发送到了生产环境 |
| 21008 | 收据是生产收据，但发送到了沙盒环境 |
| 21010 | 收据无法被授权 |

## 使用流程

### iOS 端集成流程

1. **用户购买订阅**
   ```swift
   // 使用 StoreKit 购买订阅
   let product = products.first!
   let payment = SKPayment(product: product)
   SKPaymentQueue.default().add(payment)
   ```

2. **获取收据**
   ```swift
   // 获取 App Store 收据
   guard let receiptURL = Bundle.main.appStoreReceiptURL,
         let receiptData = try? Data(contentsOf: receiptURL) else {
       return
   }
   let receiptString = receiptData.base64EncodedString()
   ```

3. **发送到后端验证**
   ```swift
   // 发送收据到后端验证
   let request = SubscriptionVerifyRequest(
       receipt_data: receiptString,
       password: "your_shared_secret"
   )
   // 调用 POST /subscription/verify
   ```

4. **处理响应**
   ```swift
   // 根据响应更新 UI
   if response.subscription.status == "active" {
       // 用户有有效订阅
       enablePremiumFeatures()
   }
   ```

### 后端处理流程

1. **接收收据验证请求**
2. **向 Apple 服务器验证收据**
3. **解析订阅信息**
4. **更新用户订阅状态**
5. **返回验证结果**

## 安全注意事项

1. **收据验证**: 必须在服务器端验证收据，不能仅依赖客户端数据
2. **HTTPS**: 所有通信必须使用 HTTPS
3. **共享密钥**: 妥善保管 App Store Connect 的共享密钥
4. **日志记录**: 记录所有订阅相关的操作日志
5. **错误处理**: 妥善处理各种异常情况

## 测试

### 沙盒测试

1. 在 App Store Connect 中创建沙盒测试用户
2. 在 iOS 设备上使用沙盒账户登录
3. 使用沙盒环境进行订阅测试

### 测试用例

1. **正常订阅流程**
   - 购买订阅
   - 验证收据
   - 检查订阅状态

2. **订阅过期**
   - 等待订阅过期
   - 验证状态更新

3. **订阅取消**
   - 取消订阅
   - 验证状态更新

4. **网络异常**
   - 模拟网络错误
   - 验证重试机制

## 部署说明

1. **数据库迁移**: 运行 `python database/migrate_add_subscription.py`
2. **环境变量**: 确保所有必要的环境变量已设置
3. **HTTPS**: 确保服务器支持 HTTPS
4. **监控**: 设置订阅相关的监控和告警

## 支持

如有问题，请查看日志文件或联系开发团队。

