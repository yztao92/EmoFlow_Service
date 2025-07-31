# EmoFlow 服务 Supervisor 监控配置

## 概述

本项目使用 Supervisor 来监控 EmoFlow 服务进程，确保服务在崩溃时能够自动重启。

## 文件说明

- `emoflow_supervisor.conf` - Supervisor 配置文件
- `setup_supervisor.sh` - 自动安装和配置脚本
- `start_emoflow.sh` - 手动启动脚本
- `logs/` - 日志文件目录

## 快速开始

### 1. 自动安装和配置

```bash
# 运行自动配置脚本
./setup_supervisor.sh
```

### 2. 手动安装

如果自动脚本失败，可以手动执行以下步骤：

```bash
# 安装 Supervisor
apt update
apt install -y supervisor

# 复制配置文件
cp emoflow_supervisor.conf /etc/supervisor/conf.d/

# 重新加载配置
supervisorctl reread
supervisorctl update

# 启动服务
supervisorctl start emoflow
```

## 常用命令

### 服务管理

```bash
# 查看所有服务状态
supervisorctl status

# 查看 EmoFlow 服务状态
supervisorctl status emoflow

# 启动服务
supervisorctl start emoflow

# 停止服务
supervisorctl stop emoflow

# 重启服务
supervisorctl restart emoflow

# 重新加载配置
supervisorctl reread
supervisorctl update
```

### 日志查看

```bash
# 查看服务日志
tail -f /root/EmoFlow_Service/logs/emoflow.log

# 查看错误日志
tail -f /root/EmoFlow_Service/logs/emoflow_error.log

# 查看 Supervisor 主日志
tail -f /var/log/supervisor/supervisord.log
```

### 手动启动（不使用 Supervisor）

```bash
# 直接启动服务
./start_emoflow.sh
```

## 配置说明

### 主要配置项

- **command**: 启动命令，使用 uvicorn 启动 FastAPI 应用
- **directory**: 工作目录
- **autostart**: 自动启动（true）
- **autorestart**: 自动重启（true）
- **startretries**: 启动重试次数（3次）
- **startsecs**: 启动超时时间（10秒）
- **stdout_logfile**: 标准输出日志文件
- **stderr_logfile**: 错误日志文件

### 日志轮转

- 日志文件大小限制：50MB
- 日志文件备份数量：10个
- 当日志文件达到限制时会自动轮转

## 故障排除

### 1. 服务无法启动

```bash
# 检查配置文件语法
supervisord -n -c /etc/supervisor/supervisord.conf

# 查看详细错误信息
supervisorctl tail emoflow
```

### 2. 权限问题

```bash
# 确保日志目录存在且有写权限
mkdir -p /root/EmoFlow_Service/logs
chmod 755 /root/EmoFlow_Service/logs
```

### 3. 端口冲突

如果 8000 端口被占用，修改 `emoflow_supervisor.conf` 中的端口号：

```ini
command=/root/EmoFlow_Service/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

然后重新加载配置：

```bash
supervisorctl reread
supervisorctl update
supervisorctl restart emoflow
```

## 系统服务

Supervisor 作为系统服务运行，开机自启动：

```bash
# 启用开机自启动
systemctl enable supervisor

# 启动 Supervisor 服务
systemctl start supervisor

# 查看服务状态
systemctl status supervisor
```

## 监控和告警

可以通过以下方式监控服务状态：

```bash
# 检查服务是否运行
if supervisorctl status emoflow | grep -q "RUNNING"; then
    echo "服务运行正常"
else
    echo "服务异常，需要检查"
fi
```

## 注意事项

1. 确保虚拟环境路径正确：`/root/EmoFlow_Service/venv/`
2. 确保工作目录存在：`/root/EmoFlow_Service/`
3. 确保日志目录有写权限
4. 如果修改了配置文件，需要重新加载配置
5. 建议定期检查日志文件大小，避免磁盘空间不足 