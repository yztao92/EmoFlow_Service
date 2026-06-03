#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户心心数量修改脚本
功能：修改指定用户ID的心心数量
使用方法：python update_user_heart.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database_models.database import SessionLocal
from database_models.user import User
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_user_heart(user_id: int, new_heart_count: int) -> bool:
    """
    修改指定用户的心心数量
    
    Args:
        user_id: 用户ID
        new_heart_count: 新的心心数量
        
    Returns:
        bool: 修改是否成功
    """
    db: Session = SessionLocal()
    try:
        # 查找用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"❌ 用户ID {user_id} 不存在")
            return False
        
        # 记录修改前的状态
        old_heart = user.heart
        logger.info(f"🔍 找到用户: ID={user.id}, 姓名='{user.name}', 当前心心数量={old_heart}")
        
        # 更新心心数量
        user.heart = new_heart_count
        db.commit()
        db.refresh(user)
        
        # 记录修改结果
        logger.info(f"✅ 修改成功: 用户ID {user_id} 的心心数量从 {old_heart} 修改为 {new_heart_count}")
        logger.info(f"📊 用户信息: ID={user.id}, 姓名='{user.name}', 心心数量={user.heart}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 修改失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 50)
    print("💖 用户心心数量修改工具")
    print("=" * 50)
    
    # 目标用户ID
    target_user_id = 13
    
    # 获取新的心心数量
    try:
        new_heart_count = input(f"请输入用户ID {target_user_id} 的新心心数量: ").strip()
        new_heart_count = int(new_heart_count)
        
        if new_heart_count < 0:
            print("❌ 心心数量不能为负数")
            return
            
    except ValueError:
        print("❌ 请输入有效的数字")
        return
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
        return
    
    # 确认修改
    print(f"\n🔍 即将修改用户ID {target_user_id} 的心心数量为: {new_heart_count}")
    confirm = input("确认修改吗？(y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes', '是']:
        print("👋 操作已取消")
        return
    
    # 执行修改
    print("\n🚀 开始修改...")
    success = update_user_heart(target_user_id, new_heart_count)
    
    if success:
        print(f"\n🎉 修改完成！用户ID {target_user_id} 的心心数量已更新为 {new_heart_count}")
    else:
        print(f"\n💥 修改失败！请检查用户ID {target_user_id} 是否存在")

if __name__ == "__main__":
    main()




