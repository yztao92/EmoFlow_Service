import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)

import json
import torch
from dotenv import load_dotenv, find_dotenv
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings  # ✅ 推荐新版路径

# 加载环境变量
load_dotenv(find_dotenv())

# 配置路径
input_path = "merged_data.jsonl"
output_dir = "embedding/vectorstore_by_summary_small_zh"
os.makedirs(output_dir, exist_ok=True)

# 加载数据
records = []
with open(input_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            records.append(obj)
        except Exception as e:
            print(f"⚠️ 第{idx}行解析出错: {e}\n内容: {line[:100]}")

# 构建文档
docs = []
for r in records:
    summary = r.get("summary", "").strip()
    if not summary:
        continue
    docs.append(Document(
        page_content=summary,
        metadata={
            "content": r.get("content", ""),
            "type": r.get("type", ""),
            "type_confidence": r.get("type_confidence", 0),
            "emotion": r.get("emotion", ""),
            "emotion_confidence": r.get("emotion_confidence", 0),
            "source": r.get("source", "")
        }
    ))

# ✅ 使用 BAAI/bge-small-zh 模型作为 embedding
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# 构建向量库
vectorstore = FAISS.from_documents(docs, embedding_model)
vectorstore.save_local(output_dir)

print(f"✅ 向量库已生成，共 {len(docs)} 条，存储于：{output_dir}")