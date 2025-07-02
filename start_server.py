#!/usr/bin/env python3
"""
EmoFlow 服务器启动脚本
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    # 检查环境变量
    required_vars = ["ZHIPUAI_API_KEY", "DEEPSEEK_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ 缺少必需的环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请创建 .env 文件并设置相应的 API 密钥")
        sys.exit(1)
    
    # 检查向量库是否存在
    vectorstore_path = os.getenv("VECTORSTORE_BASE", "data/vectorstore_by_summary")
    if not os.path.exists(vectorstore_path):
        print(f"❌ 向量库路径不存在: {vectorstore_path}")
        print("请先运行 embedding/build_vectorstore.py 构建向量库")
        sys.exit(1)
    
    print("✅ 环境检查通过，启动服务器...")
    
    # 启动服务器
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 