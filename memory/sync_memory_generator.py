#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步记忆点生成器
功能：在日记生成后直接调用，同步生成记忆点并更新数据库
"""

import os
import sys
import logging
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from database_models import SessionLocal, Journal
from llm.llm_factory import chat_with_llm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_memory_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_memory_point_for_journal(journal_id: int) -> bool:
    """
    为指定日记同步生成记忆点
    功能：直接调用LLM生成记忆点，并更新数据库
    
    参数:
        journal_id: 日记ID
        
    返回:
        bool: 是否成功生成记忆点
    """
    db = SessionLocal()
    try:
        # 获取日记信息
        journal = db.query(Journal).filter(Journal.id == journal_id).first()
        if not journal:
            logger.warning(f"⚠️  日记 {journal_id} 不存在，跳过")
            return False
        
        # 检查是否已有记忆点
        if journal.memory_point:
            logger.info(f"⏭️  日记 {journal_id} 已有记忆点，跳过")
            return True
        
        logger.info(f"📝 开始为日记 {journal_id} 生成记忆点...")
        
        # 生成记忆点
        memory_point = _generate_memory_point(journal)
        
        if memory_point:
            # 更新日记的记忆点
            journal.memory_point = memory_point
            db.commit()
            logger.info(f"✅ 日记 {journal_id} 记忆点生成成功: {memory_point[:50]}...")
            return True
        else:
            logger.warning(f"⚠️  日记 {journal_id} 记忆点生成失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 为日记 {journal_id} 生成记忆点失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def _generate_memory_point(journal: Journal) -> Optional[str]:
    """
    为单篇日记生成记忆点
    """
    try:
        # 获取日记内容
        content = journal.content
        
        # 构建分析提示词
        prompt = _create_analysis_prompt()
        prompt = prompt.format(journal_content=content)
        
        # 调用LLM进行分析
        response = chat_with_llm(prompt)
        
        # 清理响应内容
        memory_point = response.strip()
        
        # 移除可能的引号
        if memory_point.startswith('"') and memory_point.endswith('"'):
            memory_point = memory_point[1:-1]
        elif memory_point.startswith('"') and memory_point.endswith('"'):
            memory_point = memory_point[1:-1]
        
        return memory_point
        
    except Exception as e:
        logger.error(f"❌ 生成记忆点失败: {e}")
        return None

def _create_analysis_prompt() -> str:
    """
    创建记忆点分析的提示词
    """
    return """
你是一个专业的用户心理分析师，需要基于用户的日记内容，生成一个详细的记忆点总结。

## 分析要求：
请仔细分析这篇日记，生成一个包含以下要素的记忆点总结：

1. **核心事件**：发生了什么重要的事情
2. **具体细节**：包含关键的人物、地点、时间、结果等
3. **情感状态**：用户的感受和情绪变化
4. **影响意义**：这件事对用户的影响或意义

## 输出要求：
- 总结要详细具体，包含关键信息
- 长度控制在30-50字之间
- 用客观的语言描述，避免过度主观判断
- 突出日记中最重要、最有价值的内容
- 如果涉及人际关系，要说明具体对象
- 如果涉及工作/学习，要说明具体领域或成果
- 输出格式：直接输出记忆点内容，不要包含引号或时间前缀

## 示例格式：
和女友因为旅行计划产生分歧，讨论了预算和目的地，最终达成妥协
工作压力大，连续加班到深夜，感觉身心疲惫，但项目有了重要进展
朋友聚会很开心，大家分享近况，回忆大学时光，心情愉悦放松
考试失败，数学科目成绩不理想，感到失落，决定加强复习

## 日记内容：
{journal_content}

请基于以上要求，生成一个详细的记忆点总结：
"""
