# File: dialogue/session_manager.py
# 功能：聊天会话管理服务
# 实现：管理用户聊天会话的创建、获取、更新和存储

import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from database_models import SessionLocal, ChatSession
from .state_tracker import StateTracker

logger = logging.getLogger(__name__)

class SessionManager:
    """
    聊天会话管理器
    功能：管理用户聊天会话的创建、获取、更新和存储
    """
    
    def __init__(self):
        self.memory_cache = {}  # 内存缓存，提高性能
    
    def get_or_create_session(self, user_id: int, session_id: str) -> StateTracker:
        """
        获取或创建聊天会话
        :param user_id: 用户ID
        :param session_id: 会话ID
        :return: StateTracker实例
        """
        session_key = f"user_{user_id}_{session_id}"
        
        # 先从内存缓存获取
        if session_key in self.memory_cache:
            logger.debug(f"从内存缓存获取会话: {session_key}")
            return self.memory_cache[session_key]
        
        # 从数据库获取
        db: Session = SessionLocal()
        try:
            chat_session = db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.session_id == session_id,
                ChatSession.is_active == True
            ).first()
            
            if chat_session:
                # 从数据库恢复会话状态
                state_data = json.loads(chat_session.state_data) if chat_session.state_data else {}
                state = StateTracker.from_dict(state_data)
                logger.debug(f"从数据库恢复会话: {session_key}")
            else:
                # 创建新会话
                state = StateTracker()
                logger.debug(f"创建新会话: {session_key}")
            
            # 存储到内存缓存
            self.memory_cache[session_key] = state
            return state
            
        finally:
            db.close()
    
    def save_session(self, user_id: int, session_id: str, state: StateTracker) -> None:
        """
        保存聊天会话状态
        :param user_id: 用户ID
        :param session_id: 会话ID
        :param state: StateTracker实例
        """
        session_key = f"user_{user_id}_{session_id}"
        
        # 更新内存缓存
        self.memory_cache[session_key] = state
        
        # 保存到数据库
        db: Session = SessionLocal()
        try:
            chat_session = db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.session_id == session_id,
                ChatSession.is_active == True
            ).first()
            
            state_data = json.dumps(state.to_dict(), ensure_ascii=False)
            
            if chat_session:
                # 更新现有会话
                chat_session.state_data = state_data
                chat_session.updated_at = db.query(ChatSession).filter(
                    ChatSession.id == chat_session.id
                ).first().updated_at
                logger.debug(f"更新会话状态: {session_key}")
            else:
                # 创建新会话记录
                chat_session = ChatSession(
                    user_id=user_id,
                    session_id=session_id,
                    state_data=state_data
                )
                db.add(chat_session)
                logger.debug(f"创建新会话记录: {session_key}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"保存会话状态失败: {session_key}, 错误: {e}")
            raise
        finally:
            db.close()
    
    def clear_session(self, user_id: int, session_id: str) -> None:
        """
        清除聊天会话（标记为非活跃）
        :param user_id: 用户ID
        :param session_id: 会话ID
        """
        session_key = f"user_{user_id}_{session_id}"
        
        # 清除内存缓存
        if session_key in self.memory_cache:
            del self.memory_cache[session_key]
        
        # 标记数据库中的会话为非活跃
        db: Session = SessionLocal()
        try:
            chat_session = db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.session_id == session_id,
                ChatSession.is_active == True
            ).first()
            
            if chat_session:
                chat_session.is_active = False
                db.commit()
                logger.debug(f"清除会话: {session_key}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"清除会话失败: {session_key}, 错误: {e}")
            raise
        finally:
            db.close()
    
    def clear_memory_cache(self) -> None:
        """
        清除内存缓存（用于内存管理）
        """
        self.memory_cache.clear()
        logger.debug("清除会话内存缓存")

# 全局会话管理器实例
session_manager = SessionManager()
