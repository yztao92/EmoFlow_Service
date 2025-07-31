# File: rag/rag_chain.py
# 功能：RAG检索增强生成的核心逻辑
# 实现：用户查询 → 向量检索 → 知识融合 → LLM生成回复

import logging
import time
import numpy as np
import re
from typing import Dict, Any

# 导入千问向量库系统
from vectorstore.qwen_vectorstore import get_qwen_vectorstore, set_qwen_embedding_model
from llm.qwen_embedding_factory import get_qwen_embedding_model
from rag.prompt_router import route_prompt_by_emotion
from rag.prompts import PROMPT_MAP
from llm.llm_factory import chat_with_llm

# 延迟初始化千问向量库和embedding模型
_qwen_vectorstore = None
_qwen_embedding_model = None

def get_qwen_vectorstore():
    """获取千问向量库实例（延迟初始化）"""
    global _qwen_vectorstore
    if _qwen_vectorstore is None:
        from vectorstore.qwen_vectorstore import get_qwen_vectorstore as _get_qwen_vectorstore
        _qwen_vectorstore = _get_qwen_vectorstore()
        # 确保embedding模型被设置到向量库
        embedding_model = get_qwen_embedding_model()
        from vectorstore.qwen_vectorstore import set_qwen_embedding_model
        set_qwen_embedding_model(embedding_model)
    return _qwen_vectorstore

def get_qwen_embedding_model():
    """获取千问embedding模型实例（延迟初始化）"""
    global _qwen_embedding_model
    if _qwen_embedding_model is None:
        from llm.qwen_embedding_factory import get_qwen_embedding_model as _get_qwen_embedding_model
        _qwen_embedding_model = _get_qwen_embedding_model()
    return _qwen_embedding_model

def chat_with_llm(prompt: str) -> dict:
    """
    调用LLM生成回复
    
    参数：
        prompt (str): 完整的提示词
    
    返回：
        dict: 包含answer字段的响应字典
    """
    # 这里调用你的LLM工厂函数
    from llm.llm_factory import chat_with_llm as llm_chat
    return llm_chat(prompt)

def clean_answer(text: str) -> str:
    """
    清理LLM回复文本
    
    参数：
        text (str): 原始回复文本
    
    返回：
        str: 清理后的回复文本
    """
    text = text.strip()  # 去除首尾空白
    # 使用正则表达式检查是否被引号包围，如果是则去除
    if re.fullmatch(r'^["""\'].*["""\']$', text):
        return text[1:-1].strip()
    return text

def run_rag_chain(
    query: str,
    round_index: int,
    state_summary: str,
    emotion: str = "neutral",  # 保留emotion参数用于Prompt路由
) -> str:
    """
    RAG 主逻辑：完整的检索增强生成流程
    
    参数：
        query (str): 用户输入的查询文本
        参数来源：main.py中用户的最新输入
        round_index (int): 当前对话轮次
        参数来源：main.py中计算的用户发言轮次
        state_summary (str): 对话状态摘要
        参数来源：StateTracker.summary()方法生成
        emotion (str): 用户情绪状态（仅用于Prompt路由）
        参数来源：前端传入的情绪信息
    
    返回：
        str: AI生成的回复文本
    
    流程：
        1. Prompt路由（基于情绪）
        2. 千问向量检索（纯相似度）
        3. 构造完整Prompt并调用LLM
        4. 清理和返回回复
    """
    # ==================== 1. Prompt路由 ====================
    # 使用传入的情绪参数进行Prompt路由
    prompt_key = route_prompt_by_emotion(emotion)
    prompt_template = PROMPT_MAP.get(prompt_key, PROMPT_MAP["default"])
    logging.info(f"[Prompt 路由] 使用 prompt_key: {prompt_key}")

    # ==================== 2. 千问向量检索 ====================
    # 根据对话轮次决定检索数量：第一轮检索更多内容，后续轮次减少
    k = 5 if round_index == 1 else 3
    
    # 执行千问向量检索（纯相似度检索，无情绪过滤）
    start_time = time.time()
    search_results = get_qwen_vectorstore().search(query, k=k)
    retrieve_duration = time.time() - start_time
    logging.info(f"⏱️ [千问检索耗时] {retrieve_duration:.2f} 秒")

    # ==================== 3. 检索结果处理和日志记录 ====================
    if not search_results:
        logging.warning("⚠️ 未检索到相关文档")
        # 如果没有检索到结果，使用默认回复
        context = "抱歉，我没有找到相关的知识来回答您的问题。"
    else:
        # 记录检索结果
        logging.info(f"\n🧠 [千问检索] 情绪={emotion}, prompt={prompt_key}, k={k}")
        for i, result in enumerate(search_results, 1):
            similarity = result.get('similarity', 0)
            title = result.get('title', '未知标题')
            logging.info(f"—— 文档 {i} （相似度 {similarity*100:.1f}%）—— {title[:50]}…")

        # ==================== 4. 构造上下文和Prompt ====================
        # 将检索到的文档构造为上下文
        context_parts = []
        for result in search_results:
            answer_summary = result.get('answer_summary', '')
            key_point = result.get('key_point', '')
            suggestion = result.get('suggestion', '')
            
            # 组合文档信息
            doc_info = f"摘要: {answer_summary}"
            if key_point:
                doc_info += f"\n关键点: {key_point}"
            if suggestion:
                doc_info += f"\n建议: {suggestion}"
            
            context_parts.append(doc_info)
        
        context = "\n\n".join(context_parts)

    # ==================== 5. 构造完整Prompt ====================
    # 使用Prompt模板格式化完整提示词
    prompt = prompt_template.format(
        emotion=emotion,  # 当前情绪（用于Prompt风格）
        round_index=round_index,  # 对话轮次
        state_summary=state_summary,  # 状态摘要
        context=context,  # 检索到的知识上下文
        question=query  # 用户查询
    )

    # 记录使用的完整Prompt（用于调试）
    logging.info("\n💡 [使用 Prompt]---------------------------------------------------")
    logging.info(prompt)
    logging.info("💡 [End Prompt]---------------------------------------------------\n")

    # ==================== 6. LLM调用和回复清理 ====================
    # 调用LLM生成回复
    res = chat_with_llm(prompt)
    raw_answer = res.get("answer", "").strip()  # 获取原始回复
    answer = clean_answer(raw_answer)  # 清理回复格式
    return answer
