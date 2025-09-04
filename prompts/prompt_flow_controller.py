# File: prompts/prompt_flow_controller.py
import logging
from typing import List, Dict, Any
from prompts.chat_prompts_generator import build_final_prompt
from llm.llm_factory import chat_with_llm

try:
    from retriever.search import retrieve
except Exception:
    logging.warning("[prompt_flow] 未找到 retriever.search.retrieve，RAG 将被禁用")
    def retrieve(queries: List[str], top_k: int = 4):
        return []

def chat_once(analysis: dict, state_summary: str, question: str, current_time: str = None, user_id: int = None, user_info: Dict[str, Any] = None, session_id: str = None) -> str:
    # —— 获取用户记忆点（如果有user_id）—— #
    user_memories = []
    if user_id:
        try:
            from memory import get_user_latest_memories
            user_memories = get_user_latest_memories(user_id, limit=10)
            if user_memories:
                logging.info(f"📝 获取到用户 {user_id} 的 {len(user_memories)} 个记忆点")
            else:
                logging.info(f"📝 用户 {user_id} 暂无记忆点")
        except Exception as e:
            logging.warning(f"获取用户记忆点失败，跳过：{e}")
            user_memories = []

    # —— 可选 RAG —— #
    rag_bullets = []
    if analysis.get("need_rag"):
        try:
            docs = retrieve(analysis.get("rag_queries", []), top_k=4)
            rag_bullets = [getattr(d, "snippet", str(d)) for d in (docs or [])]
        except Exception as e:
            logging.warning("RAG 检索失败，跳过：%s", e)

    # —— 新增：实时搜索RAG —— #
    if analysis.get("need_live_search"):
        try:
            from llm.qianfan_rag import get_rag_bullets_for_query_with_cache
            live_queries = analysis.get("live_search_queries", [])
            # 只处理第一个搜索词，避免多个搜索拖慢速度
            if len(live_queries) > 1:
                live_queries = [live_queries[0]]
            
            for query in live_queries:
                # 使用带缓存的搜索函数
                if session_id:
                    from llm.search_cache_manager import get_cached_search_result
                    live_bullets = get_rag_bullets_for_query_with_cache(query, session_id)
                else:
                    # 如果没有session_id，回退到普通搜索
                    from llm.qianfan_rag import get_rag_bullets_for_query
                    live_bullets = get_rag_bullets_for_query(query)
                
                if live_bullets:
                    rag_bullets.extend(live_bullets)
                else:
                    # 添加降级提示
                    rag_bullets.append(f"抱歉，暂时无法获取'{query}'的最新信息，请稍后再试或尝试其他查询。")
                    
        except Exception as e:
            logging.warning("实时搜索RAG失败，跳过：%s", e)
    
    # —— 新增：即使不需要新搜索，也要传递已搜索的内容 —— #
    elif session_id:
        try:
            from llm.search_cache_manager import get_session_searched_content
            searched_content = get_session_searched_content(session_id)
            if searched_content:
                # 将已搜索的内容添加到rag_bullets中
                rag_bullets.append(f"已搜索的相关信息：\n{searched_content}")
        except Exception as e:
            logging.warning(f"[搜索优化] 添加已搜索内容失败: {e}")

    # —— 拼装最终 Prompt —— #
    final_prompt = build_final_prompt(
        {**analysis, "rag_bullets": rag_bullets, "rag_queries": analysis.get("rag_queries", [])},
        state_summary,
        question,
        current_time,
        user_memories,  # 新增：传递用户记忆点
        user_info  # 新增：传递用户基本信息
    )
    
    # 格式化显示最终prompt
    logging.info("=" * 50)
    logging.info("🎯 最终拼接的 PROMPT")
    logging.info("=" * 50)
    logging.info(final_prompt)
    logging.info("=" * 50)

    # —— 生成 —— #
    resp = chat_with_llm(final_prompt)
    answer = resp.get("answer", "") if isinstance(resp, dict) else resp
    
    # 清理可能出现的多余引号
    if isinstance(answer, str):
        # 使用正则表达式清理所有类型的引号（包括Unicode引号）
        import re
        # 移除所有类型的引号（包括Unicode引号）
        answer = re.sub(r'^["""''""]+', '', answer)  # 移除开头的引号
        answer = re.sub(r'["""''""]+$', '', answer)  # 移除结尾的引号
        answer = answer.strip()  # 移除空白字符

    # —— 失败回退（根据 emotion_type 适配）—— #
    if not isinstance(answer, str) or len(answer.strip()) < 4:
        emotion_type = analysis.get("emotion_type", "neutral")
        fallback = {
            "tired": "我在，先休息一下，等你想说的时候我们再聊。",
            "negative": "我理解你的感受，先让情绪沉淀一下，我在这里陪着你。",
            "angry": "我听见你的愤怒了，先冷静一下，我支持你。",
            "positive": "真为你开心！想继续分享这份喜悦吗？",
            "neutral": "我在，想聊什么都可以。"
        }
        answer = fallback.get(emotion_type, fallback["neutral"])

    return answer