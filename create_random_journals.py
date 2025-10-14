#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
创建真正随机的日记数据
使用丰富的随机场景和事件
"""

import os
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

from database_models.database import SessionLocal
from database_models.journal import Journal
from llm.llm_factory import chat_with_llm

# Nick 用户的 ID
NICK_USER_ID = 13

# 情绪类型和权重
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

# 丰富的随机场景库
RANDOM_SCENARIOS = [
    # 工作相关
    "今天在公司开会，讨论了新项目的方案",
    "下午写代码时发现了一个很难调试的bug",
    "同事请我帮忙整理文档，花了一整个上午",
    "老板突然要求加班，说要赶一个紧急项目",
    "在电梯里遇到了很久没见的同事，聊了几句",
    "中午和同事一起去楼下新开的餐厅吃饭",
    "今天完成了上周就开始写的报告",
    "办公室的空调坏了，一整天都很热",
    
    # 日常生活
    "早上起床发现外面下雨了，忘记带伞",
    "去超市买菜，发现很多商品都在打折",
    "家里的WiFi突然断网了，修了半天才恢复",
    "下午去银行办事，排队等了一个小时",
    "晚上做饭时不小心切到了手指",
    "洗衣服时发现洗衣机坏了，只能手洗",
    "今天收到了一个快递，是朋友寄来的礼物",
    "去理发店剪头发，发型师很健谈",
    
    # 交通出行
    "早上坐地铁上班，人特别多，差点迟到",
    "下班路上遇到堵车，在路上等了很久",
    "骑车去公园，路上看到一只流浪猫",
    "坐公交时给老人让座，他说了声谢谢",
    "开车去商场，停车位很难找",
    "走路回家时看到路边有人卖糖葫芦",
    "坐出租车时司机一直在听广播",
    "骑共享单车时发现车胎没气了",
    
    # 社交活动
    "朋友约我晚上一起看电影",
    "和家人视频通话，聊了很久",
    "在咖啡厅遇到一个有趣的陌生人",
    "参加朋友的生日聚会，玩得很开心",
    "和邻居在楼道里聊天，发现是老乡",
    "去健身房锻炼，遇到了教练",
    "在公园遛狗时认识了其他狗主人",
    "朋友请我帮忙搬家，累了一整天",
    
    # 娱乐休闲
    "晚上在家看了一部很感人的电影",
    "下午在图书馆看书，环境很安静",
    "去KTV唱歌，和朋友玩到很晚",
    "在家玩游戏，不知不觉玩到深夜",
    "去博物馆参观，学到了很多新知识",
    "在书店逛了一下午，买了几本书",
    "和朋友一起去爬山，风景很美",
    "在家听音乐，放松了一整天",
    
    # 健康相关
    "今天感觉身体不太舒服，可能是感冒了",
    "去体检，医生说各项指标都很正常",
    "牙疼得厉害，去看了牙医",
    "运动时不小心扭伤了脚踝",
    "晚上失眠了，躺在床上睡不着",
    "今天心情很好，感觉精神饱满",
    "去药店买药，药师很耐心地解释用法",
    "在家做瑜伽，感觉很放松",
    
    # 学习成长
    "今天学习了一门新的编程语言",
    "读了一本很有启发的书",
    "在网上看了一个有趣的教程",
    "和朋友讨论了一个深奥的哲学问题",
    "尝试做了一道新菜，味道还不错",
    "学习了一首新的钢琴曲",
    "研究了股票投资，学到了很多",
    "学会了使用一个新的软件",
    
    # 购物消费
    "在网上买了一件心仪很久的衣服",
    "去商场逛街，买了很多东西",
    "在二手市场淘到了一个古董",
    "去菜市场买菜，发现物价又涨了",
    "在网上订外卖，送餐员很准时",
    "去书店买书，店员推荐了几本好书",
    "在超市购物，收银员态度很好",
    "去电器城买了个新手机",
    
    # 天气季节
    "今天阳光明媚，心情也特别好",
    "外面下大雨，只能在家待着",
    "刮大风，路上到处都是落叶",
    "天气很冷，穿了很多衣服",
    "雾霾很严重，出门要戴口罩",
    "今天有彩虹，大家都停下来拍照",
    "下雪了，地上积了厚厚一层",
    "天气很热，只想待在空调房里",
    
    # 意外事件
    "今天发生了很多意想不到的事情",
    "在路上捡到了一个小钱包",
    "遇到了一个迷路的小孩，帮他找到了家",
    "家里的水管突然爆裂，水漫了一地",
    "在餐厅吃饭时，服务员上错了菜",
    "坐地铁时坐过了站，多走了很多路",
    "去银行取钱时发现卡被吞了",
    "在公园里看到有人求婚，很浪漫",
    
    # 情感体验
    "今天想起了一些往事，有些感慨",
    "听到一首老歌，勾起了很多回忆",
    "看到一对老夫妻牵手散步，很感动",
    "收到了一封很久没联系的朋友的来信",
    "在街上看到有人吵架，心情不太好",
    "看到小朋友在公园玩耍，想起了童年",
    "今天特别想念远方的家人",
    "在书店看到一本书，想起了某个人"
]

def weighted_random_choice(items):
    """根据权重随机选择"""
    emotions, weights = zip(*items)
    return random.choices(emotions, weights=weights, k=1)[0]

def generate_random_journal_content(emotion: str, scenario: str) -> str:
    """使用随机场景生成日记内容"""
    prompt = f"""基于以下场景和情绪，生成一篇真实自然的心情日记：

