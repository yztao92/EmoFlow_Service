import os, sys

# 把项目根目录加入到 Python 模块搜索路径
# 假设你的目录结构是：
# /root/EmoFlow/
#   embedding/build_vectorstore.py
#   llm/zhipu_embedding.py
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)

from llm.zhipu_embedding import ZhipuEmbedding
# 后面正常写你的逻辑...
import json
from itertools import groupby
from dotenv import load_dotenv, find_dotenv

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 加载环境变量（如果你的项目需要）
load_dotenv(find_dotenv())

# 路径配置
data_dir     = "/root/EmoFlow/data"
json_path    = os.path.join(data_dir, "merged_cleaned_conversations.json")
store_base   = os.path.join(data_dir, "vectorstore_by_emotion")

# 确保输出目录存在
os.makedirs(store_base, exist_ok=True)

# 1. 读取合并后的 JSON
with open(json_path, "r", encoding="utf-8") as f:
    records = json.load(f)

# 2. 按 emotion_type 排序并分组
records.sort(key=lambda r: r["emotion_type"])
for emo, group in groupby(records, key=lambda r: r["emotion_type"]):
    docs = []
    for r in group:
        # 构建 Document：page_content 为内容，metadata 可以存 topic
        docs.append(Document(
            page_content=r["content"],
            metadata={"topic": r["topic"]}
        ))

    # 3. （可选）长文本拆分
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    split_docs = splitter.split_documents(docs)

    # 4. 嵌入并构建 FAISS 索引
    embedding = ZhipuEmbedding()
    vs = FAISS.from_documents(split_docs, embedding)

    # 5. 保存到对应子目录
    emo_dir = os.path.join(store_base, emo)
    os.makedirs(emo_dir, exist_ok=True)
    vs.save_local(emo_dir)

    print(f"✅ 已生成情绪 “{emo}” 的向量库，共 {len(split_docs)} 段，路径：{emo_dir}")