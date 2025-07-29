# EmoFlow API 文档

## 概述

EmoFlow 是一个基于 FastAPI 的情绪日记服务，提供 Apple 登录认证、智能聊天对话和心情日记管理功能。

**基础URL**: `http://localhost:8000`  
**API版本**: v1  
**认证方式**: JWT Token (Header: `Authorization`)

---

## 目录

- [认证模块](#认证模块)
- [聊天模块](#聊天模块)
- [日记模块](#日记模块)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [示例代码](#示例代码)

---

## 认证模块

### Apple 登录

**POST** `/auth/apple`

使用 Apple ID 进行用户认证和登录。

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `identity_token` | string | ✅ | Apple 身份令牌 |
| `full_name` | string | ❌ | 用户姓名 |
| `email` | string | ❌ | 用户邮箱 |

#### 请求示例

```json
{
  "identity_token": "eyJraWQiOiI4NkQ4...",
  "full_name": "张三",
  "email": "zhangsan@example.com"
}
```

#### 响应示例

```json
{
  "status": "ok",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": 123,
  "email": "zhangsan@example.com",
  "name": "张三"
}
```

#### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | 状态标识 ("ok") |
| `token` | string | JWT 访问令牌 |
| `user_id` | integer | 用户ID |
| `email` | string | 用户邮箱 |
| `name` | string | 用户姓名 |

#### 错误响应

```json
{
  "detail": "Apple 登录验证失败"
}
```

---

## 聊天模块

### 智能对话

**POST** `/chat`

与 AI 助手进行智能对话，支持情绪检测和上下文理解。

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `session_id` | string | ✅ | 对话会话ID |
| `messages` | array | ✅ | 对话消息列表 |
| `emotion` | string | ❌ | 用户情绪标识 |

#### 消息格式

```json
{
  "role": "user|assistant",
  "content": "消息内容"
}
```

#### 请求示例

```json
{
  "session_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "我今天心情不太好"
    },
    {
      "role": "assistant", 
      "content": "我理解你的感受，能告诉我发生了什么吗？"
    },
    {
      "role": "user",
      "content": "工作上遇到了一些困难"
    }
  ],
  "emotion": "sad"
}
```

#### 响应示例

```json
{
  "response": {
    "answer": "我理解工作上的困难确实会让人感到压力。让我们一起分析一下具体的情况，也许能找到解决方案。",
    "references": []
  }
}
```

#### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `response.answer` | string | AI 助手的回复 |
| `response.references` | array | 参考信息（预留） |

---

## 日记模块

### 生成心情日记

**POST** `/journal/generate`

基于对话内容自动生成心情日记。

**需要认证**: ✅ (JWT Token)

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `session_id` | string | ✅ | 对话会话ID |
| `messages` | array | ✅ | 对话消息列表 |
| `emotion` | string | ❌ | 用户情绪标识 |

#### 请求示例

```json
{
  "session_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "我今天心情不太好"
    },
    {
      "role": "assistant",
      "content": "我理解你的感受，能告诉我发生了什么吗？"
    }
  ],
  "emotion": "sad"
}
```

#### 响应示例

```json
{
  "journal": "今天的心情确实有些低落，工作上遇到了一些挑战。虽然感到压力，但通过和朋友的交流，心情稍微好了一些。",
  "title": "工作压力的一天",
  "journal_id": 456,
  "emotion": "sad",
  "status": "success"
}
```

#### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `journal` | string | 生成的日记内容 |
| `title` | string | 日记标题 |
| `journal_id` | integer | 日记ID |
| `emotion` | string | 情绪标识 |
| `status` | string | 生成状态 |

### 获取日记列表

**GET** `/journal/list`

获取当前用户的日记列表。

**需要认证**: ✅ (JWT Token)

#### 查询参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `limit` | integer | 20 | 每页数量 |
| `offset` | integer | 0 | 偏移量 |

#### 请求示例

```bash
GET /journal/list?limit=10&offset=0
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 响应示例

```json
{
  "status": "success",
  "journals": [
    {
      "id": 456,
      "title": "工作压力的一天",
      "content": "今天的心情确实有些低落...",
      "messages": [
        {
          "role": "user",
          "content": "我今天心情不太好"
        }
      ],
      "session_id": "session_123",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

#### 响应字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | 请求状态 |
| `journals` | array | 日记列表 |
| `total` | integer | 总数量 |
| `limit` | integer | 每页数量 |
| `offset` | integer | 偏移量 |

### 获取日记详情

**GET** `/journal/{journal_id}`

获取特定日记的详细信息。

**需要认证**: ✅ (JWT Token)

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `journal_id` | integer | 日记ID |

#### 请求示例

```bash
GET /journal/456
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 响应示例

```json
{
  "status": "success",
  "journal": {
    "id": 456,
    "title": "工作压力的一天",
    "content": "今天的心情确实有些低落...",
    "messages": [
      {
        "role": "user",
        "content": "我今天心情不太好"
      }
    ],
    "session_id": "session_123",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

### 删除日记

**DELETE** `/journal/{journal_id}`

删除指定的日记。

**需要认证**: ✅ (JWT Token)

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `journal_id` | integer | 日记ID |

#### 请求示例

```bash
DELETE /journal/456
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 响应示例

```json
{
  "status": "success",
  "message": "日记删除成功"
}
```

---

## 数据模型

### User 用户模型

```json
{
  "id": 123,
  "apple_user_id": "001234.567890abcdef.1234",
  "email": "user@example.com",
  "name": "张三"
}
```

### Journal 日记模型

```json
{
  "id": 456,
  "user_id": 123,
  "title": "工作压力的一天",
  "content": "今天的心情确实有些低落...",
  "messages": "[{\"role\":\"user\",\"content\":\"我今天心情不太好\"}]",
  "session_id": "session_123",
  "emotion": "sad",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### Message 消息模型

```json
{
  "role": "user|assistant",
  "content": "消息内容"
}
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token 无效或过期） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误

| 错误类型 | 状态码 | 描述 |
|----------|--------|------|
| `Apple 登录验证失败` | 401 | Apple 身份验证失败 |
| `无效或过期的 Token` | 401 | JWT Token 无效或已过期 |
| `日记不存在` | 404 | 指定的日记不存在 |
| `获取日记详情失败` | 500 | 服务器内部错误 |

---

## 示例代码

### JavaScript/TypeScript

```javascript
// 配置基础URL和Token
const API_BASE = 'http://localhost:8000';
const token = 'your-jwt-token';

// Apple 登录
async function appleLogin(identityToken, fullName, email) {
  const response = await fetch(`${API_BASE}/auth/apple`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      identity_token: identityToken,
      full_name: fullName,
      email: email
    })
  });
  return response.json();
}

// 聊天对话
async function chat(sessionId, messages, emotion) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      messages: messages,
      emotion: emotion
    })
  });
  return response.json();
}

// 生成日记
async function generateJournal(sessionId, messages, emotion) {
  const response = await fetch(`${API_BASE}/journal/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: sessionId,
      messages: messages,
      emotion: emotion
    })
  });
  return response.json();
}

// 获取日记列表
async function getJournals(limit = 20, offset = 0) {
  const response = await fetch(`${API_BASE}/journal/list?limit=${limit}&offset=${offset}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// 获取日记详情
async function getJournalDetail(journalId) {
  const response = await fetch(`${API_BASE}/journal/${journalId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// 删除日记
async function deleteJournal(journalId) {
  const response = await fetch(`${API_BASE}/journal/${journalId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

### Python

```python
import requests

API_BASE = 'http://localhost:8000'
token = 'your-jwt-token'

# Apple 登录
def apple_login(identity_token, full_name=None, email=None):
    response = requests.post(f'{API_BASE}/auth/apple', json={
        'identity_token': identity_token,
        'full_name': full_name,
        'email': email
    })
    return response.json()

# 聊天对话
def chat(session_id, messages, emotion=None):
    response = requests.post(f'{API_BASE}/chat', json={
        'session_id': session_id,
        'messages': messages,
        'emotion': emotion
    })
    return response.json()

# 生成日记
def generate_journal(session_id, messages, emotion=None):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(f'{API_BASE}/journal/generate', 
                           json={
                               'session_id': session_id,
                               'messages': messages,
                               'emotion': emotion
                           },
                           headers=headers)
    return response.json()

# 获取日记列表
def get_journals(limit=20, offset=0):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{API_BASE}/journal/list?limit={limit}&offset={offset}',
                          headers=headers)
    return response.json()

# 获取日记详情
def get_journal_detail(journal_id):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{API_BASE}/journal/{journal_id}',
                          headers=headers)
    return response.json()

# 删除日记
def delete_journal(journal_id):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(f'{API_BASE}/journal/{journal_id}',
                             headers=headers)
    return response.json()
```

### cURL

```bash
# Apple 登录
curl -X POST http://localhost:8000/auth/apple \
  -H "Content-Type: application/json" \
  -d '{
    "identity_token": "your-apple-token",
    "full_name": "张三",
    "email": "zhangsan@example.com"
  }'

# 聊天对话
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_123",
    "messages": [
      {"role": "user", "content": "我今天心情不太好"}
    ],
    "emotion": "sad"
  }'

# 生成日记
curl -X POST http://localhost:8000/journal/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "session_id": "session_123",
    "messages": [
      {"role": "user", "content": "我今天心情不太好"}
    ],
    "emotion": "sad"
  }'

# 获取日记列表
curl -X GET "http://localhost:8000/journal/list?limit=10&offset=0" \
  -H "Authorization: Bearer your-jwt-token"

# 获取日记详情
curl -X GET http://localhost:8000/journal/456 \
  -H "Authorization: Bearer your-jwt-token"

# 删除日记
curl -X DELETE http://localhost:8000/journal/456 \
  -H "Authorization: Bearer your-jwt-token"
```

---

## 注意事项

1. **认证**: 除了 `/auth/apple` 和 `/chat` 接口，其他接口都需要在请求头中携带有效的 JWT Token
2. **会话管理**: 聊天功能使用 `session_id` 来维护对话上下文
3. **情绪检测**: 系统会自动检测用户消息中的情绪，也可以通过 `emotion` 参数手动指定
4. **数据存储**: 日记数据会永久保存在数据库中，包含完整的对话历史
5. **错误处理**: 所有接口都有完善的错误处理机制，会返回相应的 HTTP 状态码和错误信息

---

## 更新日志

- **v1.0.0**: 初始版本，支持 Apple 登录、聊天对话和日记管理
- **v1.1.0**: 新增情绪检测功能
- **v1.2.0**: 优化日记生成算法，支持对话历史存储 