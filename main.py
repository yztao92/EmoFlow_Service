# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# ===== 文本预处理与向量库构建 =====
def build_vectorstore():
    documents = []
    for filename in ["data/act.txt", "data/jin_gang_jing.txt"]:
        loader = TextLoader(filename, encoding="utf-8")
        docs = loader.load()
        documents.extend(docs)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectorstore = FAISS.from_documents(split_docs, embedding=embeddings)
    vectorstore.save_local("vectorstore")
    return vectorstore

# 如果 vectorstore 不存在，则构建
if not os.path.exists("vectorstore"):
    build_vectorstore()

# 加载已保存的向量数据库
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vectorstore = FAISS.load_local("vectorstore", embeddings)
qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(openai_api_key=OPENAI_API_KEY), retriever=vectorstore.as_retriever())

# ===== 定义 API 输入输出 =====
class QARequest(BaseModel):
    question: str

class QAResponse(BaseModel):
    answer: str

@app.post("/rag", response_model=QAResponse)
async def rag_answer(request: QARequest):
    try:
        response = qa.run(request.question)
        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))