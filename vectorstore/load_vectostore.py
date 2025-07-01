# File: vectorstore/load_vectorstore.py
import os
from typing import Dict
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 根目录：请确保环境变量或默认值指向你的分情绪向量库根目录
VECTORSTORE_BASE = os.getenv(
    "VECTORSTORE_BASE", "vectorstore_by_emotion"
)

_embedding = ZhipuEmbedding()
_loaded: Dict[str, FAISS] = {}

def get_retriever_by_emotion(emotion: str, k: int = 3):
    """
    按 emotion 延迟加载 FAISS 索引，并返回 MMR retriever。
    """
    # 延迟加载索引
    if emotion not in _loaded:
        path = os.path.join(VECTORSTORE_BASE, emotion)
        _loaded[emotion] = FAISS.load_local(
            path,
            _embedding,
            allow_dangerous_deserialization=True
        )
    vs = _loaded[emotion]

    # MMR 检索，兼顾相关性与多样性
    return vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 4,
            "lambda_mult": 0.7
        }
    )


# File: llm/zhipu_chat.py
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from vectorstore.load_vectorstore import get_retriever_by_emotion
from llm.zhipu_wrapper import ZhipuLLM

prompt_template = """
已知信息：
{context}

问题：
{question}

请结合已知信息回答问题，如果无法从中得到答案，请直接说“我不知道”。
"""
prompt = PromptTemplate.from_template(prompt_template)

def zhipu_chat(query: str, emotion: str = "default", round_index: int = 1) -> str:
    # 1) 动态设置 k: 首轮多给上下文
    k = 5 if round_index == 1 else 3

    # 2) 获取按情绪分库并做 MMR 检索的 retriever
    retriever = get_retriever_by_emotion(emotion, k=k)

    # 3) 构建 RetrievalQA 链
    chain = RetrievalQA.from_chain_type(
        llm=ZhipuLLM(),
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt}
    )

    # 4) 执行查询并返回回答
    return chain.run({
        "query": query
    })