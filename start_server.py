#!/usr/bin/env python3
"""
EmoFlow 服务器启动脚本
"""

import os
import subprocess
import sys

def main():
    # 设置环境变量解决 OpenMP 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    # 启动 FastAPI 服务
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    print("🚀 启动 EmoFlow 服务...")
    print("📝 已设置 KMP_DUPLICATE_LIB_OK=TRUE 解决 OpenMP 警告")
    print("🌐 服务地址: http://localhost:8000")
    print("📚 API 文档: http://localhost:8000/docs")
    print("=" * 50)
    
    try:
        # 保证子进程日志实时输出到主终端
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main() 