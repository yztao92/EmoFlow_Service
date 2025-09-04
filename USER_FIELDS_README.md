# 用户字段扩展说明

## 新增字段

为User模型添加了以下三个新字段：

### 1. `is_member` (Boolean)
- **类型**: Boolean
- **默认值**: False
- **说明**: 标识用户是否为会员
- **用途**: 可以用于会员特权、付费功能等

### 2. `birthday` (Date)
- **类型**: Date
- **默认值**: NULL (可为空)
- **说明**: 用户生日
- **用途**: 生日提醒、个性化服务、年龄相关功能

### 3. `memory_points` (Text)
- **类型**: Text
- **默认值**: NULL (可为空)
- **说明**: 记忆点，存储用户的重要信息
- **用途**: 用户偏好、重要事件记录、个性化推荐等

### 4. `membership_expires_at` (DateTime)
- **类型**: DateTime
- **默认值**: NULL (可为空)
- **说明**: 会员过期时间
- **用途**: 会员状态管理、过期提醒、自动续费等

## 数据库迁移

### 运行迁移脚本
```bash
python database_migration.py
```

迁移脚本会：
1. 自动备份现有数据库
2. 为users表添加新字段
3. 显示迁移结果和当前表结构

### 手动SQL迁移（可选）
```sql
ALTER TABLE users ADD COLUMN is_member BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN birthday DATE;
ALTER TABLE users ADD COLUMN memory_points TEXT;
```

## API使用

### 更新用户资料
```http
PUT /user/profile
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "新姓名",
  "email": "new@email.com",
  "is_member": true,
  "birthday": "1990-01-01",
  "memory_points": "喜欢安静的环境，对音乐有特殊偏好",
  "membership_expires_at": "2024-12-31T23:59:59"
}
```

### 获取用户资料
```http
GET /user/profile
Authorization: Bearer <jwt_token>
```

响应示例：
```json
{
  "status": "ok",
  "user": {
    "id": 1,
    "name": "用户名",
    "email": "user@email.com",
    "heart": 100,
    "is_member": false,
    "birthday": "1990-01-01",
    "memory_points": "喜欢安静的环境，对音乐有特殊偏好",
    "membership_expires_at": "2024-12-31T23:59:59"
  }
}
```

## 字段说明

### `is_member`
- 布尔值，表示用户会员状态
- 可用于控制功能访问权限
- 建议在业务逻辑中检查此字段

### `birthday`
- 日期格式：YYYY-MM-DD
- 可用于计算年龄、生日提醒等
- 注意处理时区问题

### `memory_points`
- 文本字段，可存储任意长度的信息
- 建议使用结构化格式（如JSON字符串）
- 可用于AI个性化服务

### `membership_expires_at`
- 日期时间格式：ISO 8601标准（如"2024-12-31T23:59:59"）
- 用于判断会员是否过期
- 建议在业务逻辑中检查此字段

## 注意事项

1. **数据备份**: 迁移前会自动备份数据库
2. **向后兼容**: 新字段都是可选的，不影响现有功能
3. **性能考虑**: 新字段会占用少量存储空间
4. **索引**: 建议为`is_member`字段添加索引（如果查询频繁）

## 示例代码

### Python中使用新字段
```python
from database_models import User
from sqlalchemy.orm import Session

# 更新用户会员状态
user.is_member = True
user.birthday = date(1990, 1, 1)
user.memory_points = "用户偏好：喜欢安静，对音乐敏感"
user.membership_expires_at = datetime(2024, 12, 31, 23, 59, 59)

# 查询会员用户
members = db.query(User).filter(User.is_member == True).all()

# 查询特定年龄段的用户
from datetime import date, timedelta
cutoff_date = date.today() - timedelta(days=365*25)  # 25岁以下
young_users = db.query(User).filter(User.birthday > cutoff_date).all()

# 查询未过期的会员用户
from datetime import datetime
active_members = db.query(User).filter(
    User.is_member == True,
    (User.membership_expires_at == None) | (User.membership_expires_at > datetime.now())
).all()
```
