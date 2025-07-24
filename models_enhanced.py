# 增强版用户模型示例
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./database/users.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    apple_user_id = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)  # 用户姓名
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    last_login = Column(DateTime, default=datetime.utcnow)  # 最后登录时间

def init_db():
    Base.metadata.create_all(bind=engine) 