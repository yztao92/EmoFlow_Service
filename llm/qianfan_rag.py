# llm/qianfan_rag.py
# 功能：百度 AppBuilder V2 搜索增强接口封装

import os
import requests
import json
import logging
from typing import List

def call_appbuilder_search(query: str, model: str = "ernie-3.5-8k", max_retries: int = 3) -> str:
    """
    调用百度 AppBuilder V2 智能搜索生成接口，获取简洁总结回答
    """
    api_key = os.getenv("QIANFAN_API_KEY")
    if not api_key:
        logging.warning("[AppBuilder V2] 缺少 QIANFAN_API_KEY")
        return ""

    url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "model": model,
        "enable_deep_search": False,  # 不走深度链路，提升速度
        "instruction": "请用简洁语言总结用户问题的核心信息，控制在500字以内"
    }

    # 重试机制
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                logging.error(f"[AppBuilder V2] HTTP错误: {response.status_code}")
                logging.debug(f"[AppBuilder V2] 响应内容: {response.text}")
                if attempt < max_retries - 1:
                    logging.info(f"[AppBuilder V2] 将在 {2 ** attempt} 秒后重试...")
                    import time
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                return ""

            result = response.json()

            # 优先提取生成结果
            content = result.get("result") \
                or result.get("content") \
                or result.get("answer") \
                or (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

            if content:
                return content
            else:
                logging.warning("[AppBuilder V2] 返回结果为空")
                return ""

        except requests.exceptions.Timeout as e:
            logging.warning(f"[AppBuilder V2] 请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                logging.error(f"[AppBuilder V2] 所有重试均失败")
                return ""
        except requests.exceptions.RequestException as e:
            logging.warning(f"[AppBuilder V2] 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                logging.error(f"[AppBuilder V2] 所有重试均失败")
                return ""
        except Exception as e:
            logging.error(f"[AppBuilder V2] 未知错误: {e}")
            return ""
    
    return ""

def get_rag_bullets_for_query(query: str) -> List[str]:
    """
    获取用户查询对应的简洁高质量回答，用于填充 RAG 块
    """
    raw_text = call_appbuilder_search(query)
    if not raw_text:
        return []

    clean_text = raw_text.replace("^[", "").replace("]^", "").strip()
    return [clean_text]

def get_rag_bullets_for_query_with_cache(query: str, session_id: str) -> List[str]:
    """
    获取用户查询对应的简洁高质量回答，支持缓存机制
    
    参数：
        query (str): 搜索查询词
        session_id (str): 会话ID
    
    返回：
        List[str]: 搜索结果列表
    """
    try:
        from .search_cache_manager import search_with_cache
        
        raw_text = search_with_cache(query, session_id)
        if not raw_text:
            return []

        clean_text = raw_text.replace("^[", "").replace("]^", "").strip()
        return [clean_text]
    except ImportError:
        # 如果缓存管理器不可用，回退到普通搜索
        logging.warning("[AI搜索] 缓存管理器不可用，使用普通搜索")
        return get_rag_bullets_for_query(query)