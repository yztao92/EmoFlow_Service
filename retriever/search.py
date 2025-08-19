# retriever/search.py
from typing import List

class Doc:
    def __init__(self, snippet: str):
        self.snippet = snippet

def retrieve(queries: List[str], top_k: int = 4) -> List[Doc]:
    # 这里先返回空列表，等你接入向量库后再实现
    return []