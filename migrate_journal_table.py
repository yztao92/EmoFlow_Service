#!/usr/bin/env python3
"""
日记表结构迁移脚本
简化字段，只保留核心字段
"""

import os
import sys
import logging
from datetime import datetime
from database_models import User, Journal, SessionLocal
from database_models.database import Base
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def backup_journal_data():
    """
    备份现有日记数据
    """
    try:
        logging.info("🔄 开始备份现有日记数据")
        
        db = SessionLocal()
        try:
            # 获取所有日记数据
            journals = db.query(Journal).all()
            
            backup_data = []
            for journal in journals:
                backup_data.append({
                    'id': journal.id,
                    'user_id': journal.user_id,
                    'title': journal.title,
                    'content': journal.content,
                    'content_html': journal.content_html,
                    'content_plain': journal.content_plain,
                    'content_format': journal.content_format,
                    'is_safe': journal.is_safe,
                    'messages': journal.messages,
                    'session_id': journal.session_id,
                    'emotion': journal.emotion,
                    'memory_point': journal.memory_point,
                    'created_at': journal.created_at,
                    'updated_at': journal.updated_at
                })
            
            # 保存备份到文件
            import json
            with open('journal_backup.json', 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            logging.info(f"✅ 已备份 {len(backup_data)} 条日记数据到 journal_backup.json")
            return True
            
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 备份失败：{e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logging.error(f"❌ 备份异常：{e}")
        return False

def create_new_journal_table():
    """
    创建新的简化日记表
    """
    try:
        logging.info("🔄 开始创建新的简化日记表")
        
        # 获取数据库连接
        from database_models.database import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        
        # 创建新表
        new_table_sql = """
        CREATE TABLE journals_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            messages TEXT,
            emotion VARCHAR,
            session_id VARCHAR,
            memory_point TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
        
        with engine.connect() as conn:
            conn.execute(text(new_table_sql))
            conn.commit()
        
        logging.info("✅ 新表 journals_new 创建成功")
        return True
        
    except Exception as e:
        logging.error(f"❌ 创建新表失败：{e}")
        return False

def migrate_data():
    """
    迁移数据到新表
    """
    try:
        logging.info("🔄 开始迁移数据到新表")
        
        # 获取数据库连接
        from database_models.database import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        
        # 迁移数据
        migrate_sql = """
        INSERT INTO journals_new (id, user_id, content, messages, emotion, session_id, memory_point, created_at, updated_at)
        SELECT id, user_id, content, messages, emotion, session_id, memory_point, created_at, updated_at
        FROM journals
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(migrate_sql))
            conn.commit()
            logging.info(f"✅ 已迁移 {result.rowcount} 条数据")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ 数据迁移失败：{e}")
        return False

def replace_table():
    """
    替换表结构
    """
    try:
        logging.info("🔄 开始替换表结构")
        
        # 获取数据库连接
        from database_models.database import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 删除旧表
            conn.execute(text("DROP TABLE journals"))
            logging.info("✅ 旧表 journals 已删除")
            
            # 重命名新表
            conn.execute(text("ALTER TABLE journals_new RENAME TO journals"))
            logging.info("✅ 新表已重命名为 journals")
            
            conn.commit()
        
        return True
        
    except Exception as e:
        logging.error(f"❌ 表替换失败：{e}")
        return False

def verify_migration():
    """
    验证迁移结果
    """
    try:
        logging.info("🔄 开始验证迁移结果")
        
        db = SessionLocal()
        try:
            # 检查表结构
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            columns = inspector.get_columns('journals')
            
            print("\n📊 新表结构验证:")
            print("-" * 50)
            for column in columns:
                print(f"  {column['name']:<15} | {column['type']} | {'NOT NULL' if not column['nullable'] else 'NULL'}")
            
            # 检查数据数量
            count = db.query(Journal).count()
            print(f"\n📈 数据统计:")
            print(f"  总日记数: {count}")
            
            # 检查样本数据
            sample = db.query(Journal).first()
            if sample:
                print(f"\n📝 样本数据验证:")
                print(f"  ID: {sample.id}")
                print(f"  User ID: {sample.user_id}")
                print(f"  Content 长度: {len(sample.content) if sample.content else 0}")
                print(f"  Messages: {'有' if sample.messages else '无'}")
                print(f"  Emotion: {sample.emotion}")
                print(f"  Session ID: {sample.session_id}")
                print(f"  Memory Point: {'有' if sample.memory_point else '无'}")
                print(f"  Created At: {sample.created_at}")
                print(f"  Updated At: {sample.updated_at}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 验证失败：{e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logging.error(f"❌ 验证异常：{e}")
        return False

def main():
    """
    主函数
    """
    print("🔄 日记表结构迁移工具")
    print("=" * 60)
    print("将简化日记表结构，只保留以下字段：")
    print("1. id")
    print("2. user_id") 
    print("3. content")
    print("4. messages")
    print("5. emotion")
    print("6. session_id")
    print("7. memory_point")
    print("8. created_at")
    print("9. updated_at")
    print("=" * 60)
    
    # 确认操作
    confirmation = input("⚠️ 确定要执行迁移吗？这将删除 title, content_html, content_plain, content_format, is_safe 字段 (y/N): ")
    if confirmation.lower() != 'y':
        print("🚫 操作取消")
        return
    
    # 执行迁移步骤
    steps = [
        ("备份数据", backup_journal_data),
        ("创建新表", create_new_journal_table),
        ("迁移数据", migrate_data),
        ("替换表结构", replace_table),
        ("验证结果", verify_migration)
    ]
    
    for step_name, step_func in steps:
        print(f"\n🔄 执行步骤: {step_name}")
        if not step_func():
            print(f"❌ 步骤失败: {step_name}")
            return
        print(f"✅ 步骤完成: {step_name}")
    
    print("\n🎉 迁移完成！")
    print("📁 备份文件: journal_backup.json")

if __name__ == "__main__":
    main()
