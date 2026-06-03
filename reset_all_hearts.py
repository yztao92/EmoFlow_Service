#!/usr/bin/env python3
"""
重置所有用户心心为100的脚本
"""

import os
import sys
import logging
from database_models import User, SessionLocal
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def reset_all_users_heart():
    """
    重置所有用户的心心：会员用户重置为100，普通用户重置为10
    """
    try:
        logging.info("🕛 开始执行：重置所有用户heart值")
        
        db = SessionLocal()
        try:
            # 获取所有用户
            users = db.query(User).all()
            total_users = len(users)
            logging.info(f"📊 当前共有 {total_users} 个用户")
            
            if total_users == 0:
                logging.warning("⚠️ 没有找到任何用户")
                return True
            
            inactive_count = 0
            active_count = 0
            
            for user in users:
                if user.subscription_status == "active":
                    user.heart = 100
                    active_count += 1
                else:
                    user.heart = 10
                    inactive_count += 1
            
            db.commit()
            
            logging.info(f"✅ 成功重置 {total_users} 个用户: {active_count}个会员重置为100, {inactive_count}个普通用户重置为10")
            return True
            
        except Exception as e:
            db.rollback()
            logging.error(f"❌ 数据库操作失败：{e}")
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
    print("=" * 60)
    print("💖 用户心心重置脚本")
    print("=" * 60)
    
    # 确认操作
    confirm = input("⚠️ 确定要重置所有用户的心心为100吗？(y/N): ")
    if confirm.lower() != 'y':
        print("❌ 操作已取消")
        return
    
    # 执行重置
    success = reset_all_users_heart()
    
    if success:
        print("🎉 重置完成！")
    else:
        print("💥 重置失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
