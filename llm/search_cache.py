#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索缓存管理模块
用于缓存千问实时搜索的结果，按sessionID分别存储
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class SearchCache:
    """搜索缓存管理器"""
    
    def __init__(self, cache_dir: str = "search_cache"):
        """
        初始化搜索缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logging.info(f"[搜索缓存] 创建缓存目录: {self.cache_dir}")
    
    def _get_cache_file_path(self, session_id: str) -> str:
        """获取指定session的缓存文件路径"""
        return os.path.join(self.cache_dir, f"{session_id}.json")
    
    def add_search_result(self, session_id: str, query: str, result: str) -> None:
        """
        添加搜索结果到缓存
        
        Args:
            session_id: 会话ID
            query: 搜索查询
            result: 搜索结果
        """
        try:
            cache_file = self._get_cache_file_path(session_id)
            
            # 读取现有缓存
            cache_data = self._load_cache(session_id)
            
            # 添加新的搜索结果
            search_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "result": result
            }
            
            cache_data["search_results"].append(search_entry)
            
            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"[搜索缓存] 已缓存搜索结果: {session_id} - {query}")
            
        except Exception as e:
            logging.error(f"[搜索缓存] 缓存失败: {e}")
    
    def get_search_results(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取指定session的所有搜索结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            cache_data = self._load_cache(session_id)
            return cache_data.get("search_results", [])
        except Exception as e:
            logging.error(f"[搜索缓存] 读取缓存失败: {e}")
            return []
    
    def get_latest_search_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定session的最新搜索结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 最新搜索结果，如果没有则返回None
        """
        try:
            search_results = self.get_search_results(session_id)
            if search_results:
                return search_results[-1]  # 返回最后一个（最新的）
            return None
        except Exception as e:
            logging.error(f"[搜索缓存] 获取最新结果失败: {e}")
            return None
    
    def _load_cache(self, session_id: str) -> Dict[str, Any]:
        """
        加载指定session的缓存数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 缓存数据
        """
        cache_file = self._get_cache_file_path(session_id)
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"[搜索缓存] 读取缓存文件失败: {e}")
        
        # 返回默认结构
        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "search_results": []
        }
    
    def clear_cache(self, session_id: str) -> None:
        """
        清除指定session的缓存
        
        Args:
            session_id: 会话ID
        """
        try:
            cache_file = self._get_cache_file_path(session_id)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logging.info(f"[搜索缓存] 已清除缓存: {session_id}")
        except Exception as e:
            logging.error(f"[搜索缓存] 清除缓存失败: {e}")
    
    def get_cache_info(self, session_id: str) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 缓存信息
        """
        try:
            cache_data = self._load_cache(session_id)
            search_results = cache_data.get("search_results", [])
            
            return {
                "session_id": session_id,
                "created_at": cache_data.get("created_at"),
                "total_searches": len(search_results),
                "latest_search": search_results[-1] if search_results else None
            }
        except Exception as e:
            logging.error(f"[搜索缓存] 获取缓存信息失败: {e}")
            return {"session_id": session_id, "error": str(e)}

# 全局缓存实例
_search_cache = None

def get_search_cache() -> SearchCache:
    """获取搜索缓存实例（单例模式）"""
    global _search_cache
    if _search_cache is None:
        _search_cache = SearchCache()
    return _search_cache

def cache_search_result(session_id: str, query: str, result: str) -> None:
    """
    便捷函数：缓存搜索结果
    
    Args:
        session_id: 会话ID
        query: 搜索查询
        result: 搜索结果
    """
    cache = get_search_cache()
    cache.add_search_result(session_id, query, result)

def get_cached_search_results(session_id: str) -> List[Dict[str, Any]]:
    """
    便捷函数：获取缓存的搜索结果
    
    Args:
        session_id: 会话ID
        
    Returns:
        List[Dict]: 搜索结果列表
    """
    cache = get_search_cache()
    return cache.get_search_results(session_id)

def get_latest_cached_result(session_id: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取最新的缓存结果
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 最新搜索结果
    """
    cache = get_search_cache()
    return cache.get_latest_search_result(session_id)

# 测试函数
def test_search_cache():
    """测试搜索缓存功能"""
    print("🧪 测试搜索缓存功能")
    print("=" * 50)
    
    # 测试数据
    session_id = "test_session_001"
    test_queries = [
        "今日最新股市行情",
        "科技股表现如何",
        "政策利好有哪些"
    ]
    test_results = [
        "• A股市场今日表现疲软\n• 上证指数下跌1.25%\n• 深证成指下跌2.83%",
        "• 科技股分化明显\n• 人工智能板块活跃\n• 芯片股表现强劲",
        "• 国务院发布体育产业政策\n• 央行开展逆回购操作\n• 工信部发布稳增长方案"
    ]
    
    try:
        # 添加测试数据
        for query, result in zip(test_queries, test_results):
            cache_search_result(session_id, query, result)
        
        # 获取所有结果
        all_results = get_cached_search_results(session_id)
        print(f"✅ 缓存了 {len(all_results)} 个搜索结果")
        
        # 获取最新结果
        latest = get_latest_cached_result(session_id)
        if latest:
            print(f"✅ 最新搜索: {latest['query']}")
            print(f"📝 结果预览: {latest['result'][:50]}...")
        
        # 获取缓存信息
        cache_info = get_search_cache().get_cache_info(session_id)
        print(f"📊 缓存信息: {cache_info}")
        
        # 清理测试数据
        get_search_cache().clear_cache(session_id)
        print("✅ 测试完成，已清理测试数据")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_search_cache()
