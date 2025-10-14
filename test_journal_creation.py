#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试日记创建脚本
"""

import os
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

from database_models.database import SessionLocal
from database_models.journal import Journal
from llm.llm_factory import chat_with_llm

def test_journal_creation():
    """测试创建一篇日记"""
    print("🧪 测试日记创建...")
    
    # 测试LLM调用
    test_prompt = """请生成一篇happy情绪的心情日记，要求：
1. 用第一人称"我"的口吻
2. 字数控制在80-100字
3. 内容要真实自然，像真实的日常记录
4. 不要提到AI、对话等
5. 以事件和场景为主，情绪为辅

请直接输出日记内容："""
    
    try:
        content = chat_with_llm(test_prompt)
        print(f"✅ 日记内容生成成功:")
        print(f"内容: {content}")
        
        # 测试记忆点生成
        memory_prompt = f"""请根据以下日记内容生成一个简洁的记忆点摘要，要求：
1. 格式：2025-10-15 + 简短描述（10-15字）
2. 突出主要事件或感受
3. 语言简洁自然

日记内容：{content}
情绪：happy

请直接输出记忆点："""
        
        memory_point = chat_with_llm(memory_prompt)
        print(f"✅ 记忆点生成成功:")
        print(f"记忆点: {memory_point}")
        
        # 测试数据库写入
        db = SessionLocal()
        try:
            journal = Journal(
                user_id=13,
                content=content,
                session_id="test",
                emotion="happy",
                memory_point=memory_point,
                created_at=datetime.now(timezone(timedelta(hours=8)))
            )
            
            db.add(journal)
            db.commit()
            db.refresh(journal)
            
            print(f"✅ 数据库写入成功: ID={journal.id}")
            
        except Exception as e:
            print(f"❌ 数据库写入失败: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_journal_creation()
