# -*- coding: utf-8 -*-
# vectorstore/vectorstore_factory.py
"""
适配器：把底层 QwenVectorStore（单 query 检索 + 自定义元数据）
封装成多 query 融合检索，并统一返回字段：
  - content: str   （用于蒸馏 bullets）
  - score: float   （相似度 0~1）
  - meta:  Dict    （保留原始元数据）
"""

from __future__ import annotations
from typing import List, Dict, Any
import logging
import math

# 复用你的底层实现
from vectorstore.qwen_vectorstore import get_qwen_vectorstore  # type: ignore


class VectorStoreAdapter:
    """对接 QwenVectorStore，提供 .search(queries, top_k) 接口"""

    def __init__(self) -> None:
        # 你的 get_qwen_vectorstore 会 new 一个实例并注入 embedding_model
        self._store = get_qwen_vectorstore()

    @staticmethod
    def _choose_content(row: Dict[str, Any]) -> str:
        """
        选择更精炼的字段作为 bullets 文本来源（有就用，无则回退）：
        key_point > answer_summary > embedding_text > answer_text > question > title
        """
        for f in ("key_point", "answer_summary", "embedding_text", "answer_text", "question", "title"):
            v = (row.get(f) or "").strip()
            if v:
                return v
        return ""

    @staticmethod
    def _norm_score(row: Dict[str, Any]) -> float:
        """
        统一相似度分数为 [0,1]：
        - 优先使用 row["similarity"]（你的实现里是 1 - distance）
        - 若只有 distance，则做保守映射
        """
        if "similarity" in row and row["similarity"] is not None:
            try:
                return float(row["similarity"])
            except Exception:
                pass
        if "distance" in row and row["distance"] is not None:
            try:
                d = float(row["distance"])
                return max(0.0, min(1.0, 1.0 / (1.0 + d)))
            except Exception:
                pass
        return 0.0

    def search(self, queries: List[str], top_k: int = 15) -> List[Dict[str, Any]]:
        """
        多 query 融合检索：
        - 对每个 query 取 ceil(top_k / len(queries)) 条（下限 5）
        - 以 id 去重；同一 id 分数取更大者
        - 输出统一字段：content/score/meta
        """
        if not queries:
            return []

        per_q = max(5, int(math.ceil(top_k / max(1, len(queries)))))
        pool: Dict[str, Dict[str, Any]] = {}

        for q in queries:
            try:
                hits = self._store.search(q, k=per_q)  # 你的底层接口：单 query
            except Exception as e:
                logging.warning(f"[VectorStoreAdapter] search('{q}') 失败：{e}")
                continue

            for row in hits:
                doc_id = str(row.get("id", "") or "")
                if not doc_id:
                    continue

                score = self._norm_score(row)
                content = self._choose_content(row)

                item = {
                    "content": content,
                    "score": score,
                    "meta": row,  # 原样保留你的元数据（包含 title/url/...）
                }

                if doc_id not in pool:
                    pool[doc_id] = item
                else:
                    # 分数更高的覆盖
                    if score > pool[doc_id]["score"]:
                        pool[doc_id] = item

        results = list(pool.values())
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# 工厂方法：供上层调用
def get_vectorstore_adapter() -> VectorStoreAdapter:
    return VectorStoreAdapter()