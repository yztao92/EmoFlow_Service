# File: database_models/__init__.py
# 功能：数据库模型包的初始化文件，导出所有模型和配置
# 实现：统一导出用户、日记模型和数据库配置

# 导出数据库配置
from .database import init_db, SessionLocal

# 导出数据模型
from .user import User
from .journal import Journal
from .chat_session import ChatSession
from .image import Image

# 导出数据验证模型
from .schemas import AppleLoginRequest

# 导出所有公共接口
__all__ = [
    "init_db",
    "SessionLocal", 
    "User",
    "Journal",
    "ChatSession",
    "Image",
    "AppleLoginRequest"
] 