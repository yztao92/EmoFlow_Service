import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
import json
from dotenv import load_dotenv, find_dotenv
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 加载环境变量
load_dotenv(find_dotenv())

# 配置路径
input_path = "merged_data.jsonl"
output_dir = "vectorstore_by_summary"
os.makedirs(output_dir, exist_ok=True)

records = []
with open("merged_data.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            records.append(obj)
        except Exception as e:
            print(f"⚠️ 第{idx}行解析出错: {e}\n内容: {line[:100]}")

# 构建向量库，推荐用 summary 字段作为向量内容
docs = []
for r in records:
    summary = r.get("summary", "").strip()
    if not summary:
        continue  # 没有 summary 跳过
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

# 嵌入模型
embedding = ZhipuEmbedding()
vectorstore = FAISS.from_documents(docs, embedding)
vectorstore.save_local(output_dir)

print(f"✅ 已生成向量库，{len(docs)} 条，存储在: {output_dir}")