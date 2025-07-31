# File: database_models/database.py
# 功能：数据库配置和连接管理
# 实现：使用SQLAlchemy ORM，配置SQLite数据库连接

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==================== 数据库配置 ====================
# SQLite数据库连接URL
# 参数来源：项目配置，使用本地SQLite文件存储
DATABASE_URL = "sqlite:///./database/users.db"

# 创建数据库引擎
# 参数说明：
# - DATABASE_URL: 数据库连接字符串
# - connect_args: SQLite特定参数，允许多线程访问
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建会话工厂
# 参数说明：
# - bind: 绑定到数据库引擎
# - autoflush: 禁用自动刷新
# - autocommit: 禁用自动提交
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 声明式基类
Base = declarative_base()

# ==================== 数据库初始化 ====================
def init_db():
    """
    初始化数据库
    功能：创建所有数据库表结构
    
    说明：
        此函数在应用启动时调用，确保数据库表结构存在
        如果表已存在，不会重复创建
    """
    Base.metadata.create_all(bind=engine)  # 创建所有表结构 