import os
import requests
from typing import List
from dotenv import load_dotenv, find_dotenv
from langchain.embeddings.base import Embeddings  # 必须继承这个基类

# 加载环境变量
_ = load_dotenv(find_dotenv())

class ZhipuEmbedding(Embeddings):
    def __init__(self):
        self.api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("未检测到 ZHIPUAI_API_KEY 环境变量")
        self.url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    def _embed(self, texts: List[str]) -> List[List[float]]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        vectors = []
        for idx, text in enumerate(texts):
            payload = {
                "model": "embedding-2",
                "input": text
            }
            res = requests.post(self.url, headers=headers, json=payload)

            print(f"[调试] 第 {idx + 1} 条文本返回状态码:", res.status_code)
            print(f"[调试] 第 {idx + 1} 条返回内容:", res.text)

            if res.status_code == 200:
                try:
                    embedding = res.json()["data"][0]["embedding"]
                    vectors.append(embedding)
                except KeyError:
                    raise ValueError(f"❌ 接口成功但返回格式异常: {res.json()}")
            else:
                raise ValueError(f"请求失败: {res.status_code}, {res.text}")
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]