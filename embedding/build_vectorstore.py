# File: embedding/build_vectorstore.py
# 功能：构建向量数据库
# 实现：从JSONL数据文件构建FAISS向量库，用于知识检索

import os, sys  # 操作系统接口和系统路径
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # 获取项目根目录
sys.path.insert(0, root)  # 将项目根目录添加到Python路径
import json  # JSON处理
from dotenv import load_dotenv, find_dotenv  # 环境变量加载
from langchain.schema import Document  # LangChain文档模型
from langchain_community.vectorstores import FAISS  # FAISS向量数据库
from llm.zhipu_embedding import ZhipuEmbedding  # 智谱AI embedding模型

# 加载环境变量
load_dotenv(find_dotenv())

# ==================== 路径配置 ====================
# 输入文件路径：包含知识数据的JSONL文件
# 参数来源：项目数据文件，包含心理知识内容
input_path = "merged_data.jsonl"

# 输出目录：向量库存储路径
# 参数来源：项目配置，向量库将存储在此目录
output_dir = "vectorstore_by_summary"
os.makedirs(output_dir, exist_ok=True)  # 创建输出目录（如果不存在）

# ==================== 数据加载 ====================
# 从JSONL文件加载知识数据
records = []
with open("merged_data.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):  # 逐行读取，从1开始计数
        line = line.strip()  # 去除首尾空白
        if not line:
            continue  # 跳过空行
        try:
            obj = json.loads(line)  # 解析JSON行
            records.append(obj)  # 添加到记录列表
        except Exception as e:
            print(f"⚠️ 第{idx}行解析出错: {e}\n内容: {line[:100]}")  # 记录解析错误

# ==================== 文档构建 ====================
# 构建LangChain文档对象，推荐用summary字段作为向量内容
docs = []
for r in records:
    summary = r.get("summary", "").strip()  # 获取摘要字段
    if not summary:
        continue  # 没有summary的跳过
    
    # 创建Document对象，包含内容和元数据
    docs.append(Document(
        page_content=summary,  # 文档内容（用于向量化）
        metadata={
            "content": r.get("content", ""),  # 原始内容
            "type": r.get("type", ""),  # 知识类型
            "type_confidence": r.get("type_confidence", 0),  # 类型置信度
            "emotion": r.get("emotion", ""),  # 情绪标签
            "emotion_confidence": r.get("emotion_confidence", 0),  # 情绪置信度
            "source": r.get("source", "")  # 数据来源
        }
    ))

# ==================== 向量库构建 ====================
# 初始化embedding模型
embedding = ZhipuEmbedding()  # 使用智谱AI的embedding模型

# 从文档构建FAISS向量库
vectorstore = FAISS.from_documents(docs, embedding)

# 保存向量库到本地目录
vectorstore.save_local(output_dir)

# 输出构建结果
print(f"✅ 已生成向量库，{len(docs)} 条，存储在: {output_dir}")