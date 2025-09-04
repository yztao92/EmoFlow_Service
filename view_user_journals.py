#!/usr/bin/env python3
"""
查看指定用户日记内容的脚本
"""

import os
import sys
import logging
import json
from datetime import datetime
from database_models import User, Journal, SessionLocal
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def view_user_journals(user_name=None, user_id=None):
    """
    查看指定用户的日记内容
    
    参数：
        user_name (str): 用户姓名
        user_id (int): 用户ID
    """
    try:
        logging.info(f"🕛 开始查询用户日记: {user_name or user_id}")
        
        db = SessionLocal()
        try:
            # 根据姓名或ID查找用户
            if user_name:
                user = db.query(User).filter(User.name == user_name).first()
            elif user_id:
                user = db.query(User).filter(User.id == user_id).first()
            else:
                logging.error("❌ 请提供用户姓名或用户ID")
                return False
            
            if not user:
                logging.error(f"❌ 未找到用户: {user_name or user_id}")
                return False
            
            # 查询该用户的所有日记
            journals = db.query(Journal).filter(Journal.user_id == user.id)\
                .order_by(Journal.created_at.desc()).all()
            
            print("=" * 80)
            print(f"📝 用户日记详情 - {user.name} (ID: {user.id})")
            print("=" * 80)
            print(f"用户邮箱: {user.email or '未设置'}")
            print(f"Apple ID: {user.apple_user_id or '未设置'}")
            print(f"总日记数: {len(journals)} 篇")
            print("=" * 80)
            
            if not journals:
                print("📭 该用户还没有写过日记")
                return True
            
            # 显示每篇日记的详细信息
            for i, journal in enumerate(journals, 1):
                print(f"\n📖 第 {i} 篇日记")
                print("-" * 60)
                print(f"日记ID: {journal.id}")
                print(f"标题: {journal.title}")
                print(f"创建时间: {journal.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"更新时间: {journal.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"情绪标签: {journal.emotion or '未设置'}")
                print(f"会话ID: {journal.session_id or '未设置'}")
                print(f"内容格式: {journal.content_format or '未设置'}")
                print(f"安全标识: {'是' if journal.is_safe else '否'}")
                
                # 显示记忆点
                if journal.memory_point:
                    print(f"记忆点: {journal.memory_point}")
                
                # 显示日记内容
                print(f"\n📄 日记内容:")
                print("-" * 40)
                content = journal.content_plain or journal.content
                if content:
                    # 限制显示长度，避免输出过长
                    if len(content) > 500:
                        print(content[:500] + "...")
                        print(f"\n[内容已截断，完整内容共 {len(content)} 字符]")
                    else:
                        print(content)
                else:
                    print("无内容")
                
                # 显示对话历史（如果有）
                if journal.messages:
                    try:
                        messages = json.loads(journal.messages)
                        if messages:
                            print(f"\n💬 对话历史 ({len(messages)} 条消息):")
                            print("-" * 40)
                            for j, msg in enumerate(messages[:3], 1):  # 只显示前3条
                                role = msg.get('role', 'unknown')
                                content = msg.get('content', '')
                                if len(content) > 100:
                                    content = content[:100] + "..."
                                print(f"{j}. [{role}] {content}")
                            if len(messages) > 3:
                                print(f"... 还有 {len(messages) - 3} 条消息")
                    except json.JSONDecodeError:
                        print("\n💬 对话历史: 格式错误")
                
                print("\n" + "=" * 60)
            
            return True
            
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 数据库查询失败：{e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logging.error(f"❌ 脚本执行异常：{e}")
        return False

def main():
    """
    主函数
    """
    print("📝 用户日记查看工具")
    print("=" * 50)
    
    # 查看 Maggie Chou 的日记
    user_name = "Maggie Chou"
    
    if view_user_journals(user_name=user_name):
        print("\n🎉 查询完成！")
    else:
        print("\n❌ 查询失败，请查看日志获取详情。")

if __name__ == "__main__":
    main()
