# File: models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from typing import Optional
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
    name = Column(String, nullable=True)  # 新增：姓名字段
    
    # 关联日记
    journals = relationship("Journal", back_populates="user")

class Journal(Base):
    __tablename__ = "journals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    session_id = Column(String, nullable=True)  # 关联的对话会话ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联用户
    user = relationship("User", back_populates="journals")

class AppleLoginRequest(BaseModel):
    identity_token: str
    full_name: Optional[str] = None  # 新增：用户姓名
    email: Optional[str] = None      # 新增：用户邮箱

def init_db():
    Base.metadata.create_all(bind=engine)