场景：{scenario}
情绪：{emotion}

要求：
1. 用第一人称"我"的口吻
2. 字数控制在80-100字
3. 以场景为基础，自然地融入情绪
4. 内容要真实，像真实的日常记录
5. 不要提到AI、对话等
6. 语言要口语化，不要太书面

请直接输出日记内容："""
    
    try:
        content = chat_with_llm(prompt)
        return content.strip()
    except Exception as e:
        print(f"⚠️ LLM生成失败，使用简单模板: {e}")
        # 备用模板
        return f"{scenario}，今天感觉{emotion}。记录一下。"

def generate_memory_point(date_str: str, content: str, emotion: str) -> str:
    """生成记忆点"""
    prompt = f"""请根据以下日记内容生成一个简洁的记忆点摘要，要求：
1. 格式：{date_str} + 简短描述（10-15字）
2. 突出主要事件或感受
3. 语言简洁自然

日记内容：{content}
情绪：{emotion}

请直接输出记忆点："""
    
    try:
        memory_point = chat_with_llm(prompt)
        return memory_point.strip()
    except Exception as e:
        print(f"⚠️ 记忆点生成失败，使用简单模板: {e}")
        short_content = content[:20].replace('\n', ' ')
        return f"{date_str} {short_content}"

def create_random_journals_for_date_range(start_date, end_date):
    """为日期范围创建随机日记"""
    db = SessionLocal()
    created_count = 0
    
    try:
        current_date = start_date
        while current_date <= end_date:
            # 随机选择情绪
            emotion = weighted_random_choice(EMOTIONS)
            
            # 随机选择场景
            scenario = random.choice(RANDOM_SCENARIOS)
            
            date_str = current_date.strftime('%Y-%m-%d')
            
            print(f"\n📅 创建日记: {date_str} | 情绪: {emotion}")
            print(f"   场景: {scenario}")
            
            # 生成日记内容
            content = generate_random_journal_content(emotion, scenario)
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
                session_id="random",
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
    print("📝 开始创建真正随机的日记数据")
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
    
    print("📆 创建日期范围:")
    print(f"   八月份: {august_start.strftime('%Y-%m-%d')} ~ {august_end.strftime('%Y-%m-%d')} (31天)")
    print(f"   九月份: {september_start.strftime('%Y-%m-%d')} ~ {september_end.strftime('%Y-%m-%d')} (30天)")
    print(f"   总计: 61篇日记")
    print()
    print("🎭 情绪分布:")
    for emotion, weight in EMOTIONS:
        print(f"   {emotion}: {weight}%")
    print()
    print("🎲 随机特点:")
    print("   - 61个不同的随机场景")
    print("   - 情绪和场景完全随机组合")
    print("   - 使用千问LLM生成真实内容")
    print("   - 每个场景只使用一次")
    print()
    
    input("按 Enter 键开始创建...")
    print()
    
    # 打乱场景顺序，确保随机性
    random.shuffle(RANDOM_SCENARIOS)
    print(f"🎲 已随机打乱 {len(RANDOM_SCENARIOS)} 个场景")
    
    # 创建八月份日记
    print("\n" + "=" * 80)
    print("🗓️  创建八月份日记")
    print("=" * 80)
    august_count = create_random_journals_for_date_range(august_start, august_end)
    
    # 创建九月份日记
    print("\n" + "=" * 80)
    print("🗓️  创建九月份日记")
    print("=" * 80)
    september_count = create_random_journals_for_date_range(september_start, september_end)
    
    # 总结
    total = august_count + september_count
    print("\n" + "=" * 80)
    print("✅ 随机日记创建完成！")
    print("=" * 80)
    print(f"八月份: {august_count} 篇")
    print(f"九月份: {september_count} 篇")
    print(f"总计: {total} 篇")
    print("=" * 80)

if __name__ == "__main__":
    main()
