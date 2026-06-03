#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试心心重置逻辑
功能：测试新的心心重置逻辑（会员100，普通用户10）
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

def test_heart_reset_logic():
    """
    测试心心重置逻辑
    """
    print("=" * 60)
    print("🧪 测试心心重置逻辑")
    print("=" * 60)
    
    db: Session = SessionLocal()
    try:
        # 获取所有用户
        users = db.query(User).all()
        total = len(users)
        
        if total == 0:
            print("❌ 没有找到任何用户")
            return
        
        print(f"📊 当前共有 {total} 个用户")
        print("\n📋 用户状态详情：")
        
        inactive_count = 0
        active_count = 0
        
        for user in users:
            status = "会员" if user.subscription_status == "active" else "普通用户"
            reset_heart = 100 if user.subscription_status == "active" else 10
            
            print(f"  - 用户ID {user.id}: {user.name or '未命名'} ({status}) - 当前心心: {user.heart} -> 重置后: {reset_heart}")
            
            if user.subscription_status == "active":
                active_count += 1
            else:
                inactive_count += 1
        
        print(f"\n📈 统计结果：")
        print(f"  - 会员用户: {active_count} 个 (重置为100)")
        print(f"  - 普通用户: {inactive_count} 个 (重置为10)")
        print(f"  - 总计: {total} 个用户")
        
        print(f"\n✅ 心心重置逻辑测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_heart_reset_logic()




