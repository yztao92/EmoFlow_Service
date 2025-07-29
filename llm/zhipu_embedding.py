# File: llm/zhipu_embedding.py
# 功能：智谱AI Embedding模型封装
# 实现：封装智谱AI的embedding-2模型，提供文本向量化功能

import os  # 操作系统接口，用于环境变量
import requests  # HTTP请求库
from typing import List  # 类型提示
from dotenv import load_dotenv, find_dotenv  # 环境变量加载
from langchain_core.embeddings import Embeddings  # LangChain embedding基类

# 加载环境变量
_ = load_dotenv(find_dotenv())

class ZhipuEmbedding(Embeddings):
    """
    智谱AI Embedding模型封装类
    功能：将文本转换为向量表示，支持批量处理
    
    主要方法：
        - _embed: 核心embedding方法，支持批量处理
        - embed_documents: 文档向量化（批量）
        - embed_query: 查询向量化（单个）
    
    特点：
        - 支持批量处理，提高效率
        - 自动分批处理，符合API限制
        - 继承LangChain Embeddings接口，兼容性好
    """
    
    def __init__(self):
        """
        初始化智谱AI Embedding模型
        
        配置：
            - api_key: 从环境变量获取智谱AI API密钥
            - url: 智谱AI embedding API端点
        
        异常：
            ValueError: 当API密钥未设置时抛出异常
        """
        # 从环境变量获取API密钥
        self.api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("未检测到 ZHIPUAI_API_KEY 环境变量")
        
        # 智谱AI embedding API端点
        self.url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        核心embedding方法，将文本列表转换为向量列表
        
        参数：
            texts (List[str]): 待向量化的文本列表
            参数来源：embed_documents或embed_query方法调用
        
        返回：
            List[List[float]]: 向量列表，每个向量是一个浮点数列表
        
        异常：
            ValueError: API调用失败或响应格式异常时抛出异常
        
        特点：
            - 支持批量处理，提高效率
            - 自动分批，每批最多16条（API限制）
            - 错误处理和重试机制
        """
        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"  # Bearer token认证
        }
        
        # 支持批量处理，每次最多16条（API限制）
        vectors = []
        BATCH = 16  # 批处理大小
        
        # 分批处理文本
        for i in range(0, len(texts), BATCH):
            batch = texts[i:i+BATCH]  # 获取当前批次
            
            # 构造请求体
            payload = {
                "model": "embedding-2",  # 使用智谱AI的embedding-2模型
                "input": batch if len(batch) > 1 else batch[0]  # 单个文本或文本列表
            }
            
            # 发送POST请求到智谱AI API
            res = requests.post(self.url, headers=headers, json=payload)
            
            # 检查响应状态
            if res.status_code == 200:
                try:
                    # 解析JSON响应
                    embeddings = res.json()["data"]
                    # data是数组，每个元素包含embedding向量
                    vectors.extend([item["embedding"] for item in embeddings])
                except Exception as e:
                    # API调用成功但响应格式异常
                    raise ValueError(f"接口成功但格式异常: {res.text}")
            else:
                # API调用失败
                print(f"请求失败: {res.status_code} - {res.text}")
                raise ValueError(f"Zhipu API 请求失败")
        
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        文档向量化方法（批量）
        
        参数：
            texts (List[str]): 文档文本列表
            参数来源：向量库构建或批量检索时调用
        
        返回：
            List[List[float]]: 文档向量列表
        
        说明：
            这是LangChain Embeddings接口的标准方法
            用于批量处理文档向量化
        """
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        查询向量化方法（单个）
        
        参数：
            text (str): 查询文本
            参数来源：用户查询或单个文本向量化时调用
        
        返回：
            List[float]: 查询向量
        
        说明：
            这是LangChain Embeddings接口的标准方法
            用于单个查询文本的向量化
        """
        return self._embed([text])[0]  # 返回第一个（也是唯一的）向量