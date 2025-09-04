#!/usr/bin/env python3
"""
分析日记数据格式的脚本
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

def analyze_journal_format():
    """
    分析日记数据格式
    """
    try:
        logging.info("🕛 开始分析日记数据格式")
        
        db = SessionLocal()
        try:
            # 获取一些样本日记
            sample_journals = db.query(Journal).limit(5).all()
            
            if not sample_journals:
                logging.warning("⚠️ 没有找到任何日记")
                return False
            
            print("=" * 80)
            print("📊 日记数据格式分析")
            print("=" * 80)
            
            # 分析数据库表结构
            print("🗄️ 数据库表结构 (journals 表):")
            print("-" * 50)
            journal_columns = Journal.__table__.columns
            for column in journal_columns:
                print(f"  {column.name:<20} | {column.type} | {'NOT NULL' if not column.nullable else 'NULL'}")
            
            print("\n" + "=" * 80)
            print("📝 样本日记数据分析")
            print("=" * 80)
            
            for i, journal in enumerate(sample_journals, 1):
                print(f"\n📖 样本日记 {i} (ID: {journal.id})")
                print("-" * 60)
                
                # 基本信息
                print("🔍 基本信息:")
                print(f"  user_id: {journal.user_id}")
                print(f"  title: {journal.title}")
                print(f"  created_at: {journal.created_at}")
                print(f"  updated_at: {journal.updated_at}")
                print(f"  emotion: {journal.emotion}")
                print(f"  session_id: {journal.session_id}")
                print(f"  content_format: {journal.content_format}")
                print(f"  is_safe: {journal.is_safe}")
                
                # 内容字段分析
                print("\n📄 内容字段分析:")
                print(f"  content 长度: {len(journal.content) if journal.content else 0}")
                print(f"  content_html 长度: {len(journal.content_html) if journal.content_html else 0}")
                print(f"  content_plain 长度: {len(journal.content_plain) if journal.content_plain else 0}")
                print(f"  memory_point 长度: {len(journal.memory_point) if journal.memory_point else 0}")
                
                # 显示内容预览
                if journal.content:
                    print(f"\n📝 content 预览 (前100字符):")
                    print(f"  {journal.content[:100]}...")
                
                if journal.content_plain:
                    print(f"\n📝 content_plain 预览 (前100字符):")
                    print(f"  {journal.content_plain[:100]}...")
                
                if journal.memory_point:
                    print(f"\n🧠 memory_point 预览 (前100字符):")
                    print(f"  {journal.memory_point[:100]}...")
                
                # 分析 messages 字段
                print(f"\n💬 messages 字段分析:")
                if journal.messages:
                    try:
                        messages = json.loads(journal.messages)
                        print(f"  messages 类型: {type(messages)}")
                        print(f"  messages 长度: {len(messages)}")
                        if messages:
                            print(f"  第一条消息结构: {list(messages[0].keys()) if isinstance(messages[0], dict) else '非字典类型'}")
                            if isinstance(messages[0], dict):
                                print(f"  第一条消息内容: {messages[0]}")
                    except json.JSONDecodeError as e:
                        print(f"  messages JSON解析错误: {e}")
                        print(f"  messages 原始内容: {journal.messages[:100]}...")
                else:
                    print("  messages 为空")
                
                print("\n" + "=" * 60)
            
            # 统计各种字段的使用情况
            print("\n📊 字段使用统计:")
            print("-" * 50)
            
            total_journals = db.query(Journal).count()
            print(f"总日记数: {total_journals}")
            
            # 统计各字段的非空情况
            stats = {
                'content': db.query(Journal).filter(Journal.content.isnot(None)).count(),
                'content_html': db.query(Journal).filter(Journal.content_html.isnot(None)).count(),
                'content_plain': db.query(Journal).filter(Journal.content_plain.isnot(None)).count(),
                'memory_point': db.query(Journal).filter(Journal.memory_point.isnot(None)).count(),
                'messages': db.query(Journal).filter(Journal.messages.isnot(None)).count(),
                'emotion': db.query(Journal).filter(Journal.emotion.isnot(None)).count(),
                'session_id': db.query(Journal).filter(Journal.session_id.isnot(None)).count(),
            }
            
            for field, count in stats.items():
                percentage = (count / total_journals) * 100 if total_journals > 0 else 0
                print(f"  {field:<15}: {count:3d}/{total_journals} ({percentage:5.1f}%)")
            
            # 统计情绪标签分布
            print(f"\n😊 情绪标签分布:")
            print("-" * 30)
            from sqlalchemy import func
            emotion_stats = db.query(Journal.emotion, func.count(Journal.id)).group_by(Journal.emotion).all()
            for emotion, count in emotion_stats:
                percentage = (count / total_journals) * 100 if total_journals > 0 else 0
                print(f"  {emotion or '未设置':<15}: {count:3d} ({percentage:5.1f}%)")
            
            # 统计内容格式分布
            print(f"\n📄 内容格式分布:")
            print("-" * 30)
            format_stats = db.query(Journal.content_format, func.count(Journal.id)).group_by(Journal.content_format).all()
            for format_type, count in format_stats:
                percentage = (count / total_journals) * 100 if total_journals > 0 else 0
                print(f"  {format_type or '未设置':<15}: {count:3d} ({percentage:5.1f}%)")
            
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
    print("📊 日记数据格式分析工具")
    print("=" * 50)
    
    if analyze_journal_format():
        print("\n🎉 分析完成！")
    else:
        print("\n❌ 分析失败，请查看日志获取详情。")

if __name__ == "__main__":
    main()
