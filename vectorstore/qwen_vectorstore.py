# File: vectorstore/qwen_vectorstore.py
# 功能：使用千问text-embedding-v4模型的向量库检索系统
# 实现：加载FAISS向量库 + SQLite元数据库，提供检索接口

import faiss
import sqlite3
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
import os

class QwenVectorStore:
    """
    千问向量库检索器
    功能：加载FAISS向量库和SQLite元数据库，提供相似度检索
    """
    
    def __init__(self, faiss_path: str, metadata_path: str):
        """
        初始化向量库检索器
        
        参数：
            faiss_path (str): FAISS向量库文件路径
            metadata_path (str): SQLite元数据库文件路径
        """
        self.faiss_path = faiss_path
        self.metadata_path = metadata_path
        self.index = None
        self.embedding_model = None
        self.metadata_conn = None
        
        # 加载向量库和元数据库
        self._load_faiss_index()
        self._load_metadata_db()
        
    def _load_faiss_index(self):
        """加载FAISS向量库"""
        try:
            if not os.path.exists(self.faiss_path):
                raise FileNotFoundError(f"FAISS向量库文件不存在: {self.faiss_path}")
            
            self.index = faiss.read_index(self.faiss_path)
            # logging.info(f"✅ FAISS向量库加载成功: {self.faiss_path}")
            # logging.info(f"📊 向量库信息: {self.index.ntotal} 个向量, 维度: {self.index.d}")
            
        except Exception as e:
            logging.error(f"❌ FAISS向量库加载失败: {e}")
            raise
    
    def _load_metadata_db(self):
        """加载SQLite元数据库"""
        try:
            if not os.path.exists(self.metadata_path):
                raise FileNotFoundError(f"元数据库文件不存在: {self.metadata_path}")
            
            self.metadata_conn = sqlite3.connect(self.metadata_path)
            # 测试连接
            cursor = self.metadata_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata")
            count = cursor.fetchone()[0]
            # logging.info(f"✅ 元数据库加载成功: {self.metadata_path}")
            # logging.info(f"📊 元数据记录数: {count}")
            
        except Exception as e:
            logging.error(f"❌ 元数据库加载失败: {e}")
            raise
    
    def set_embedding_model(self, embedding_model):
        """
        设置embedding模型
        
        参数：
            embedding_model: 千问embedding模型实例
        """
        self.embedding_model = embedding_model
        # logging.info("✅ Embedding模型设置成功")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        执行向量检索
        
        参数：
            query (str): 查询文本
            k (int): 返回结果数量
        
        返回：
            List[Dict[str, Any]]: 检索结果列表，包含相似度和元数据
        """
        if self.embedding_model is None:
            raise ValueError("Embedding模型未设置")
        
        # 1. 生成查询向量
        query_vector = self.embedding_model.embed_query(query)
        query_vector = np.array(query_vector).reshape(1, -1).astype('float32')
        
        # 2. FAISS检索（使用IndexIDMap，直接返回ID）
        distances, ids = self.index.search(query_vector, k)
        
        # 3. 获取元数据
        results = []
        cursor = self.metadata_conn.cursor()
        
        for distance, doc_id in zip(distances[0], ids[0]):
            if doc_id == -1:  # FAISS返回-1表示无效索引
                continue
                
            # 查询元数据（使用原始ID）
            cursor.execute("""
                SELECT id, url, title, question, answer_text, answer_summary, 
                       key_point, suggestion, topic, source, embedding_text
                FROM metadata WHERE id = ?
            """, (str(int(doc_id)),))  # 转换为字符串ID
            
            row = cursor.fetchone()
            if row:
                # 将距离转换为相似度（1 - 距离）
                similarity = 1.0 - float(distance)
                
                metadata = {
                    'id': row[0],
                    'url': row[1],
                    'title': row[2],
                    'question': row[3],
                    'answer_text': row[4],
                    'answer_summary': row[5],
                    'key_point': row[6],
                    'suggestion': row[7],
                    'topic': row[8],
                    'source': row[9],
                    'embedding_text': row[10],
                    'similarity': similarity,
                    'distance': float(distance)
                }
                results.append(metadata)
        
        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # logging.info(f"🔍 检索完成: 查询='{query[:50]}...', 返回 {len(results)} 个结果")
        # for i, result in enumerate(results[:3]):  # 只记录前3个结果
        #     logging.info(f"  {i+1}. 相似度 {result['similarity']:.3f} - {result['title'][:50]}...")
        
        return results
    
    def get_metadata_by_id(self, doc_id: str) -> Dict[str, Any]:
        """
        根据文档ID获取元数据
        
        参数：
            doc_id (str): 文档ID
        
        返回：
            Dict[str, Any]: 元数据字典
        """
        cursor = self.metadata_conn.cursor()
        cursor.execute("""
            SELECT id, url, title, question, answer_text, answer_summary, 
                   key_point, suggestion, topic, source, embedding_text
            FROM metadata WHERE id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'question': row[3],
                'answer_text': row[4],
                'answer_summary': row[5],
                'key_point': row[6],
                'suggestion': row[7],
                'topic': row[8],
                'source': row[9],
                'embedding_text': row[10]
            }
        return None
    
    def close(self):
        """关闭数据库连接"""
        if self.metadata_conn:
            self.metadata_conn.close()
            # logging.info("✅ 元数据库连接已关闭")

# 全局向量库实例
_qwen_vectorstore = None

def get_qwen_vectorstore() -> QwenVectorStore:
    """
    获取千问向量库实例（每次调用都创建新实例，避免线程问题）
    
    返回：
        QwenVectorStore: 向量库实例
    """
    faiss_path = "dataset/faiss_index.bin"
    metadata_path = "dataset/metadata.db"
    vectorstore = QwenVectorStore(faiss_path, metadata_path)
    
    # 动态设置embedding模型
    try:
        from llm.qwen_embedding_factory import get_qwen_embedding_model
        embedding_model = get_qwen_embedding_model()
        vectorstore.set_embedding_model(embedding_model)
    except Exception as e:
        logging.warning(f"⚠️ 动态设置embedding模型失败: {e}")
    
    return vectorstore

def set_qwen_embedding_model(embedding_model):
    """
    设置千问embedding模型
    
    参数：
        embedding_model: 千问embedding模型实例
    """
    vectorstore = get_qwen_vectorstore()
    vectorstore.set_embedding_model(embedding_model) 