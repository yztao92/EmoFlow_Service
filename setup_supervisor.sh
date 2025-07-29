#!/bin/bash

echo "🚀 开始安装和配置 Supervisor..."

# 检查是否已安装 supervisor
if ! command -v supervisord &> /dev/null; then
    echo "📦 安装 Supervisor..."
    apt update
    apt install -y supervisor
else
    echo "✅ Supervisor 已安装"
fi

# 创建 supervisor 配置目录（如果不存在）
mkdir -p /etc/supervisor/conf.d

# 复制配置文件到 supervisor 配置目录
echo "📝 复制配置文件..."
cp emoflow_supervisor.conf /etc/supervisor/conf.d/

# 重新加载 supervisor 配置
echo "🔄 重新加载 Supervisor 配置..."
supervisorctl reread
supervisorctl update

# 启动 emoflow 服务
echo "▶️ 启动 EmoFlow 服务..."
supervisorctl start emoflow

# 检查服务状态
echo "📊 检查服务状态..."
supervisorctl status emoflow

echo "✅ Supervisor 配置完成！"
echo ""
echo "📋 常用命令："
echo "  查看状态: supervisorctl status"
echo "  启动服务: supervisorctl start emoflow"
echo "  停止服务: supervisorctl stop emoflow"
echo "  重启服务: supervisorctl restart emoflow"
echo "  查看日志: tail -f /root/EmoFlow_Service/logs/emoflow.log"
echo "  查看错误日志: tail -f /root/EmoFlow_Service/logs/emoflow_error.log" 