import requests

url = "http://127.0.0.1:8000/journal/generate"

payload = {
    "emotions": ["sad"],
    "messages": [
        {"role": "user", "content": "今天真的很累，一整天都在处理各种杂事。"},
        {"role": "assistant", "content": "听起来你今天承受了不少压力，要不要放松一下？"},
        {"role": "user", "content": "晚上想早点睡，感觉自己需要好好休息。"}
    ]
}

response = requests.post(url, json=payload)

print("✅ 返回状态码:", response.status_code)
print("📘 生成的心情日记:\n", response.json().get("journal", "没有返回 journal 字段"))