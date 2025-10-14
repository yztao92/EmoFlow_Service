#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量创建展示用日记数据
为 Nick 用户创建 8月、9月、10月的日记
"""

import sys
import os
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

from database_models.database import SessionLocal
from database_models.journal import Journal
from llm.llm_factory import chat_with_llm
from prompts.journal_prompts import get_journal_generation_prompt

# Nick 用户的 ID
NICK_USER_ID = 13

# 情绪类型和权重（用于随机分配）
EMOTIONS = [
    ("angry", 10),      # 愤怒 10%
    ("sad", 10),        # 悲伤 10%
    ("unhappy", 15),    # 不开心 15%
    ("happy", 25),      # 开心 25%
    ("peaceful", 30),   # 平和 30%
    ("happiness", 5),   # 幸福 5%
    ("tired", 10),      # 疲惫 10%
    ("unpeaceful", 5),  # 不安 5%
]

# 日记生成配置

def weighted_random_choice(items):
    """根据权重随机选择"""
    emotions, weights = zip(*items)
    return random.choices(emotions, weights=weights, k=1)[0]

def generate_journal_content(emotion: str, date_str: str) -> str:
    """使用千问LLM直接生成日记内容"""
    prompt = f"""请生成一篇{emotion}情绪的心情日记，要求：
1. 用第一人称"我"的口吻
2. 字数控制在80-100字
3. 内容要真实自然，像真实的日常记录
4. 不要提到AI、对话等
5. 以事件和场景为主，情绪为辅
6. 符合{emotion}的情绪氛围

请直接输出日记内容："""
    
    try:
        # 调用千问LLM生成日记
        content = chat_with_llm(prompt)
        return content.strip()
    except Exception as e:
        print(f"⚠️ LLM生成失败，使用简单模板: {e}")
        # 如果LLM失败，使用简单模板
        fallback_templates = {
            "happy": "今天心情很好，做了很多事情，感觉生活充满了希望。",
            "sad": "今天有些难过，心里有点沉重，希望明天会更好。",
            "angry": "今天遇到了让人生气的事情，心情不太好。",
            "peaceful": "今天很平静，享受了安静的时光。",
            "unhappy": "今天不太开心，感觉有些失落。",
            "tired": "今天很累，需要好好休息一下。",
            "happiness": "今天特别幸福，感受到了生活的美好。",
            "unpeaceful": "今天心里有些不安，感觉有些焦虑。"
        }
        return fallback_templates.get(emotion, "今天记录一下心情。")

def generate_memory_point(date_str: str, content: str, emotion: str) -> str:
    """使用千问LLM生成记忆点"""
    prompt = f"""请根据以下日记内容生成一个简洁的记忆点摘要，要求：
1. 格式：{date_str} + 简短描述（10-15字）
2. 突出主要事件或感受
3. 语言简洁自然

日记内容：{content}
情绪：{emotion}

请直接输出记忆点："""
    
    try:
        # 调用千问LLM生成记忆点
        memory_point = chat_with_llm(prompt)
        return memory_point.strip()
    except Exception as e:
        print(f"⚠️ 记忆点LLM生成失败，使用简单模板: {e}")
        # 如果LLM失败，使用简单模板
        short_content = content[:20].replace('\n', ' ')
        return f"{date_str} {short_content}"

def create_journals_for_date_range(start_date, end_date):
    """为日期范围创建日记"""
    db = SessionLocal()
    created_count = 0
    
    try:
        current_date = start_date
        while current_date <= end_date:
            # 随机选择情绪
            emotion = weighted_random_choice(EMOTIONS)
            
            date_str = current_date.strftime('%Y-%m-%d')
            
            print(f"\n📅 创建日记: {date_str} | 情绪: {emotion}")
            
            # 生成日记内容
            content = generate_journal_content(emotion, date_str)
            print(f"   内容: {content[:50]}...")
            
            # 生成记忆点
            memory_point = generate_memory_point(date_str, content, emotion)
            print(f"   记忆点: {memory_point}")
            
            # 设置创建时间（随机在当天的某个时间）
            hour = random.randint(8, 22)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            created_at = current_date.replace(hour=hour, minute=minute, second=second)
            
            # 创建日记记录
            journal = Journal(
                user_id=NICK_USER_ID,
                content=content,
                session_id="demo",
                emotion=emotion,
                memory_point=memory_point,
                created_at=created_at,
                updated_at=created_at
            )
            
            db.add(journal)
            db.commit()
            db.refresh(journal)
            
            created_count += 1
            print(f"   ✅ 已创建日记 ID={journal.id}")
            
            # 移到下一天
            current_date += timedelta(days=1)
    
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
    
    return created_count

def main():
    print("=" * 80)
    print("📝 开始批量创建展示用日记")
    print("=" * 80)
    print(f"目标用户: Nick (ID={NICK_USER_ID})")
    print()
    
    # 定义日期范围（使用东八区时区）
    tz = timezone(timedelta(hours=8))
    
    # 八月份: 2025-08-01 到 2025-08-31
    august_start = datetime(2025, 8, 1, tzinfo=tz)
    august_end = datetime(2025, 8, 31, tzinfo=tz)
    
    # 九月份: 2025-09-01 到 2025-09-30
    september_start = datetime(2025, 9, 1, tzinfo=tz)
    september_end = datetime(2025, 9, 30, tzinfo=tz)
    
    # 十月份: 2025-10-01 到 2025-10-14
    october_start = datetime(2025, 10, 1, tzinfo=tz)
    october_end = datetime(2025, 10, 14, tzinfo=tz)
    
    print("📆 创建日期范围:")
    print(f"   八月份: {august_start.strftime('%Y-%m-%d')} ~ {august_end.strftime('%Y-%m-%d')} (31天)")
    print(f"   九月份: {september_start.strftime('%Y-%m-%d')} ~ {september_end.strftime('%Y-%m-%d')} (30天)")
    print(f"   十月份: {october_start.strftime('%Y-%m-%d')} ~ {october_end.strftime('%Y-%m-%d')} (14天)")
    print(f"   总计: 75篇日记")
    print()
    print("🎭 情绪分布:")
    for emotion, weight in EMOTIONS:
        print(f"   {emotion}: {weight}%")
    print()
    print("📝 内容特点:")
    print("   - 情绪随机分配")
    print("   - 使用千问LLM生成真实日记内容")
    print("   - 字数控制在80-100字")
    print("   - 自动生成记忆点摘要")
    print("   - 完全符合数据库格式")
    print()
    
    input("按 Enter 键开始创建...")
    print()
    
    # 创建八月份日记
    print("\n" + "=" * 80)
    print("🗓️  创建八月份日记")
    print("=" * 80)
    august_count = create_journals_for_date_range(august_start, august_end)
    
    # 创建九月份日记
    print("\n" + "=" * 80)
    print("🗓️  创建九月份日记")
    print("=" * 80)
    september_count = create_journals_for_date_range(september_start, september_end)
    
    # 创建十月份日记
    print("\n" + "=" * 80)
    print("🗓️  创建十月份日记")
    print("=" * 80)
    october_count = create_journals_for_date_range(october_start, october_end)
    
    # 总结
    total = august_count + september_count + october_count
    print("\n" + "=" * 80)
    print("✅ 日记创建完成！")
    print("=" * 80)
    print(f"八月份: {august_count} 篇")
    print(f"九月份: {september_count} 篇")
    print(f"十月份: {october_count} 篇")
    print(f"总计: {total} 篇")
    print("=" * 80)

if __name__ == "__main__":
    main()

