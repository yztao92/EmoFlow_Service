# File: rag/rag_chain.py
# 功能：RAG (Retrieval-Augmented Generation) 检索增强生成的核心实现
# 包含：情绪检测、知识检索、Prompt路由、LLM调用等完整流程

from rag.prompt_router import route_prompt_by_emotion  # 根据情绪路由到不同风格的Prompt
from llm.emotion_detector import detect_emotion  # 情绪检测模块
from rag.prompts import PROMPT_MAP  # 不同风格的Prompt模板映射
from vectorstore.load_vectorstore import get_retriever_by_emotion  # 根据情绪获取向量检索器
from llm.deepseek_wrapper import DeepSeekLLM  # DeepSeek LLM包装器
from llm.embedding_factory import get_embedding_model  # 获取embedding模型
from langchain_core.messages import HumanMessage  # LangChain消息格式
import numpy as np  # 数值计算库，用于相似度计算
import logging  # 日志记录
import re  # 正则表达式，用于文本清理
import time  # 时间模块，用于性能监控

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化全局模型实例
embedding_model = get_embedding_model()  # 获取embedding模型实例
_deepseek = DeepSeekLLM()  # 初始化DeepSeek LLM实例

def chat_with_llm(prompt: str) -> dict:
    """
    调用DeepSeek LLM生成回复
    
    参数：
        prompt (str): 输入给LLM的完整提示词
        参数来源：run_rag_chain函数中构造的Prompt
    
    返回：
        dict: 包含LLM回复的字典，格式 {"answer": "生成的回复"}
    """
    response_text = _deepseek._call([
        HumanMessage(role="user", content=prompt)  # 构造LangChain消息格式
    ])
    return {"answer": response_text}

def clean_answer(text: str) -> str:
    """
    清理LLM回复中的多余引号和格式
    
    参数：
        text (str): 原始LLM回复文本
        参数来源：chat_with_llm函数返回的原始回复
    
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
    
    返回：
        str: AI生成的回复文本
    
    流程：
        1. 自动情绪识别 + Prompt路由
        2. 根据情绪检索相关知识
        3. 构造完整Prompt并调用LLM
        4. 清理和返回回复
    """
    # ==================== 1. 情绪识别和Prompt路由 ====================
    # 自动识别用户输入的情绪
    emotion = detect_emotion(query)
    # 根据情绪选择对应的Prompt风格
    prompt_key = route_prompt_by_emotion(emotion)
    # 从Prompt映射中获取对应的模板
    prompt_template = PROMPT_MAP.get(prompt_key, PROMPT_MAP["default"])
    logging.info(f"[Prompt 路由] 使用 prompt_key: {prompt_key}")  # 记录使用的Prompt风格

    # ==================== 2. 知识检索 ====================
    # 根据对话轮次决定检索数量：第一轮检索更多内容，后续轮次减少
    k = 5 if round_index == 1 else 3
    # 根据情绪获取对应的检索器（包含情绪过滤）
    retriever = get_retriever_by_emotion(emotion, k=k)

    # 执行检索并记录耗时
    start_time = time.time()
    docs = retriever.invoke(query)  # 使用LangChain的invoke方法进行检索
    retrieve_duration = time.time() - start_time
    logging.info(f"⏱️ [检索耗时] {retrieve_duration:.2f} 秒")

    # ==================== 3. 相似度计算和日志记录 ====================
    # 计算查询向量
    q_vec = np.array(embedding_model.embed_query(query))
    q_norm = np.linalg.norm(q_vec) + 1e-8  # 计算查询向量范数，加小值避免除零
    
    # 计算文档向量
    doc_texts = [d.page_content for d in docs]  # 提取文档内容
    d_vecs = np.array(embedding_model.embed_documents(doc_texts))  # 批量计算文档向量
    d_norms = np.linalg.norm(d_vecs, axis=1) + 1e-8  # 计算文档向量范数
    
    # 计算余弦相似度
    sims = (d_vecs @ q_vec) / (d_norms * q_norm)

    # 记录检索结果和相似度
    logging.info(f"\n🧠 [检索] 情绪={emotion}, prompt={prompt_key}, k={k}")
    for i, (doc, sim) in enumerate(zip(docs, sims), 1):
        snippet = doc.page_content.replace("\n", " ")[:200]  # 截取文档片段用于日志
        logging.info(f"—— 文档段 {i} （情绪={doc.metadata.get('emotion')}，相似度 {sim*100:.1f}%）—— {snippet}…")

    # ==================== 4. 构造上下文和Prompt ====================
    # 将检索到的文档构造为上下文，包含摘要和原文
    context = "\n\n".join(
        f"摘要: {doc.page_content}\n原文: {doc.metadata.get('content', '')[:300]}"  # 限制原文长度
        for doc in docs
    )

    # 使用Prompt模板格式化完整提示词
    prompt = prompt_template.format(
        emotion=emotion,  # 当前情绪
        round_index=round_index,  # 对话轮次
        state_summary=state_summary,  # 状态摘要
        context=context,  # 检索到的知识上下文
        question=query  # 用户查询
    )

    # 记录使用的完整Prompt（用于调试）
    logging.info("\n💡 [使用 Prompt]---------------------------------------------------")
    logging.info(prompt)
    logging.info("💡 [End Prompt]---------------------------------------------------\n")

    # ==================== 5. LLM调用和回复清理 ====================
    # 调用LLM生成回复
    res = chat_with_llm(prompt)
    raw_answer = res.get("answer", "").strip()  # 获取原始回复
    answer = clean_answer(raw_answer)  # 清理回复格式
    return answer
