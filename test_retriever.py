# test_retriever_no_emotion_filter.py

import os, sys
import numpy as np

# 保证能导入项目模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from llm.zhipu_embedding import ZhipuEmbedding
from langchain_community.vectorstores import FAISS

def main():
    # 1) 配置向量库路径和查询
    VECTORSTORE_BASE = os.getenv("VECTORSTORE_BASE", "data/vectorstore_by_summary")
    query = "我的上司真的太过份了。"
    k = 3

    # 2) 加载向量库（只加载一次）
    embedder = ZhipuEmbedding()
    vs = FAISS.load_local(
        VECTORSTORE_BASE,
        embedder,
        allow_dangerous_deserialization=True
    )

    # 3) 构造一个不带过滤的 MMR retriever
    retriever = vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 4,
            "lambda_mult": 0.7
        },
        filter=None  # 这里不做情绪过滤
    )

    # 4) 执行检索
    docs = retriever.get_relevant_documents(query)

    # 5) 计算相似度
    q_vec = np.array(embedder.embed_query(query))
    q_norm = np.linalg.norm(q_vec) + 1e-8
    doc_texts = [d.page_content for d in docs]
    d_vecs = np.array(embedder.embed_documents(doc_texts))
    d_norms = np.linalg.norm(d_vecs, axis=1) + 1e-8
    sims = (d_vecs @ q_vec) / (d_norms * q_norm)

    # 6) 打印结果
    print(f"不做情绪过滤，共检索 top-{k}：\n")
    for i, (doc, sim) in enumerate(zip(docs, sims), 1):
        snippet = doc.page_content.replace("\n", " ")[:200]
        emo = doc.metadata.get("emotion", "N/A")
        print(f"--- Document {i} （emotion={emo}, 相似度 {sim*100:.1f}%）---")
        print("内容片段：", snippet)
        print()

if __name__ == "__main__":
    main()