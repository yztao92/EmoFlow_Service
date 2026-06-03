#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询有效订阅用户的过期时间
"""

from database_models import SessionLocal, User
from datetime import datetime, timezone

def check_active_subscriptions():
    """查询所有有效订阅用户的过期时间"""
    db = SessionLocal()
    try:
        # 查询所有有效订阅用户
        active_users = db.query(User).filter(
            User.subscription_status == "active"
        ).all()
        
        print("=" * 60)
        print("📊 有效订阅用户信息")
        print("=" * 60)
        print(f"总共有 {len(active_users)} 个有效订阅用户\n")
        
        if active_users:
            now = datetime.now(timezone.utc)
            for user in active_users:
                expires_at = user.subscription_expires_at
                if expires_at:
                    # 确保时区一致性
                    if expires_at.tzinfo is None:
                        # 如果 expires_at 没有时区信息，假设是 UTC
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    
                    # 计算剩余时间
                    time_diff = expires_at - now
                    days_remaining = time_diff.days
                    hours_remaining = time_diff.seconds // 3600
                    minutes_remaining = (time_diff.seconds % 3600) // 60
                    
                    print(f"用户 ID: {user.id}")
                    print(f"  姓名: {user.name or '未设置'}")
                    print(f"  邮箱: {user.email or '未设置'}")
                    print(f"  产品 ID: {user.subscription_product_id}")
                    print(f"  过期时间: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    if days_remaining >= 0:
                        print(f"  剩余时间: {days_remaining} 天 {hours_remaining} 小时 {minutes_remaining} 分钟")
                    else:
                        print(f"  已过期: {-days_remaining} 天前")
                    
                    if days_remaining < 0:
                        print(f"  ⚠️ 状态: 已过期但状态未更新")
                    elif days_remaining <= 7:
                        print(f"  ⚠️ 状态: 即将过期（{days_remaining} 天后）")
                    else:
                        print(f"  ✅ 状态: 正常")
                    print(f"  自动续费: {'是' if user.auto_renew_status else '否'}")
                    print(f"  环境: {user.subscription_environment}")
                    print(f"  心心: {user.heart}")
                    print("-" * 60)
                else:
                    print(f"用户 ID: {user.id}")
                    print(f"  姓名: {user.name or '未设置'}")
                    print(f"  ⚠️ 过期时间未设置")
                    print("-" * 60)
        else:
            print("当前没有有效订阅用户")
        
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    check_active_subscriptions()

