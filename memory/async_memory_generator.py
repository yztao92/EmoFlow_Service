#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步记忆点生成器
功能：在日记生成后异步生成记忆点，不影响主流程
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime
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
        logging.FileHandler('async_memory_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AsyncMemoryGenerator:
    """
    异步记忆点生成器
    功能：在后台异步生成日记的记忆点，不影响主流程
    """
    
    def __init__(self):
        self.analysis_prompt = self._create_analysis_prompt()
        self.processing_queue = []
        self.is_running = False
        self.worker_thread = None
    
    def _create_analysis_prompt(self) -> str:
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
    
    def add_journal_to_queue(self, journal_id: int) -> bool:
        """
        将日记添加到处理队列
        """
        try:
            if journal_id not in self.processing_queue:
                self.processing_queue.append(journal_id)
                logger.info(f"✅ 日记 {journal_id} 已添加到记忆点生成队列")
                
                # 如果工作线程没有运行，启动它
                if not self.is_running:
                    self._start_worker()
                
                return True
            else:
                logger.info(f"⏭️  日记 {journal_id} 已在队列中，跳过")
                return False
                
        except Exception as e:
            logger.error(f"❌ 添加日记到队列失败: {e}")
            return False
    
    def _start_worker(self):
        """
        启动后台工作线程
        """
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("🚀 异步记忆点生成器已启动")
    
    def _worker_loop(self):
        """
        工作线程主循环
        """
        while self.is_running:
            try:
                if self.processing_queue:
                    # 处理队列中的日记
                    journal_id = self.processing_queue.pop(0)
                    self._process_single_journal(journal_id)
                else:
                    # 队列为空，等待一段时间
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ 工作线程异常: {e}")
                time.sleep(5)  # 异常后等待更长时间
        
        logger.info("🛑 异步记忆点生成器已停止")
    
    def _process_single_journal(self, journal_id: int):
        """
        处理单篇日记，生成记忆点
        """
        db = SessionLocal()
        try:
            # 获取日记信息
            journal = db.query(Journal).filter(Journal.id == journal_id).first()
            if not journal:
                logger.warning(f"⚠️  日记 {journal_id} 不存在，跳过")
                return
            
            # 检查是否已有记忆点
            if journal.memory_point:
                logger.info(f"⏭️  日记 {journal_id} 已有记忆点，跳过")
                return
            
            logger.info(f"📝 开始为日记 {journal_id} 生成记忆点...")
            
            # 生成记忆点
            memory_point = self._generate_memory_point(journal)
            
            if memory_point:
                # 更新日记的记忆点
                journal.memory_point = memory_point
                db.commit()
                logger.info(f"✅ 日记 {journal_id} 记忆点生成成功: {memory_point[:50]}...")
            else:
                logger.warning(f"⚠️  日记 {journal_id} 记忆点生成失败")
                
        except Exception as e:
            logger.error(f"❌ 处理日记 {journal_id} 失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _generate_memory_point(self, journal: Journal) -> Optional[str]:
        """
        为单篇日记生成记忆点
        """
        try:
            # 获取日记内容
            content = journal.content
            
            # 构建分析提示词
            prompt = self.analysis_prompt.format(journal_content=content)
            
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
    
    def stop(self):
        """
        停止异步生成器
        """
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        logger.info("🛑 异步记忆点生成器已停止")

# 全局实例
_async_generator = None

def get_async_memory_generator() -> AsyncMemoryGenerator:
    """
    获取全局异步记忆点生成器实例
    """
    global _async_generator
    if _async_generator is None:
        _async_generator = AsyncMemoryGenerator()
    return _async_generator

def add_journal_for_memory_generation(journal_id: int) -> bool:
    """
    为指定日记添加记忆点生成任务
    这是主要的API接口，在日记生成后调用
    """
    try:
        generator = get_async_memory_generator()
        return generator.add_journal_to_queue(journal_id)
    except Exception as e:
        logger.error(f"❌ 添加记忆点生成任务失败: {e}")
        return False
