# llm/search_cache_manager.py
# 功能：搜索缓存管理器，基于session ID缓存搜索结果

import os
import json
import logging
from typing import Dict, Optional
from .qianfan_rag import call_appbuilder_search

# 缓存文件路径
CACHE_FILE = "search_cache.json"

def load_cache() -> Dict[str, Dict[str, str]]:
    """
    从JSON文件加载缓存数据
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logging.info("[缓存管理] 缓存文件为空，返回空字典")
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logging.warning(f"[缓存管理] JSON解析失败: {e}")
            # 如果JSON解析失败，尝试备份并重新创建文件
            try:
                backup_file = CACHE_FILE + ".backup"
                os.rename(CACHE_FILE, backup_file)
                logging.info(f"[缓存管理] 已备份损坏的缓存文件到 {backup_file}")
            except:
                pass
            return {}
        except Exception as e:
            logging.warning(f"[缓存管理] 加载缓存文件失败: {e}")
    return {}

def save_cache(cache_data: Dict[str, Dict[str, str]]):
    """
    保存缓存数据到JSON文件
    """
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"[缓存管理] 保存缓存文件失败: {e}")

def get_cached_search_result(query: str, session_id: str) -> Optional[str]:
    """
    获取缓存的搜索结果
    
    参数：
        query (str): 搜索查询词
        session_id (str): 会话ID
    
    返回：
        Optional[str]: 缓存的搜索结果，如果没有则返回None
    """
    cache_data = load_cache()
    
    if session_id in cache_data and query in cache_data[session_id]:
        logging.info(f"[缓存管理] 找到缓存结果: {query} (session: {session_id})")
        return cache_data[session_id][query]
    
    return None

def cache_search_result(query: str, session_id: str, result: str):
    """
    缓存搜索结果
    
    参数：
        query (str): 搜索查询词
        session_id (str): 会话ID
        result (str): 搜索结果
    """
    cache_data = load_cache()
    
    # 确保session_id存在
    if session_id not in cache_data:
        cache_data[session_id] = {}
    
    # 缓存结果
    cache_data[session_id][query] = result
    
    # 保存到文件
    save_cache(cache_data)
    
    logging.info(f"[缓存管理] 已缓存结果: {query} (session: {session_id})")

def search_with_cache(query: str, session_id: str) -> str:
    """
    带缓存的搜索功能
    
    参数：
        query (str): 搜索查询词
        session_id (str): 会话ID
    
    返回：
        str: 搜索结果
    """
    # 先检查缓存
    cached_result = get_cached_search_result(query, session_id)
    if cached_result:
        return cached_result
    
    # 缓存中没有，调用API搜索
    logging.info(f"[缓存管理] 缓存未命中，调用API搜索: {query}")
    result = call_appbuilder_search(query)
    
    # 缓存结果
    if result:
        cache_search_result(query, session_id, result)
    
    return result

def clear_session_cache(session_id: str):
    """
    清理指定会话的缓存
    
    参数：
        session_id (str): 会话ID
    """
    cache_data = load_cache()
    
    if session_id in cache_data:
        del cache_data[session_id]
        save_cache(cache_data)
        logging.info(f"[缓存管理] 已清理会话缓存: {session_id}")

def get_session_searched_content(session_id: str) -> str:
    """
    获取指定会话已搜索的内容摘要
    
    参数：
        session_id (str): 会话ID
    
    返回：
        str: 已搜索内容的摘要，如果没有则返回空字符串
    """
    cache_data = load_cache()
    
    if session_id not in cache_data:
        return ""
    
    session_queries = cache_data[session_id]
    if not session_queries:
        return ""
    
    # 构建已搜索内容的完整信息
    content_parts = []
    for query, result in session_queries.items():
        # 使用完整的搜索结果，不截断
        content_parts.append(f"查询：{query}\n结果：{result}")
    
    result = "\n\n".join(content_parts)
    return result

def get_cache_stats() -> Dict[str, int]:
    """
    获取缓存统计信息
    
    返回：
        Dict[str, int]: 缓存统计信息
    """
    cache_data = load_cache()
    
    total_sessions = len(cache_data)
    total_queries = sum(len(queries) for queries in cache_data.values())
    
    return {
        "total_sessions": total_sessions,
        "total_queries": total_queries
    }
