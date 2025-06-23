from llm.zhipu_rag import zhipu_chat_rag

def get_chat_response(query: str, category: str = "default"):
    try:
        result = zhipu_chat_rag(query, category)

        answer = result.get("answer", "很抱歉，AI 暂时没有给出回应。")
        references = result.get("references", [])

        print("\n🤖 [AI 回答内容]")
        print(answer)

        print("\n📚 [引用内容片段]")
        for i, ref in enumerate(references):
            print(f" - [{i+1}] {ref}")

        return {
            "answer": answer,
            "references": references
        }

    except Exception as e:
        print("[❌ ERROR] 聊天接口处理失败:", e)
        return {"answer": "AI 无法响应", "references": []}