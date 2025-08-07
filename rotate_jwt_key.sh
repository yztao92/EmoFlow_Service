#!/bin/bash

# JWT密钥轮换脚本
# 使用方法: ./rotate_jwt_key.sh

echo "🔐 开始JWT密钥轮换..."

# 1. 生成新密钥
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "✅ 生成新密钥: ${NEW_KEY:0:20}..."

# 2. 备份当前.env文件
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ 备份当前.env文件"

# 3. 替换密钥
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_KEY/" .env
echo "✅ 更新.env文件中的JWT密钥"

# 4. 验证替换
if grep -q "JWT_SECRET_KEY=$NEW_KEY" .env; then
    echo "✅ 密钥替换成功"
else
    echo "❌ 密钥替换失败"
    exit 1
fi

echo ""
echo "⚠️  重要提醒："
echo "1. 所有现有用户需要重新登录"
echo "2. 移动应用需要重新认证"
echo "3. 建议在低峰期执行此操作"
echo ""
echo "🔄 请重启服务以应用新密钥"
echo "systemctl restart your-service" 