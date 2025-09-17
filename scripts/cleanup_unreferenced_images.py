#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理未被日记引用的图片文件
功能：删除upload文件夹中未被日记引用的图片文件，保留聊天记录
作者：EmoFlow Team
创建时间：2025-09-17
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_models.database import Base
from database_models.image import Image
from database_models.journal import Journal

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup_unreferenced_images.log'),
        logging.StreamHandler()
    ]
)

def get_database_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), "..", "database", "users.db")
    
    if not os.path.exists(db_path):
        logging.error(f"❌ 数据库文件不存在: {db_path}")
        return None
    
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_referenced_image_filenames():
    """获取所有被日记引用的图片文件名"""
    db = get_database_connection()
    if not db:
        return set()
    
    try:
        # 查询所有日记中的图片ID
        journals = db.query(Journal).filter(Journal.images.isnot(None)).all()
        
        referenced_image_ids = set()
        for journal in journals:
            if journal.images:
                # 解析逗号分隔的图片ID
                image_ids = journal.images.split(",")
                for image_id in image_ids:
                    try:
                        referenced_image_ids.add(int(image_id.strip()))
                    except ValueError:
                        logging.warning(f"⚠️ 无效的图片ID: {image_id}")
        
        logging.info(f"📊 找到 {len(referenced_image_ids)} 个被日记引用的图片ID")
        
        # 根据图片ID查询文件名
        if referenced_image_ids:
            images = db.query(Image.filename).filter(Image.id.in_(referenced_image_ids)).all()
            referenced_filenames = {img.filename for img in images}
            logging.info(f"📊 找到 {len(referenced_filenames)} 个被引用的图片文件名")
        else:
            referenced_filenames = set()
            logging.info("📊 没有图片被日记引用")
        
        return referenced_filenames
        
    except Exception as e:
        logging.error(f"❌ 查询被引用图片失败: {e}")
        return set()
    finally:
        db.close()

def get_filesystem_image_filenames():
    """获取文件系统中所有图片文件名"""
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "images")
    
    if not os.path.exists(upload_dir):
        logging.warning(f"⚠️ 上传目录不存在: {upload_dir}")
        return set()
    
    filenames = set()
    
    # 遍历所有用户目录
    for user_dir in os.listdir(upload_dir):
        user_path = os.path.join(upload_dir, user_dir)
        if os.path.isdir(user_path):
            # 遍历用户目录中的文件
            for filename in os.listdir(user_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    filenames.add(filename)
    
    logging.info(f"📊 文件系统中有 {len(filenames)} 个图片文件")
    return filenames

def cleanup_unreferenced_images(dry_run=False):
    """清理未被日记引用的图片文件"""
    logging.info("=" * 60)
    logging.info("🧹 开始清理未被日记引用的图片文件")
    logging.info("=" * 60)
    
    # 获取被日记引用的图片文件名
    referenced_filenames = get_referenced_image_filenames()
    
    # 获取文件系统中的所有图片文件名
    filesystem_filenames = get_filesystem_image_filenames()
    
    # 找出未被引用的图片文件
    unreferenced_filenames = filesystem_filenames - referenced_filenames
    
    logging.info(f"📊 统计结果:")
    logging.info(f"   - 文件系统图片数: {len(filesystem_filenames)}")
    logging.info(f"   - 被日记引用数: {len(referenced_filenames)}")
    logging.info(f"   - 未被引用数: {len(unreferenced_filenames)}")
    
    if not unreferenced_filenames:
        logging.info("✅ 所有图片都被日记引用，无需清理")
        return
    
    # 计算可释放的存储空间
    total_size = 0
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "images")
    
    for user_dir in os.listdir(upload_dir):
        user_path = os.path.join(upload_dir, user_dir)
        if os.path.isdir(user_path):
            for filename in unreferenced_filenames:
                file_path = os.path.join(user_path, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    
    logging.info(f"💾 可释放存储空间: {total_size / 1024 / 1024:.2f} MB")
    
    if dry_run:
        logging.info("🔍 模拟模式 - 不会实际删除文件")
        for filename in sorted(unreferenced_filenames):
            logging.info(f"   - 将删除: {filename}")
        return
    
    # 确认删除
    logging.info(f"🗑️ 准备删除 {len(unreferenced_filenames)} 个未被引用的图片文件...")
    
    deleted_count = 0
    failed_count = 0
    freed_space = 0
    
    for filename in sorted(unreferenced_filenames):
        # 在所有用户目录中查找并删除文件
        for user_dir in os.listdir(upload_dir):
            user_path = os.path.join(upload_dir, user_dir)
            if os.path.isdir(user_path):
                file_path = os.path.join(user_path, filename)
                if os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        freed_space += file_size
                        logging.info(f"🗑️ 删除文件: {filename} ({file_size} bytes)")
                        break  # 找到并删除后跳出循环
                    except Exception as e:
                        logging.error(f"❌ 删除失败 {filename}: {e}")
                        failed_count += 1
    
    logging.info(f"✅ 删除完成: 成功 {deleted_count} 个，失败 {failed_count} 个")
    logging.info(f"💾 释放空间: {freed_space / 1024 / 1024:.2f} MB")
    logging.info("=" * 60)
    logging.info("🎉 未被引用图片文件清理完成")
    logging.info("=" * 60)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='清理未被日记引用的图片文件')
    parser.add_argument('--dry-run', action='store_true', help='模拟模式，不实际删除文件')
    
    args = parser.parse_args()
    
    try:
        cleanup_unreferenced_images(dry_run=args.dry_run)
    except KeyboardInterrupt:
        logging.info("⚠️ 用户中断操作")
    except Exception as e:
        logging.error(f"❌ 清理过程异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
