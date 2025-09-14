#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千问实时检索模块
独立封装千问的联网搜索功能，无缓存设计
"""

import os
import logging
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from .search_cache import cache_search_result

# 加载环境变量
load_dotenv()

class QwenLiveSearch:
    """千问实时检索客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化千问实时检索客户端
        
        Args:
            api_key: 千问API Key，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("QIANWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置QIANWEN_API_KEY或DASHSCOPE_API_KEY环境变量")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        logging.info("[千问实时检索] 客户端初始化成功")
    
    def search(self, query: str, model: str = "qwen-plus", search_strategy: str = "turbo", session_id: Optional[str] = None) -> str:
        """
        执行实时搜索
        
        Args:
            query: 搜索查询
            model: 使用的模型，默认为qwen-plus
            search_strategy: 搜索策略，turbo或max
            session_id: 会话ID，用于缓存结果
            
        Returns:
            str: 搜索结果内容
        """
        try:
            logging.info(f"[千问实时检索] 开始搜索: {query}")
            
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个互联网检索助手，能够返回最新实时的消息。请按以下格式返回：\n\n【最新消息】\n[500字以内的最新消息，请用bullet point形式组织内容]\n\n检索的信息必须是最新的。"
                    },
                    {"role": "user", "content": query}
                ],
                extra_body={
                    "enable_search": True,
                    "search_options": {
                        "forced_search": True,
                        "search_strategy": search_strategy,
                    }
                },
                # 添加其他优化参数
                temperature=0.3,
                max_tokens=500,
                top_p=0.8
            )
            
            result = completion.choices[0].message.content
            usage = completion.usage
            
            if result:
                # 清理文本格式
                clean_text = result.replace("^[", "").replace("]^", "").strip()
                logging.info(f"[千问实时检索] 搜索成功，Token使用: {usage.total_tokens}")
                
                # 缓存搜索结果
                if session_id:
                    try:
                        cache_search_result(session_id, query, clean_text)
                        logging.info(f"[千问实时检索] 已缓存搜索结果: {session_id}")
                    except Exception as cache_e:
                        logging.warning(f"[千问实时检索] 缓存失败: {cache_e}")
                
                return clean_text
            else:
                logging.warning(f"[千问实时检索] 搜索返回空结果")
                return ""
                
        except Exception as e:
            logging.error(f"[千问实时检索] 搜索失败: {e}")
            return ""
    
    def search_multiple(self, queries: List[str], has_timeliness_requirement: bool = False, model: str = "qwen-plus", search_strategy: str = "turbo", session_id: Optional[str] = None) -> List[str]:
        """
        批量执行实时搜索
        
        Args:
            queries: 搜索查询列表
            has_timeliness_requirement: 是否有时效性要求
            model: 使用的模型
            search_strategy: 搜索策略
            session_id: 会话ID，用于缓存结果
            
        Returns:
            List[str]: 搜索结果列表
        """
        results = []
        for query in queries:
            # 如果有时效性要求，在查询词前加上日期和"最新"
            if has_timeliness_requirement:
                from datetime import datetime
                current_date = datetime.now().strftime("%Y年%m月%d日")
                enhanced_query = f"{current_date}最新{query}"
                logging.info(f"[千问实时检索] 时效性查询: {query} -> {enhanced_query}")
            else:
                enhanced_query = query
                logging.info(f"[千问实时检索] 普通查询: {query}")
            
            result = self.search(enhanced_query, model, search_strategy, session_id)
            if result:
                results.append(result)
        return results

# 全局客户端实例
_qwen_search_client = None

def get_qwen_search_client() -> QwenLiveSearch:
    """获取千问搜索客户端实例（单例模式）"""
    global _qwen_search_client
    if _qwen_search_client is None:
        _qwen_search_client = QwenLiveSearch()
    return _qwen_search_client

def search_live(query: str, model: str = "qwen-plus", search_strategy: str = "turbo", session_id: Optional[str] = None) -> str:
    """
    便捷函数：执行单次实时搜索
    
    Args:
        query: 搜索查询
        model: 使用的模型
        search_strategy: 搜索策略
        session_id: 会话ID，用于缓存结果
        
    Returns:
        str: 搜索结果内容
    """
    client = get_qwen_search_client()
    return client.search(query, model, search_strategy, session_id)

def search_live_multiple(queries: List[str], has_timeliness_requirement: bool = False, model: str = "qwen-plus", search_strategy: str = "turbo", session_id: Optional[str] = None) -> List[str]:
    """
    便捷函数：执行批量实时搜索
    
    Args:
        queries: 搜索查询列表
        has_timeliness_requirement: 是否有时效性要求
        model: 使用的模型
        search_strategy: 搜索策略
        session_id: 会话ID，用于缓存结果
        
    Returns:
        List[str]: 搜索结果列表
    """
    client = get_qwen_search_client()
    return client.search_multiple(queries, has_timeliness_requirement, model, search_strategy, session_id)

# 测试函数
def test_qwen_live_search():
    """测试千问实时检索功能"""
    print("🧪 测试千问实时检索功能")
    print("=" * 50)
    
    try:
        # 测试单次搜索
        result = search_live("今日股市行情")
        if result:
            print("✅ 单次搜索成功")
            print(f"📝 结果预览: {result[:100]}...")
        else:
            print("❌ 单次搜索失败")
        
        # 测试批量搜索（普通查询）
        queries = ["今日天气", "最新科技新闻"]
        results = search_live_multiple(queries, has_timeliness_requirement=False)
        print(f"✅ 普通批量搜索完成，获得 {len(results)} 个结果")
        
        # 测试批量搜索（时效性查询）
        timeliness_queries = ["股市行情", "科技新闻"]
        timeliness_results = search_live_multiple(timeliness_queries, has_timeliness_requirement=True)
        print(f"✅ 时效性批量搜索完成，获得 {len(timeliness_results)} 个结果")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_qwen_live_search()
