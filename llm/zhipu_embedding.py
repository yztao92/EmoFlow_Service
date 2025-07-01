import os
import requests
from typing import List
from dotenv import load_dotenv, find_dotenv
from langchain_core.embeddings import Embeddings  # 新版 langchain

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
        # 支持批量，每次最多 16 条，API 限制
        vectors = []
        BATCH = 16
        for i in range(0, len(texts), BATCH):
            batch = texts[i:i+BATCH]
            payload = {
                "model": "embedding-2",
                "input": batch if len(batch) > 1 else batch[0]
            }
            res = requests.post(self.url, headers=headers, json=payload)
            if res.status_code == 200:
                try:
                    embeddings = res.json()["data"]
                    # data 是数组，每个元素里有 embedding
                    vectors.extend([item["embedding"] for item in embeddings])
                except Exception as e:
                    raise ValueError(f"接口成功但格式异常: {res.text}")
            else:
                print(f"请求失败: {res.status_code} - {res.text}")
                raise ValueError(f"Zhipu API 请求失败")
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]