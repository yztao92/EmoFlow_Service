#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看所有用户日记的脚本
功能：查询数据库中所有用户的日记内容
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any

def connect_to_database():
    """连接到用户数据库"""
    try:
        conn = sqlite3.connect('database/users.db')
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        return None

def get_all_users_with_journals() -> List[Dict[str, Any]]:
    """获取所有有日记的用户及其日记"""
    conn = connect_to_database()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # 查询所有有日记的用户
        query = """
        SELECT DISTINCT 
            u.id as user_id,
            u.apple_user_id,
            u.email,
            u.name,
            u.heart,
            u.is_member,
            u.birthday,
            u.membership_expires_at,
            u.created_at as user_created_at
        FROM users u
        INNER JOIN journals j ON u.id = j.user_id
        ORDER BY u.id
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        result = []
        for user in users:
            # 获取该用户的所有日记
            journal_query = """
            SELECT 
                id, title, content, content_html, content_plain,
                content_format, is_safe, messages, session_id,
                emotion, memory_point, created_at, updated_at
            FROM journals 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            """
            
            cursor.execute(journal_query, (user['user_id'],))
            journals = cursor.fetchall()
            
            user_data = {
                'user_id': user['user_id'],
                'apple_user_id': user['apple_user_id'],
                'email': user['email'],
                'name': user['name'] or f"用户{user['user_id']}",
                'heart': user['heart'],
                'is_member': bool(user['is_member']),
                'birthday': user['birthday'],
                'membership_expires_at': user['membership_expires_at'],
                'user_created_at': user['user_created_at'],
                'journals_count': len(journals),
                'journals': []
            }
            
            for journal in journals:
                journal_data = {
                    'id': journal['id'],
                    'title': journal['title'],
                    'content': journal['content'],
                    'content_html': journal['content_html'],
                    'content_plain': journal['content_plain'],
                    'content_format': journal['content_format'],
                    'is_safe': bool(journal['is_safe']),
                    'emotion': journal['emotion'],
                    'memory_point': journal['memory_point'],
                    'created_at': journal['created_at'],
                    'updated_at': journal['updated_at']
                }
                
                # 处理messages字段（JSON格式）
                if journal['messages']:
                    try:
                        messages = json.loads(journal['messages'])
                        journal_data['messages'] = messages
                    except json.JSONDecodeError:
                        journal_data['messages'] = journal['messages']
                else:
                    journal_data['messages'] = []
                
                user_data['journals'].append(journal_data)
            
            result.append(user_data)
        
        return result
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return []
    finally:
        conn.close()

def display_journals_summary(users_data: List[Dict[str, Any]]):
    """显示日记摘要信息"""
    print("=" * 80)
    print("📚 所有用户日记摘要")
    print("=" * 80)
    
    total_users = len(users_data)
    total_journals = sum(user['journals_count'] for user in users_data)
    
    print(f"👥 总用户数: {total_users}")
    print(f"📝 总日记数: {total_journals}")
    print("=" * 80)
    
    for i, user in enumerate(users_data, 1):
        print(f"\n👤 用户 {i}: {user['name']}")
        print(f"   📧 邮箱: {user['email'] or '未设置'}")
        print(f"   ❤️ 心数: {user['heart']}")
        print(f"   👑 会员: {'是' if user['is_member'] else '否'}")
        print(f"   📅 注册时间: {user['user_created_at']}")
        print(f"   📝 日记数量: {user['journals_count']}")
        
        if user['journals']:
            print("   📖 日记列表:")
            for j, journal in enumerate(user['journals'][:5], 1):  # 只显示前5篇
                print(f"      {j}. {journal['title']}")
                print(f"         情绪: {journal['emotion'] or '未标记'}")
                print(f"         时间: {journal['created_at']}")
                if journal['memory_point']:
                    print(f"         记忆点: {journal['memory_point'][:100]}...")
                print()
            
            if len(user['journals']) > 5:
                print(f"      ... 还有 {len(user['journals']) - 5} 篇日记")
        
        print("-" * 60)

def display_detailed_journals(users_data: List[Dict[str, Any]], user_id: int = None):
    """显示详细的日记内容"""
    print("\n" + "=" * 80)
    print("📖 详细日记内容")
    print("=" * 80)
    
    for user in users_data:
        if user_id and user['user_id'] != user_id:
            continue
            
        print(f"\n👤 用户: {user['name']} (ID: {user['user_id']})")
        print("=" * 60)
        
        for i, journal in enumerate(user['journals'], 1):
            print(f"\n📝 日记 {i}: {journal['title']}")
            print(f"   创建时间: {journal['created_at']}")
            print(f"   情绪标签: {journal['emotion'] or '未标记'}")
            print(f"   内容格式: {journal['content_format']}")
            print(f"   安全状态: {'安全' if journal['is_safe'] else '待检查'}")
            
            # 显示内容
            if journal['content_plain']:
                content = journal['content_plain']
            elif journal['content_html']:
                content = journal['content_html']
            else:
                content = journal['content']
            
            print(f"   内容预览: {content[:200]}...")
            
            # 显示记忆点
            if journal['memory_point']:
                print(f"   记忆点: {journal['memory_point']}")
            
            # 显示对话历史
            if journal['messages'] and len(journal['messages']) > 0:
                print(f"   对话轮次: {len(journal['messages'])}")
            
            print("-" * 40)

def main():
    """主函数"""
    print("🔍 正在查询所有用户日记...")
    
    # 获取所有用户日记数据
    users_data = get_all_users_with_journals()
    
    if not users_data:
        print("❌ 没有找到任何用户日记数据")
        return
    
    # 显示摘要信息
    display_journals_summary(users_data)
    
    # 询问是否查看详细内容
    while True:
        choice = input("\n请选择操作:\n1. 查看所有日记详细内容\n2. 查看特定用户的日记\n3. 退出\n请输入选择 (1-3): ").strip()
        
        if choice == '1':
            display_detailed_journals(users_data)
        elif choice == '2':
            try:
                user_id = int(input("请输入用户ID: "))
                display_detailed_journals(users_data, user_id)
            except ValueError:
                print("❌ 请输入有效的用户ID")
        elif choice == '3':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请输入 1-3")

if __name__ == "__main__":
    main()

