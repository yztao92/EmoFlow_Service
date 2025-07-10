# File: llm/embedding_factory.py
from langchain_huggingface import HuggingFaceEmbeddings
import torch

def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="/Users/yangzhentao/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/fake123456",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )