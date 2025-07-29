# File: llm/embedding_factory.py
# 功能：Embedding模型工厂，统一管理文本向量化模型
# 实现：加载本地bge-small-zh模型，提供统一的embedding接口

from langchain_community.embeddings import HuggingFaceEmbeddings  # HuggingFace embedding模型
import torch  # PyTorch，用于GPU/CPU设备检测
import os  # 操作系统接口，用于路径处理

# ==================== 设备检测 ====================
# 检查是否有可用的 GPU，如果没有则使用 CPU
# 参数来源：torch.cuda.is_available() 自动检测系统GPU状态
device = "cuda" if torch.cuda.is_available() else "cpu"

# ==================== 模型路径配置 ====================
# 模型本地路径（相对或绝对均可）
# 参数来源：项目目录结构，模型存储在 models/bge-small-zh 目录下
local_model_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../models/bge-small-zh"  # 相对于当前文件的路径
))

# ==================== 模型初始化 ====================
# 加载本地 bge-small-zh 模型
# 参数说明：
# - model_name: 模型路径，指向本地bge-small-zh模型
# - model_kwargs: 模型参数，指定使用GPU或CPU
# - encode_kwargs: 编码参数，启用embedding归一化
_embedding_model = HuggingFaceEmbeddings(
    model_name=local_model_path,  # 本地模型路径
    model_kwargs={"device": device},  # 设备配置（GPU/CPU）
    encode_kwargs={"normalize_embeddings": True}  # 启用embedding归一化
)

def get_embedding_model():
    """
    获取embedding模型实例
    
    返回：
        HuggingFaceEmbeddings: 已初始化的embedding模型实例
    
    说明：
        此函数提供统一的embedding模型访问接口
        被vectorstore/load_vectorstore.py和rag/rag_chain.py调用
        确保整个项目使用同一个embedding模型实例
    """
    return _embedding_model