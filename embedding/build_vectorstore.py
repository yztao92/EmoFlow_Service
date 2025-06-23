import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # 加入项目根目录

from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

# 加载 .env 环境变量
load_dotenv(find_dotenv())

# 设置目录
data_dir = "/root/EmoFlow/data"
save_base_path = "/root/EmoFlow/data/vectorstore"
os.makedirs(save_base_path, exist_ok=True)

# 清洗文本函数
def clean_text(text: str) -> str:
    skip_keywords = ["目录", "前言", "序言", "致谢", "版权", "附录", "Contents", "Preface", "Prologue"]
    lines = text.splitlines()
    cleaned = []
    skipping = False

    for line in lines:
        line = line.strip()
        if not line:  # 去除空行
            continue

        # 检测跳过开始
        if any(kw in line for kw in skip_keywords):
            skipping = True
            continue

        # 检测跳过结束（遇到正文特征）
        if skipping and (len(line) > 30 or line.startswith("第") or line[0].isdigit()):
            skipping = False

        if not skipping:
            cleaned.append(line)

    return "\n".join(cleaned)

# 初始化 embedding 模型
embedding = ZhipuEmbedding()

# 处理每个 txt 文件
txt_files = [f for f in os.listdir(data_dir) if f.endswith(".txt")]
for filename in txt_files:
    name = os.path.splitext(filename)[0]
    file_path = os.path.join(data_dir, filename)

    print(f"📘 正在处理: {filename}")

    # 加载并清洗文本
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    cleaned_text = clean_text(raw_text)
    docs = [Document(page_content=cleaned_text)]

    # 切割文本
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(docs)

    # 构建向量库
    vectorstore = FAISS.from_documents(split_docs, embedding)

    # 保存向量库
    save_path = os.path.join(save_base_path, name)
    os.makedirs(save_path, exist_ok=True)
    vectorstore.save_local(save_path)

    print(f"✅ 构建完成: {name}，段数: {len(split_docs)}")
    print(f"📂 保存路径: {save_path}\n")