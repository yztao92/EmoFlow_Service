# File: llm/embedding_factory.py

from langchain_community.embeddings import HuggingFaceEmbeddings
import torch
import os

# ✅ 检查是否有可用的 GPU（否则使用 CPU）
device = "cuda" if torch.cuda.is_available() else "cpu"

# ✅ 模型本地路径（相对或绝对均可）
local_model_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../models/bge-small-zh"
))

# ✅ 加载本地模型
_embedding_model = HuggingFaceEmbeddings(
    model_name=local_model_path,
    model_kwargs={"device": device},
    encode_kwargs={"normalize_embeddings": True}
)

def get_embedding_model():
    return _embedding_model