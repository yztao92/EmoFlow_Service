import requests

query = "我失眠的时候可以做点什么？"

response = requests.post("http://127.0.0.1:8000/chat", json={"query": query})

try:
    result = response.json()
    if "response" in result:
        cleaned = result["response"]
        # 去除 markdown code 块标记（如 ```plaintext 和 ```）
        cleaned = cleaned.replace("```plaintext", "").replace("```", "").strip()
        print("[最终回答]\n", cleaned)
    else:
        print("[错误响应]", result)
except Exception as e:
    print("[解析失败]", e)
    print("原始响应内容：", response.text)