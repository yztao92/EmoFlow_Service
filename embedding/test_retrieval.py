from langchain.embeddings import HuggingFaceEmbeddings

# ✅ 替换为你本地 fake123456 的实际绝对路径
embedding_model = HuggingFaceEmbeddings(
    model_name="/root/EmoFlow_Service/models/bge-m3/fake123456",
    model_kwargs={"device": "cpu"},  # 或 "cuda" 如支持
    encode_kwargs={"normalize_embeddings": True}
)

# 测试一条 query 是否成功生成 embedding 向量
result = embedding_model.embed_query("测试一下模型加载是否成功")
print("✅ 前 5 维 embedding 向量：", result[:5])