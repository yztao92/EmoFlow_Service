import os
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

VECTORSTORE_BASE_PATH = "./data/vectorstore"
vectorstores = {}

def load_vectorstores():
    """加载所有子目录下的向量库"""
    embedding = ZhipuEmbedding()
    for folder in os.listdir(VECTORSTORE_BASE_PATH):
        path = os.path.join(VECTORSTORE_BASE_PATH, folder)
        if os.path.isdir(path):
            try:
                vs = FAISS.load_local(
                    path, embedding, allow_dangerous_deserialization=True
                )
                vectorstores[folder] = vs
                print(f"✅ 向量库加载完成: {folder}")
            except Exception as e:
                print(f"❌ 加载失败: {folder}，原因: {e}")

def get_vectorstore(category: str):
    if category not in vectorstores:
        raise ValueError(f"❌ 向量库未找到: {category}")
    return vectorstores[category]

def get_retriever(category: str):
    return get_vectorstore(category).as_retriever()