# rag/retriever.py

import os
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 向量库根目录，按情绪存放子目录
VECTORSTORE_BASE = os.getenv(
    "VECTORSTORE_BASE", "/root/EmoFlow/data/vectorstore_by_emotion"
)

def get_retriever_by_emotion(emotion: str, k: int = 3):
    """
    根据情绪加载对应的 FAISS 向量库，并返回 Retriever。

    :param emotion: 情绪标签，如 'sad', 'happy', 'tired', 'angry'
    :param k: 检索时返回最相似文档的数量
    :return: LangChain Retriever
    """
    # 构建该情绪对应的索引路径
    index_path = os.path.join(VECTORSTORE_BASE, emotion)

    # 加载 FAISS 索引，需要与保存时使用的 embedding 一致
    # 把 Embedding 实例作为第二个位置参数传入
    vectorstore = FAISS.load_local(
        index_path,
        ZhipuEmbedding(),
        allow_dangerous_deserialization=True
    )

    # 返回 Retriever 对象，可指定检索数量 k
    return vectorstore.as_retriever(search_kwargs={"k": k})