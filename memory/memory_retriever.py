#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆点检索器
功能：从数据库中检索用户的最新记忆点，用于对话提示生成
"""

import os
import sys
from typing import List, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_models import SessionLocal, Journal

def get_user_latest_memories(user_id: int, limit: int = 5) -> List[str]:
    """
    获取用户最新的记忆点
    
    参数:
        user_id: 用户ID
        limit: 返回的记忆点数量，默认5个
        
    返回:
        List[str]: 记忆点列表，如果没有记忆点则返回空列表
    """
    db = SessionLocal()
    try:
        # 查询用户最新的有记忆点的日记
        journals = db.query(Journal).filter(
            Journal.user_id == user_id,
            Journal.memory_point.isnot(None)
        ).order_by(Journal.created_at.desc()).limit(limit).all()
        
        # 提取记忆点内容
        memories = []
        for journal in journals:
            if journal.memory_point:
                # 清理记忆点内容，移除可能的引号
                memory = journal.memory_point.strip()
                if memory.startswith('"') and memory.endswith('"'):
                    memory = memory[1:-1]
                elif memory.startswith('"') and memory.endswith('"'):
                    memory = memory[1:-1]
                
                memories.append(memory)
        
        return memories
        
    except Exception as e:
        print(f"❌ 获取用户记忆点失败: {e}")
        return []
    finally:
        db.close()

def get_user_memories_by_emotion(user_id: int, emotion: str, limit: int = 3) -> List[str]:
    """
    根据情绪类型获取用户相关的记忆点
    
    参数:
        user_id: 用户ID
        emotion: 情绪类型 (happy, peaceful, unhappy, angry等)
        limit: 返回的记忆点数量，默认3个
        
    返回:
        List[str]: 相关记忆点列表
    """
    db = SessionLocal()
    try:
        # 查询用户指定情绪类型的日记记忆点
        journals = db.query(Journal).filter(
            Journal.user_id == user_id,
            Journal.emotion == emotion,
            Journal.memory_point.isnot(None)
        ).order_by(Journal.created_at.desc()).limit(limit).all()
        
        # 提取记忆点内容
        memories = []
        for journal in journals:
            if journal.memory_point:
                memory = journal.memory_point.strip()
                if memory.startswith('"') and memory.endswith('"'):
                    memory = memory[1:-1]
                elif memory.startswith('"') and memory.endswith('"'):
                    memory = memory[1:-1]
                
                memories.append(memory)
        
        return memories
        
    except Exception as e:
        print(f"❌ 获取用户情绪相关记忆点失败: {e}")
        return []
    finally:
        db.close()

def get_user_memories_summary(user_id: int, limit: int = 5) -> str:
    """
    获取用户记忆点的文本摘要，用于对话提示
    
    参数:
        user_id: 用户ID
        limit: 返回的记忆点数量，默认5个
        
    返回:
        str: 记忆点摘要文本，如果没有记忆点则返回空字符串
    """
    memories = get_user_latest_memories(user_id, limit)
    
    if not memories:
        return ""
    
    # 将记忆点格式化为文本摘要
    summary_lines = []
    for i, memory in enumerate(memories, 1):
        summary_lines.append(f"{i}. {memory}")
    
    return "\n".join(summary_lines)
