#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查用户 ID 14 最新日记的图片数量和详情
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database_models.database import SessionLocal
from database_models.journal import Journal
from database_models.image import Image
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_latest_journal_images_detail():
    """
    详细检查用户 ID 14 最新日记的图片数量和详情
    """
    print("=" * 60)
    print("🔍 详细检查用户 ID 14 最新日记的图片")
    print("=" * 60)
    
    db: Session = SessionLocal()
    try:
        # 获取用户 14 的最新日记
        latest_journal = db.query(Journal).filter(Journal.user_id == 14)\
            .order_by(Journal.created_at.desc())\
            .first()
        
        if not latest_journal:
            print("❌ 用户 ID 14 没有日记数据")
            return False
        
        print(f"📝 最新日记信息:")
        print(f"  - ID: {latest_journal.id}")
        print(f"  - 时间: {latest_journal.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - 情绪: {latest_journal.emotion}")
        print(f"  - 内容前50字: {latest_journal.content[:50]}...")
        print(f"  - 原始图片字段值: '{latest_journal.images}'")
        
        if not latest_journal.images:
            print(f"📷 图片数量: 0张")
            return True
        
        # 解析图片ID
        image_ids = latest_journal.images.split(",")
        image_count = len(image_ids)
        
        print(f"📷 图片数量: {image_count}张")
        print(f"📋 图片ID列表: {image_ids}")
        
        # 检查每张图片的详细信息
        for i, image_id in enumerate(image_ids, 1):
            image_id = image_id.strip()  # 去除可能的空格
            
            try:
                image = db.query(Image).filter(Image.id == int(image_id)).first()
                if image:
                    print(f"\n  图片 {i} (ID: {image_id}):")
                    print(f"    - 文件名: {image.filename}")
                    print(f"    - 文件路径: {image.file_path}")
                    print(f"    - 所属用户ID: {image.user_id}")
                    print(f"    - 文件大小: {image.file_size:,} bytes")
                    print(f"    - 上传时间: {image.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 检查文件是否实际存在
                    if os.path.exists(image.file_path):
                        actual_size = os.path.getsize(image.file_path)
                        print(f"    - 文件状态: ✅ 存在 (实际大小: {actual_size:,} bytes)")
                    else:
                        print(f"    - 文件状态: ❌ 不存在")
                else:
                    print(f"\n  图片 {i} (ID: {image_id}): ❌ 在数据库中不存在")
            except ValueError:
                print(f"\n  图片 {i}: ❌ 无效的ID '{image_id}'")
            except Exception as e:
                print(f"\n  图片 {i} (ID: {image_id}): ❌ 查询失败 - {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_latest_journal_images_detail()
