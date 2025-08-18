# File: llm/qwen_embedding_factory.py
# 功能：千问text-embedding-v4模型工厂
# 实现：提供千问embedding模型的统一接口

import logging
from typing import List
import dashscope
from dashscope import TextEmbedding

class QwenEmbeddingModel:
    """
    千问text-embedding-v4模型封装
    功能：提供文本向量化接口
    """
    
    def __init__(self, api_key: str = None):
        """
        初始化千问embedding模型
        
        参数：
            api_key (str): 千问API密钥，如果为None则从环境变量获取
        """
        if api_key:
            dashscope.api_key = api_key
        else:
            # 从环境变量获取API密钥
            import os
            api_key = os.getenv('QIANWEN_API_KEY')
            if not api_key:
                raise ValueError("未设置QIANWEN_API_KEY环境变量")
            dashscope.api_key = api_key
        
        self.model_name = "text-embedding-v4"
        # logging.info(f"✅ 千问Embedding模型初始化成功: {self.model_name}")
    
    def embed_query(self, text: str) -> List[float]:
        """
        对单个查询文本进行向量化
        
        参数：
            text (str): 查询文本
        
        返回：
            List[float]: 向量表示
        """
        try:
            response = TextEmbedding.call(
                model=self.model_name,
                input=text
            )
            
            if response.status_code == 200:
                embedding = response.output['embeddings'][0]['embedding']
                logging.debug(f"✅ 查询向量化成功: '{text[:50]}...'")
                return embedding
            else:
                logging.error(f"❌ 千问API调用失败: {response.message}")
                raise Exception(f"千问API错误: {response.message}")
                
        except Exception as e:
            logging.error(f"❌ 查询向量化失败: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文档进行批量向量化
        
        参数：
            texts (List[str]): 文档文本列表
        
        返回：
            List[List[float]]: 向量表示列表
        """
        try:
            response = TextEmbedding.call(
                model=self.model_name,
                input=texts
            )
            
            if response.status_code == 200:
                embeddings = [item['embedding'] for item in response.output['embeddings']]
                logging.debug(f"✅ 批量向量化成功: {len(texts)} 个文档")
                return embeddings
            else:
                logging.error(f"❌ 千问API调用失败: {response.message}")
                raise Exception(f"千问API错误: {response.message}")
                
        except Exception as e:
            logging.error(f"❌ 批量向量化失败: {e}")
            raise

# 全局embedding模型实例
_qwen_embedding_model = None

def get_qwen_embedding_model() -> QwenEmbeddingModel:
    """
    获取千问embedding模型实例（单例模式）
    
    返回：
        QwenEmbeddingModel: embedding模型实例
    """
    global _qwen_embedding_model
    if _qwen_embedding_model is None:
        _qwen_embedding_model = QwenEmbeddingModel()
    return _qwen_embedding_model

def set_qwen_embedding_model(api_key: str = None):
    """
    设置千问embedding模型
    
    参数：
        api_key (str): 千问API密钥
    """
    global _qwen_embedding_model
    _qwen_embedding_model = QwenEmbeddingModel(api_key) 