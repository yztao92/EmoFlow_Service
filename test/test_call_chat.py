import requests
import json

url = "http://localhost:8000/chat"
data = {
    "session_id": "test-session-001",
    "messages": [
        {"role": "user", "content": "我今天有点难过"}
    ]
}

resp = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
print("状态码:", resp.status_code)
print("返回内容:", resp.json()) 