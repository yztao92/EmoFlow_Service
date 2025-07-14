# File: llm/embedding_factory.py

from langchain_community.embeddings import HuggingFaceEmbeddings
import torch

# ✅ 检查是否有可用的 GPU（否则使用 CPU）
device = "cuda" if torch.cuda.is_available() else "cpu"

# ✅ 使用 HuggingFace Hub 自动下载和缓存 bge-small-zh 模型
_embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh",
    model_kwargs={"device": device},
    encode_kwargs={"normalize_embeddings": True}
)

def get_embedding_model():
    return _embedding_model