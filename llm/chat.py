from llm.zhipu_rag import zhipu_chat_rag

def get_chat_response(query: str, retriever):
    try:
        print(f"[请求内容] query = {query}")
        answer = zhipu_chat_rag(query, retriever)
        print(f"[响应内容] result = {answer}")
        return {"response": answer}
    except Exception as e:
        print("[ERROR] 聊天接口处理失败:", e)
        return {"error": str(e)}