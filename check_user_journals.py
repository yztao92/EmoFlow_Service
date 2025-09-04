#!/usr/bin/env python3
"""
查看每个用户有多少篇日记的脚本
"""

import os
import sys
import logging
from database_models import User, Journal, SessionLocal
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_user_journals():
    """
    查看每个用户的日记数量统计
    """
    try:
        logging.info("🕛 开始查询用户日记统计")
        
        db = SessionLocal()
        try:
            # 查询所有用户及其日记数量
            from sqlalchemy import func
            
            # 使用左连接查询，确保没有日记的用户也显示出来
            results = db.query(
                User.id,
                User.name,
                User.email,
                User.apple_user_id,
                func.count(Journal.id).label('journal_count')
            ).outerjoin(Journal, User.id == Journal.user_id)\
             .group_by(User.id, User.name, User.email, User.apple_user_id)\
             .order_by(User.id).all()
            
            if not results:
                logging.warning("⚠️ 没有找到任何用户")
                return
            
            # 统计信息
            total_users = len(results)
            total_journals = sum(result.journal_count for result in results)
            users_with_journals = sum(1 for result in results if result.journal_count > 0)
            users_without_journals = total_users - users_with_journals
            
            print("=" * 80)
            print("📊 用户日记统计报告")
            print("=" * 80)
            print(f"总用户数: {total_users}")
            print(f"总日记数: {total_journals}")
            print(f"有日记的用户: {users_with_journals}")
            print(f"无日记的用户: {users_without_journals}")
            print("=" * 80)
            
            # 详细列表
            print(f"{'用户ID':<8} {'姓名':<15} {'邮箱':<25} {'日记数':<8} {'Apple ID'}")
            print("-" * 80)
            
            for result in results:
                user_id = result.id
                name = result.name or "未设置"
                email = result.email or "未设置"
                journal_count = result.journal_count
                apple_id = result.apple_user_id or "未设置"
                
                # 截断过长的字段
                if len(name) > 14:
                    name = name[:14] + "..."
                if len(email) > 24:
                    email = email[:24] + "..."
                if len(apple_id) > 20:
                    apple_id = apple_id[:20] + "..."
                
                print(f"{user_id:<8} {name:<15} {email:<25} {journal_count:<8} {apple_id}")
            
            print("=" * 80)
            
            # 按日记数量排序显示前10名
            print("\n🏆 日记数量排行榜 (前10名):")
            print("-" * 50)
            sorted_results = sorted(results, key=lambda x: x.journal_count, reverse=True)
            for i, result in enumerate(sorted_results[:10], 1):
                if result.journal_count > 0:
                    name = result.name or "未设置"
                    if len(name) > 20:
                        name = name[:20] + "..."
                    print(f"{i:2d}. {name:<25} - {result.journal_count} 篇日记")
            
            # 统计分布
            print(f"\n📈 日记数量分布:")
            print("-" * 30)
            ranges = [
                (0, 0, "无日记"),
                (1, 5, "1-5篇"),
                (6, 10, "6-10篇"),
                (11, 20, "11-20篇"),
                (21, 50, "21-50篇"),
                (51, 100, "51-100篇"),
                (101, float('inf'), "100篇以上")
            ]
            
            for min_count, max_count, label in ranges:
                if max_count == float('inf'):
                    count = sum(1 for r in results if r.journal_count >= min_count)
                else:
                    count = sum(1 for r in results if min_count <= r.journal_count <= max_count)
                print(f"{label:<10}: {count:3d} 人")
            
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
    print("📝 用户日记统计工具")
    print("=" * 50)
    
    if check_user_journals():
        print("\n🎉 统计完成！")
    else:
        print("\n❌ 统计失败，请查看日志获取详情。")

if __name__ == "__main__":
    main()
