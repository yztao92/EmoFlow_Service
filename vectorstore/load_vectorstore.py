# File: vectorstore/load_vectorstore.py
# 功能：向量数据库加载和检索器管理
# 实现：基于FAISS的向量存储，支持MMR检索和情绪过滤

import os  # 操作系统接口，用于路径处理
from langchain_community.vectorstores import FAISS  # FAISS向量数据库
from llm.embedding_factory import get_embedding_model  # 获取embedding模型
from dotenv import load_dotenv  # 环境变量加载

# 加载环境变量（可选）
load_dotenv()

# ==================== 模型和路径配置 ====================
# 获取 bge-small-zh 嵌入模型实例
# 参数来源：llm/embedding_factory.py 中的 get_embedding_model() 函数
embedding_model = get_embedding_model()

# 指向向量库目录（可通过 .env 配置）
# 参数来源：环境变量 VECTORSTORE_BASE，如果没有则使用默认路径
VECTORSTORE_BASE = os.getenv(
    "VECTORSTORE_BASE", "/root/EmoFlow_Service/embedding/vectorstore_by_summary_small_zh"
)

# ==================== 全局变量 ====================
# 向量库实例的全局缓存，避免重复加载
_vs = None

def get_retriever_by_emotion(emotion: str, k: int = 3):
    """
    加载单一向量库，基于 metadata.emotion 过滤，并用 MMR 检索
    
    参数：
        emotion (str): 情绪类型，用于过滤向量库中的文档
        参数来源：rag/rag_chain.py 中 detect_emotion() 函数返回的情绪标签
        k (int): 返回的文档数量，默认3
        参数来源：rag/rag_chain.py 中根据对话轮次计算得出（第一轮k=5，后续k=3）
    
    返回：
        FAISS.as_retriever: 配置好的检索器实例，支持MMR检索和情绪过滤
    
    功能说明：
        1. 懒加载向量库（首次调用时加载）
        2. 根据情绪过滤文档（只检索对应情绪的文档）
        3. 使用MMR检索算法（Maximum Marginal Relevance）
        4. 支持多样性检索，避免返回过于相似的文档
    """
    global _vs
    
    # 懒加载：首次调用时加载向量库
    if _vs is None:
        # 检查向量库路径是否存在
        if not os.path.exists(VECTORSTORE_BASE):
            raise ValueError(f"❌ 向量库路径不存在: {VECTORSTORE_BASE}")
        
        # 加载FAISS向量库
        _vs = FAISS.load_local(
            VECTORSTORE_BASE,  # 向量库路径
            embedding_model,  # embedding模型
            allow_dangerous_deserialization=True  # 允许反序列化（安全设置）
        )

    # 创建检索器，配置MMR检索和情绪过滤
    return _vs.as_retriever(
        search_type="mmr",  # 使用MMR检索算法
        search_kwargs={
            "k": k,  # 返回的文档数量
            "fetch_k": k * 4,  # 候选文档数量（k的4倍）
            "lambda_mult": 0.7  # MMR多样性参数（0.7=70%相关性+30%多样性）
        },
        filter={"emotion": emotion}  # 按情绪过滤文档
    )