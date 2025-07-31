#!/bin/bash

echo "🚀 启动 EmoFlow 服务..."

# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export PYTHONPATH="/root/EmoFlow_Service"

# 启动服务
echo "📡 服务将在 http://0.0.0.0:8000 启动"
echo "📝 日志文件: /root/EmoFlow_Service/logs/emoflow.log"
echo "❌ 错误日志: /root/EmoFlow_Service/logs/emoflow_error.log"
echo ""
echo "按 Ctrl+C 停止服务"
echo "----------------------------------------"

# 启动 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 