# 图片清理工具使用说明

## 📁 文件说明

- `cleanup_unused_images.py` - 基础清理脚本，只清理未被日记引用的图片
- `advanced_image_cleanup.py` - 高级清理脚本，支持多种清理策略
- `scheduled_cleanup.py` - 定时清理脚本，可配置定期执行
- `cleanup_config.json` - 配置文件示例
- `README_cleanup.md` - 本说明文档

## 🚀 快速开始

### 1. 基础清理（推荐）

```bash
# 清理未被日记引用的图片
python3 cleanup_unused_images.py
```

### 2. 高级清理

```bash
# 查看图片统计信息
python3 advanced_image_cleanup.py --action stats

# 清理未使用的图片（模拟模式）
python3 advanced_image_cleanup.py --action unused --dry-run

# 清理未使用的图片（实际执行）
python3 advanced_image_cleanup.py --action unused

# 清理30天前的图片
python3 advanced_image_cleanup.py --action old --days 30

# 清理超过5MB的图片
python3 advanced_image_cleanup.py --action large --max-size 5
```

### 3. 定时清理

```bash
# 使用默认配置运行定时清理
python3 scheduled_cleanup.py

# 使用自定义配置文件
python3 scheduled_cleanup.py --config cleanup_config.json

# 模拟模式（不实际删除）
python3 scheduled_cleanup.py --dry-run
```

## ⚙️ 配置说明

### 清理策略配置

```json
{
  "cleanup_strategies": {
    "unused_images": {
      "enabled": true,  // 是否启用清理未使用图片
      "description": "清理未被日记引用的图片"
    },
    "old_images": {
      "enabled": true,  // 是否启用清理旧图片
      "days": 30,       // 清理多少天前的图片
      "description": "清理30天前的图片"
    },
    "large_images": {
      "enabled": false, // 是否启用清理大图片
      "max_size_mb": 10, // 清理超过多少MB的图片
      "description": "清理超过10MB的图片"
    }
  }
}
```

### 清理计划配置

```json
{
  "cleanup_schedule": {
    "run_every_hours": 24,        // 每多少小时运行一次
    "max_cleanup_per_run": 100,   // 每次最多清理多少张图片
    "backup_before_delete": false // 删除前是否备份
  }
}
```

## 📊 清理策略详解

### 1. 未使用图片清理
- **原理**: 查找所有图片，检查是否被任何日记引用
- **安全**: 只删除完全没有被引用的图片
- **推荐**: 定期执行，释放存储空间

### 2. 旧图片清理
- **原理**: 删除指定天数前创建的图片
- **风险**: 可能删除仍在使用但较旧的图片
- **建议**: 谨慎使用，建议先模拟运行

### 3. 大图片清理
- **原理**: 删除超过指定大小的图片
- **用途**: 控制存储空间，清理异常大的文件
- **建议**: 根据实际需求调整大小阈值

## 🔧 定时任务设置

### 使用 crontab 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 每天凌晨2点执行清理（使用默认配置）
0 2 * * * cd /root/EmoFlow_Service/scripts && python3 scheduled_cleanup.py

# 每天凌晨2点执行清理（使用自定义配置）
0 2 * * * cd /root/EmoFlow_Service/scripts && python3 scheduled_cleanup.py --config cleanup_config.json

# 每周日凌晨3点执行清理
0 3 * * 0 cd /root/EmoFlow_Service/scripts && python3 scheduled_cleanup.py
```

### 使用 systemd 定时器（推荐）

1. 创建服务文件 `/etc/systemd/system/emoflow-cleanup.service`:
```ini
[Unit]
Description=EmoFlow Image Cleanup Service
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/EmoFlow_Service/scripts
ExecStart=/usr/bin/python3 scheduled_cleanup.py --config cleanup_config.json
StandardOutput=journal
StandardError=journal
```

2. 创建定时器文件 `/etc/systemd/system/emoflow-cleanup.timer`:
```ini
[Unit]
Description=Run EmoFlow Image Cleanup daily
Requires=emoflow-cleanup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

3. 启用定时器:
```bash
sudo systemctl daemon-reload
sudo systemctl enable emoflow-cleanup.timer
sudo systemctl start emoflow-cleanup.timer
```

## 📈 监控和日志

### 日志文件位置
- 应用日志: `/root/EmoFlow_Service/logs/scheduled_cleanup.log`
- 清理统计: `/root/EmoFlow_Service/logs/cleanup_stats.json`

### 查看清理统计
```bash
# 查看清理统计文件
cat /root/EmoFlow_Service/logs/cleanup_stats.json | python3 -m json.tool

# 查看最近的清理记录
tail -20 /root/EmoFlow_Service/logs/scheduled_cleanup.log
```

## ⚠️ 注意事项

1. **备份重要数据**: 在首次运行前，建议备份数据库和图片文件
2. **模拟运行**: 使用 `--dry-run` 参数先模拟运行，确认清理策略
3. **监控存储**: 定期检查存储空间使用情况
4. **错误处理**: 关注日志中的错误信息，及时处理异常
5. **权限检查**: 确保脚本有足够的权限访问数据库和文件系统

## 🆘 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库文件路径是否正确
   - 确认数据库文件权限

2. **文件删除失败**
   - 检查文件系统权限
   - 确认文件没有被其他进程占用

3. **配置加载失败**
   - 检查JSON配置文件格式
   - 确认配置文件路径正确

### 恢复数据

如果误删了重要图片，可以从以下位置恢复：
1. 数据库备份
2. 图片文件备份（如果启用了备份）
3. 系统回收站（如果配置了）

## 📞 技术支持

如有问题，请检查：
1. 日志文件中的错误信息
2. 系统资源使用情况
3. 数据库和文件系统状态

建议在非高峰时段运行清理任务，避免影响正常服务。
