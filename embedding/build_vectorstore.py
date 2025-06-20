import os
from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 加载环境变量
load_dotenv(find_dotenv())

# 加载原始文本
loader = TextLoader("data/act.txt", encoding="utf-8")
docs = loader.load()

# 文本切分
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
split_docs = text_splitter.split_documents(docs)

# 初始化 embedding 模型
embedding = ZhipuEmbedding()

# 构建向量索引
vectorstore = FAISS.from_documents(split_docs, embedding)

# 保存向量索引
save_path = "data/vectorstore/act"
os.makedirs(save_path, exist_ok=True)
vectorstore.save_local(save_path)

print(f"✅ 构建成功，共生成向量段数：{len(split_docs)}")
print(f"📁 向量已保存至: {save_path}")