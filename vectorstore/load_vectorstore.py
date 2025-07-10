# File: vectorstore/load_vectorstore.py

import os
from langchain_community.vectorstores import FAISS
from llm.embedding_factory import get_embedding_model  # ✅ 引入封装
from dotenv import load_dotenv

# 加载环境变量（可选）
load_dotenv()

# ✅ 获取 bge-m3 嵌入模型
embedding_model = get_embedding_model()

# ✅ 指向向量库目录（可通过 .env 配置）
VECTORSTORE_BASE = os.getenv(
    "VECTORSTORE_BASE", "embedding/vectorstore_by_summary_m3"
)

_vs = None

def get_retriever_by_emotion(emotion: str, k: int = 3):
    """
    加载单一向量库，基于 metadata.emotion 过滤，并用 MMR 检索。
    """
    global _vs
    if _vs is None:
        if not os.path.exists(VECTORSTORE_BASE):
            raise ValueError(f"❌ 向量库路径不存在: {VECTORSTORE_BASE}")
        _vs = FAISS.load_local(
            VECTORSTORE_BASE,
            embedding_model,
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