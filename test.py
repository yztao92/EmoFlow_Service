import requests
import uuid

def test_chat():
    url = "http://127.0.0.1:8000/chat"
    session_id = str(uuid.uuid4())
    test_messages = [
        {"role": "user", "content": "今天晚上本来要开会的，临时取消了哈哈哈哈哈，我可以早点下班了"}
    ]
    data = {
        "session_id": session_id,
        "messages": test_messages
    }
    resp = requests.post(url, json=data)
    print("AI 回复：", resp.json())

if __name__ == '__main__':
    test_chat()