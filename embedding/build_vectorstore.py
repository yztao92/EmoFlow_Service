import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from llm.zhipu_embedding import ZhipuEmbedding

from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# 加载环境变量
load_dotenv(find_dotenv())

# 扫描 data 目录下所有 .txt 文件
data_dir = "/root/EmoFlow/data"
txt_files = [f for f in os.listdir(data_dir) if f.endswith(".txt")]

# 初始化 embedding 模型
embedding = ZhipuEmbedding()

for filename in txt_files:
    name = os.path.splitext(filename)[0]  # 去掉扩展名
    file_path = os.path.join(data_dir, filename)

    print(f"📘 正在处理: {filename}")
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(docs)

    vectorstore = FAISS.from_documents(split_docs, embedding)

    save_path = f"data/vectorstore/{name}"
    os.makedirs(save_path, exist_ok=True)
    vectorstore.save_local(save_path)

    print(f"✅ 构建完成: {name}，段数: {len(split_docs)}")
    print(f"📂 保存路径: {save_path}\n")