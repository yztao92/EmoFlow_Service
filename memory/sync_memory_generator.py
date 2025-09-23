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
        
        # 获取图片分析内容
        image_analysis_content = _get_image_analysis_content(journal)
        
        # 构建分析提示词
        prompt = _create_analysis_prompt()
        prompt = prompt.format(
            journal_content=content,
            image_analysis=image_analysis_content
        )
        
        # 调用LLM进行分析
        response = chat_with_llm(prompt)
        
        # 清理响应内容
        memory_point = response.strip()
        
        # 移除可能的引号
        if memory_point.startswith('"') and memory_point.endswith('"'):
            memory_point = memory_point[1:-1]
        elif memory_point.startswith('"') and memory_point.endswith('"'):
            memory_point = memory_point[1:-1]
        
        # 添加时间前缀
        if journal.created_at:
            # 格式化为 "YYYY-MM-DD" 格式
            time_str = journal.created_at.strftime("%Y-%m-%d")
            memory_point = f"{time_str} {memory_point}"
        
        return memory_point
        
    except Exception as e:
        logger.error(f"❌ 生成记忆点失败: {e}")
        return None

def _get_image_analysis_content(journal: Journal) -> str:
    """
    获取日记关联图片的分析内容
    """
    try:
        if not journal.images:
            return ""
        
        # 解析图片ID列表
        image_ids = [int(id_str.strip()) for id_str in journal.images.split(",") if id_str.strip()]
        if not image_ids:
            return ""
        
        # 获取图片分析结果
        from database_models.database import SessionLocal
        from database_models.image import Image
        import json
        
        db = SessionLocal()
        try:
            images = db.query(Image).filter(Image.id.in_(image_ids)).all()
            
            analysis_parts = []
            for img in images:
                if img.analysis_result:
                    try:
                        # 解析JSON格式的分析结果
                        analysis_data = json.loads(img.analysis_result)
                        if isinstance(analysis_data, dict):
                            # 提取关键信息
                            summary = analysis_data.get('summary', '')
                            emotion = analysis_data.get('emotion', '')
                            objects = analysis_data.get('objects', [])
                            scene = analysis_data.get('scene', '')
                            
                            # 构建图片分析描述
                            img_desc = f"图片分析：{summary}"
                            if emotion:
                                img_desc += f"，情绪：{emotion}"
                            if scene:
                                img_desc += f"，场景：{scene}"
                            if objects:
                                img_desc += f"，包含：{', '.join(objects)}"
                            
                            analysis_parts.append(img_desc)
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，直接使用原始内容
                        analysis_parts.append(f"图片分析：{img.analysis_result}")
            
            return "；".join(analysis_parts) if analysis_parts else ""
            
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"⚠️ 获取图片分析内容失败: {e}")
        return ""

def _create_analysis_prompt() -> str:
    """
    生成简洁型记忆点：每篇日记只提炼一句话的核心事件
    """
    return """
你是"记忆点提炼器"。请从用户的日记中提取 **一句话核心记忆点**。

## 要求
- 一句话描述「发生了什么事」
- 保留关键信息（人物、事件、结果）
- 长度 ≤ 25 字
- 客观简洁，不做主观评价
- 不要带日期、引号或多余解释

## 示例
原文：今天加班到很晚，身心很疲惫  
记忆点：加班到深夜感到疲惫  

原文：和女友因为旅行计划产生分歧，讨论预算和目的地  
记忆点：与女友因旅行计划产生分歧  

原文：朋友聚会很开心，大家回忆大学时光  
记忆点：和朋友聚会聊天回忆大学  

## 日记内容
{journal_content}

## 图片分析
{image_analysis}

请基于以上规则，输出 1 条简洁记忆点：
""".strip()
