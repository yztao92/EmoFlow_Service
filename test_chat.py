import requests

response = requests.post("http://127.0.0.1:8000/chat", json={
    "moodScore": 5,
    "messages": [
        {"role": "user", "content": "我失眠的时候可以做点什么？"}
    ]
})

try:
    result = response.json()
    if "response" in result:
        response_data = result["response"]
        if isinstance(response_data, str):
            # 去除 markdown code 块标记
            cleaned = response_data.replace("```plaintext", "").replace("```", "").strip()
            print("[最终回答]\n", cleaned)
        else:
            print("[错误响应]", response_data)
    else:
        print("[错误响应]", result)
except Exception as e:
    print("[解析失败]", e)
    print("原始响应内容：", response.text)