# test_chat_emotion.py

import requests

resp = requests.post("http://127.0.0.1:8000/chat", json={
    "emotions": ["tired"],   # 直接指定 emotion
    "messages": [
        {"role": "user", "content": "最近太累了，总睡不够，该怎么办？"}
    ]
})

print("HTTP 状态：", resp.status_code)
data = resp.json()
print("最终回答：", data["response"]["answer"])