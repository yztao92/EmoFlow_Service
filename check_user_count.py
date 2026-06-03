#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时脚本：查询用户数量
"""

from database_models import SessionLocal, User

def count_users():
    """统计用户数量"""
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_subscribers = db.query(User).filter(User.subscription_status == "active").count()
        inactive_users = db.query(User).filter(User.subscription_status == "inactive").count()
        expired_subscribers = db.query(User).filter(User.subscription_status == "expired").count()
        
        print("=" * 50)
        print("📊 用户统计信息")
        print("=" * 50)
        print(f"总用户数: {total_users}")
        print(f"   - 有效订阅用户 (active): {active_subscribers}")
        print(f"   - 普通用户 (inactive): {inactive_users}")
        print(f"   - 过期订阅用户 (expired): {expired_subscribers}")
        print("=" * 50)
        
        # 显示所有用户的简要信息
        if total_users > 0:
            print("\n所有用户:")
            users = db.query(User).order_by(User.id).all()
            for user in users:
                print(f"  ID: {user.id}, 姓名: {user.name or '未设置'}, 邮箱: {user.email or '未设置'}, "
                      f"订阅状态: {user.subscription_status}, 心心: {user.heart}")
        
    finally:
        db.close()

if __name__ == "__main__":
    count_users()


