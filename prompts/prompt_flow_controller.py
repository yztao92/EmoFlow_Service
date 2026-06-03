# File: prompts/prompt_flow_controller.py
import logging
from typing import List, Dict, Any
from prompts.chat_prompts_generator_v2 import build_conversation_messages
from llm.llm_factory import chat_with_llm, chat_with_llm_messages

try:
    from retriever.search import retrieve
except Exception:
    logging.warning("[prompt_flow] 未找到 retriever.search.retrieve，RAG 将被禁用")
    def retrieve(queries: List[str], top_k: int = 4):
        return []

def chat_once(analysis: dict, state_summary: str, question: str, current_time: str = None, user_id: int = None, user_info: Dict[str, Any] = None, session_id: str = None, conversation_history: List[Dict[str, str]] = None) -> str:
    # —— 获取用户记忆点（如果有user_id）—— #
    user_memories = []
    if user_id:
        try:
            from memory import get_user_latest_memories
            user_memories = get_user_latest_memories(user_id, limit=5)
            if user_memories:
                logging.debug(f"📝 获取到用户 {user_id} 的 {len(user_memories)} 个记忆点")
            else:
                logging.debug(f"📝 用户 {user_id} 暂无记忆点")
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

    # —— 实时搜索RAG（优先使用缓存，必要时进行新搜索）—— #
    if analysis.get("need_live_search"):
        try:
            from llm.qwen_live_search import search_live_multiple
            
            live_queries = analysis.get("live_search_queries", [])
            has_timeliness_requirement = analysis.get("has_timeliness_requirement", False)
            logging.info(f"[实时搜索] 开始处理 {len(live_queries)} 个搜索查询")
            logging.info(f"[实时搜索] 时效性要求: {has_timeliness_requirement}")
            
            # 使用独立的千问实时检索模块
            live_results = search_live_multiple(live_queries, has_timeliness_requirement, session_id=session_id)
            
            if live_results:
                rag_bullets.extend(live_results)
                logging.info(f"[实时搜索] 获得 {len(live_results)} 个搜索结果")
            else:
                logging.warning("[实时搜索] 未获得任何搜索结果")
                    
        except Exception as e:
            logging.warning("实时搜索RAG失败，跳过：%s", e)
    
    # —— 如果没有新搜索结果，尝试从缓存中获取已有的搜索信息 —— #
    if not rag_bullets and session_id:
        try:
            from llm.search_cache import get_cached_search_results
            cached_results = get_cached_search_results(session_id)
            if cached_results:
                # 取最近3条缓存结果
                for result in cached_results[-3:]:
                    rag_bullets.append(result['result'])
                logging.info(f"[缓存搜索] 已加载 {len(cached_results)} 条缓存搜索信息到参考知识")
        except Exception as e:
            logging.warning(f"[缓存搜索] 获取缓存搜索信息失败: {e}")

    # —— 拼装对话消息列表 —— #
    messages = build_conversation_messages(
        {**analysis, "rag_bullets": rag_bullets, "rag_queries": analysis.get("rag_queries", [])},
        question,
        current_time,
        user_memories,  # 传递用户记忆点
        user_info,  # 传递用户基本信息
        conversation_history  # 传递对话历史
    )
    
    # 格式化显示消息列表（已禁用）
    # logging.info("=" * 50)
    # logging.info("🎯 最终拼接的消息列表")
    # logging.info("=" * 50)
    # for i, msg in enumerate(messages):
    #     logging.info(f"消息 {i+1} [{msg['role']}]: {msg['content'][:100]}...")
    # logging.info("=" * 50)

    # —— 生成 —— #
    resp = chat_with_llm_messages(messages)
    answer = resp.get("answer", "") if isinstance(resp, dict) else resp
    
    # 清理可能出现的多余引号
    if isinstance(answer, str):
        # 添加调试日志（已禁用）
        # logging.info(f"🔍 引号清理前: '{answer}'")
        
        # 使用正则表达式清理所有类型的引号（包括Unicode引号）
        import re
        # 移除所有类型的引号（包括Unicode引号）
        answer = re.sub(r'^["""''""]+', '', answer)  # 移除开头的引号
        answer = re.sub(r'["""''""]+$', '', answer)  # 移除结尾的引号
        answer = answer.strip()  # 移除空白字符
        
        # logging.info(f"🔍 引号清理后: '{answer}'")
    
    # 格式化显示LLM返回结果（已禁用）
    # logging.info("=" * 50)
    # logging.info("🤖 LLM 返回结果")
    # logging.info("=" * 50)
    # logging.info(f"原始响应: {resp}")
    # logging.info(f"提取答案: {answer}")
    # logging.info("=" * 50)

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