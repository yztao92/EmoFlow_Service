#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户记忆点分析脚本
功能：通过LLM分析所有用户的日记，生成记忆点并直接存储到日记表
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from database_models import SessionLocal, User, Journal
from llm.llm_factory import chat_with_llm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UserMemoryAnalyzer:
    """
    用户记忆点分析器
    功能：分析用户日记，生成记忆点并直接存储到日记表
    """
    
    def __init__(self):
        self.db = SessionLocal()
        self.analysis_prompt = self._create_analysis_prompt()
    
    def _create_analysis_prompt(self) -> str:
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

请基于以上规则，输出 1 条简洁记忆点：
""".strip()
    
    def get_all_users_with_journals(self) -> List[Dict[str, Any]]:
        """
        获取所有有日记的用户
        """
        try:
            # 查询有日记的用户
            users_with_journals = self.db.query(User).join(Journal).distinct().all()
            
            result = []
            for user in users_with_journals:
                # 获取用户的所有日记
                journals = self.db.query(Journal).filter(Journal.user_id == user.id).order_by(Journal.created_at.desc()).all()
                
                if journals:
                    result.append({
                        'user': user,
                        'journals': journals
                    })
            
            logger.info(f"找到 {len(result)} 个有日记的用户")
            return result
            
        except Exception as e:
            logger.error(f"获取用户日记失败: {e}")
            return []

    def analyze_single_journal(self, journal: Journal) -> str:
        """
        分析单篇日记，生成记忆点
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
            
            logger.info(f"✅ 生成记忆点: {memory_point}")
            return memory_point
            
        except Exception as e:
            logger.error(f"分析日记失败: {e}")
            return "日记内容分析失败"

    def update_journal_memory_points(self, user: User, journals: List[Journal]) -> bool:
        """
        更新日记的记忆点，直接存储到journals表的memory_point字段
        """
        try:
            logger.info(f"用户 {user.name} 开始更新日记记忆点...")
            
            updated_count = 0
            for journal in journals:
                # 强制重新生成所有记忆点（使用新的低维记忆点格式）
                logger.info(f"  🔄 重新生成日记 {journal.id} 的记忆点...")
                
                # 生成记忆点
                memory_description = self.analyze_single_journal(journal)
                
                # 直接更新日记表的memory_point字段
                journal.memory_point = memory_description
                updated_count += 1
                
                logger.info(f"  ✅ 日记 {journal.id} 记忆点更新完成")
            
            # 提交更改
            self.db.commit()
            
            logger.info(f"✅ 成功更新用户 {user.name} 的 {updated_count} 篇日记记忆点")
            return True
            
        except Exception as e:
            logger.error(f"更新日记记忆点失败: {e}")
            self.db.rollback()
            return False

    def run_full_analysis(self):
        """
        运行完整的记忆点分析
        """
        logger.info("🚀 开始全量日记记忆点分析")
        
        try:
            # 1. 获取所有有日记的用户
            users_with_journals = self.get_all_users_with_journals()
            
            if not users_with_journals:
                logger.warning("没有找到有日记的用户")
                return
            
            # 2. 分析每个用户的日记
            analysis_results = []
            for user_data in users_with_journals:
                user = user_data['user']
                journals = user_data['journals']
                
                logger.info(f"📝 分析用户 {user.name} 的 {len(journals)} 篇日记")
                
                # 更新日记记忆点
                success = self.update_journal_memory_points(user, journals)
                
                if success:
                    analysis_results.append({
                        'user_id': user.id,
                        'user_name': user.name,
                        'journals_count': len(journals),
                        'status': 'success',
                        'update_time': datetime.now().isoformat()
                    })
                else:
                    analysis_results.append({
                        'user_id': user.id,
                        'user_name': user.name,
                        'journals_count': len(journals),
                        'status': 'failed',
                        'update_time': datetime.now().isoformat()
                    })
                
                logger.info(f"✅ 完成用户 {user.name} 的分析")
            
            # 3. 输出分析总结
            logger.info("=" * 60)
            logger.info("🎉 全量日记记忆点分析完成！")
            logger.info("=" * 60)
            
            success_count = sum(1 for r in analysis_results if r['status'] == 'success')
            total_count = len(analysis_results)
            
            logger.info(f"总用户数: {total_count}")
            logger.info(f"成功分析: {success_count}")
            logger.info(f"失败数量: {total_count - success_count}")
            
            # 保存分析结果到文件
            with open('memory_analysis_results.json', 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            
            logger.info("📁 分析结果已保存到 memory_analysis_results.json")
            
        except Exception as e:
            logger.error(f"❌ 全量分析失败: {e}")
        finally:
            self.db.close()

def main():
    """
    主函数
    """
    analyzer = UserMemoryAnalyzer()
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()
