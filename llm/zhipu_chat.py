# llm/zhipu_chat.py

from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.chat_models import ChatOpenAI  # 智谱用自定义 wrapper 替代
from langchain.vectorstores import FAISS
from vectorstore.load_vectorstore import get_vectorstore
from llm.zhipu_wrapper import ZhipuLLM  # 你需要自定义一个包装类，继承 BaseChatModel

def zhipu_chat(query: str) -> str:
    # 1. 加载向量库
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever()

    # 2. 构造提示模板
    prompt_template = """
    已知信息：
    {context}

    问题：
    {question}

    请结合已知信息回答问题，如果无法从中得到答案，请直接说“我不知道”。
    """
    prompt = PromptTemplate.from_template(prompt_template)

    # 3. 初始化 RAG Chain（ZhipuLLM 是你自定义的 LangChain wrapper）
    chain = RetrievalQA.from_chain_type(
        llm=ZhipuLLM(),  # 替代 ChatOpenAI
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt}
    )

    # 4. 执行查询
    result = chain.run(query)
    return result