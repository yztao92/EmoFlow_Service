# Heart 功能说明文档

## 功能概述

Heart（心数）是用户系统中的一个新字段，用于跟踪用户的状态。每个用户注册时默认获得100个heart值，每天凌晨12点自动重置为100。

### 心心消耗规则

- **聊天功能**: 每次调用 `chat` API 消耗 2 个心心
- **AI生成日记**: 每次调用 `journal/generate` API 消耗 4 个心心
- **其他功能**: 不消耗心心值

## 数据库结构

### 用户表 (users) 新增字段

```sql
ALTER TABLE users ADD COLUMN heart INTEGER DEFAULT 100 NOT NULL;
```

- **字段名**: `heart`
- **类型**: `INTEGER`
- **默认值**: `100`
- **约束**: `NOT NULL`

## API 接口

### 1. 获取用户心数

**接口**: `GET /user/heart`

**功能**: 获取当前登录用户的心数值

**请求头**: 
```
Authorization: Bearer <JWT_TOKEN>
```

**响应示例**:
```json
{
    "status": "ok",
    "user": {
        "id": 1,
        "heart": 100
    }
}
```

### 2. 聊天接口（消耗2个心心）

**接口**: `POST /chat`

**功能**: 用户与AI进行对话，每次调用消耗2个心心值

**请求头**: 
```
Authorization: Bearer <JWT_TOKEN>
```

**请求体**:
```json
{
    "session_id": "unique_session_id",
    "messages": [
        {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "emotion": "happy"
}
```

**响应示例**:
```json
{
    "response": {
        "answer": "你好！我是EmoFlow情绪陪伴助手...",
        "references": [],
        "user_heart": 18
    }
}
```

**注意事项**:
- 需要有效的JWT token进行认证
- 每次调用消耗2个心心值
- 如果心心值不足，会返回403错误
- 返回用户剩余的心心值

### 3. AI生成日记接口（消耗4个心心）

**接口**: `POST /journal/generate`

**功能**: 根据对话历史生成个人心情总结，每次调用消耗4个心心值

**请求头**: 
```
Authorization: Bearer <JWT_TOKEN>
```

**请求体**:
```json
{
    "session_id": "unique_session_id",
    "messages": [
        {"role": "user", "content": "今天心情不错"},
        {"role": "assistant", "content": "那很好啊！"}
    ],
    "emotion": "happy"
}
```

**响应示例**:
```json
{
    "journal": "今天的心情真的很不错...",
    "content_html": "<p>今天的心情真的很不错...</p>",
    "content_plain": "今天的心情真的很不错...",
    "content_format": "html",
    "is_safe": true,
    "title": "今日心情",
    "journal_id": 123,
    "emotion": "happy",
    "status": "success",
    "user_heart": 16
}
```

**注意事项**:
- 需要有效的JWT token进行认证
- 每次调用消耗4个心心值
- 如果心心值不足，会返回403错误
- 返回用户剩余的心心值

### 4. 更新用户心数

**接口**: `PUT /user/heart`

**功能**: 更新当前登录用户的心数值

**请求头**: 
```
Authorization: Bearer <JWT_TOKEN>
```

**请求体**:
```json
{
    "heart": 25
}
```

**响应示例**:
```json
{
    "status": "ok",
    "message": "心数更新成功",
    "user": {
        "id": 1,
        "heart": 25
    }
}
```

### 5. 获取用户资料（已更新）

**接口**: `GET /user/profile`

**功能**: 获取当前登录用户的完整资料信息（包含heart值）

**响应示例**:
```json
{
    "status": "ok",
    "user": {
        "id": 1,
        "name": "振涛",
        "email": "yztao92@gmail.com",
        "heart": 100
    }
}
```

### 6. 测试接口（仅开发环境）

**接口**: `POST /admin/test-heart-reset`

**功能**: 手动触发heart重置任务，用于测试定时任务功能

**响应示例**:
```json
{
    "status": "ok",
    "message": "测试heart重置任务执行成功",
    "timestamp": "2025-08-12T10:21:52.672000"
}
```

## 定时任务

### 自动重置功能

- **执行时间**: 每天凌晨00:00（午夜12点）
- **执行内容**: 将所有用户的heart值重置为100
- **实现方式**: 使用APScheduler库的Cron触发器
- **日志记录**: 详细记录执行过程和结果

### 定时任务配置

```python
scheduler.add_job(
    func=reset_all_users_heart,
    trigger=CronTrigger(hour=0, minute=0),  # 每天凌晨00:00执行
    id="heart_reset_job",
    name="每日重置用户heart值",
    replace_existing=True
)
```

## 技术实现

### 依赖库

- `apscheduler`: 定时任务调度器
- `sqlalchemy`: 数据库ORM操作

### 核心函数

1. **`reset_all_users_heart()`**: 执行heart重置的核心函数
2. **`start_heart_reset_scheduler()`**: 启动定时任务调度器
3. **`on_startup()`**: 应用启动时初始化定时任务
4. **`on_shutdown()`**: 应用关闭时清理定时任务

### 数据库操作

```python
# 重置所有用户的heart值为100
db.query(User).update({"heart": 100})
db.commit()
```

## 使用场景

1. **用户注册**: 新用户自动获得100个heart值
2. **日常重置**: 每天凌晨自动重置，确保用户每天都有足够的heart值
3. **游戏化元素**: 可用于各种功能消耗，如发送消息、创建日记等
4. **用户激励**: 通过heart值的变化来激励用户参与

## 注意事项

1. **权限控制**: 只有登录用户才能查看和修改自己的heart值
2. **数据验证**: heart值不能为负数
3. **事务安全**: 使用数据库事务确保数据一致性
4. **错误处理**: 完善的异常处理和日志记录
5. **性能考虑**: 批量更新操作，避免逐个用户更新

## 部署说明

### 环境要求

- Python 3.7+
- APScheduler 3.11.0+
- SQLite 3.x

### 安装依赖

```bash
pip install apscheduler
```

### 启动应用

```bash
python main.py
```

应用启动时会自动：
1. 初始化数据库
2. 启动定时任务调度器
3. 配置每天凌晨00:00的heart重置任务

## 监控和日志

### 日志级别

- **INFO**: 正常操作日志
- **WARNING**: 警告信息
- **ERROR**: 错误信息

### 关键日志

- 定时任务启动成功
- 定时任务执行开始
- 定时任务执行结果
- 用户heart值更新操作

## 故障排除

### 常见问题

1. **定时任务未启动**: 检查APScheduler是否正确安装
2. **数据库连接失败**: 检查数据库文件权限和路径
3. **heart值未重置**: 检查定时任务日志和数据库连接

### 调试方法

1. 使用测试接口手动触发重置
2. 查看应用日志输出
3. 检查数据库中的heart字段值
4. 验证定时任务调度器状态
