# ✅ 1. llm/zhipu_wrapper.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")

class ZhipuLLM(BaseChatModel):
    def _call(self, messages, **kwargs):
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ZHIPU_API_KEY}"
        }
        payload = {
            "model": "glm-4",
            "messages": [
                {"role": "user", "content": messages[-1].content}
            ]
        }
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    @property
    def _llm_type(self):
        return "zhipu-chat"

# ✅ 2. vectorstore/load_vectorstore.py 中新增 get_vectorstore()
from langchain_community.vectorstores import FAISS
from llm.zhipu_embedding import ZhipuEmbedding

VECTORSTORE_PATH = "data/vectorstore/act"

_vectorstore = None

def load_vectorstore():
    global _vectorstore
    embedding = ZhipuEmbedding()
    _vectorstore = FAISS.load_local(VECTORSTORE_PATH, embedding, allow_dangerous_deserialization=True)

def get_vectorstore():
    if _vectorstore is None:
        load_vectorstore()
    return _vectorstore

# ✅ 3. 修改 llm/zhipu_chat.py 实现 RAG
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from vectorstore.load_vectorstore import get_vectorstore
from llm.zhipu_wrapper import ZhipuLLM

prompt_template = """
已知信息：
{context}

问题：
{question}

请结合已知信息回答问题，如果无法从中得到答案，请直接说“我不知道”。
"""
prompt = PromptTemplate.from_template(prompt_template)

def zhipu_chat(query: str) -> str:
    retriever = get_vectorstore().as_retriever()
    chain = RetrievalQA.from_chain_type(
        llm=ZhipuLLM(),
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt}
    )
    return chain.run(query)