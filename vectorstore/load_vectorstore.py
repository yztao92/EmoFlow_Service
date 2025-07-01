# File: vectorstore/load_vectorstore.py

import os
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 指向唯一的向量库目录
VECTORSTORE_BASE = os.getenv(
    "VECTORSTORE_BASE", "data/vectorstore_by_summary"
)

_embedding = ZhipuEmbedding()
_vs = None

def get_retriever_by_emotion(emotion: str, k: int = 3):
    """
    加载单一库，基于 metadata.emotion 过滤，并用 MMR 检索。
    """
    global _vs
    if _vs is None:
        _vs = FAISS.load_local(
            VECTORSTORE_BASE,
            _embedding,
            allow_dangerous_deserialization=True
        )

    return _vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 4,
            "lambda_mult": 0.7
        },
        filter={"emotion": emotion}
    )