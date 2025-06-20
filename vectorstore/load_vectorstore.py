import os
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

VECTORSTORE_PATH = "data/vectorstore/act"
vectorstore = None

def load_vectorstore():
    global vectorstore
    embedding = ZhipuEmbedding()
    vectorstore = FAISS.load_local(
        VECTORSTORE_PATH,
        embedding,
        allow_dangerous_deserialization=True
    )
    print("✅ 向量库加载完成")

def get_vectorstore():
    return vectorstore

def get_retriever():
    if vectorstore is None:
        raise ValueError("❌ 向量库未加载，请先执行 load_vectorstore()")
    return vectorstore.as_retriever()