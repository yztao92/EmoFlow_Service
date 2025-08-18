# -*- coding: utf-8 -*-
# prompts/knowledge_retriever.py

from __future__ import annotations
from typing import List, Dict, Any
import hashlib
import re

# 关键：从 vectorstore 包里拿到适配器
from vectorstore.vectorstore_factory import get_vectorstore_adapter  # type: ignore

DEFAULT_TOP_K: int = 15
MAX_BULLETS: int = 3
MAX_CHARS_PER_BULLET: int = 120


def _normalize_text(t: str) -> str:
    if not t:
        return ""
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*([，。？！；：,.?!;:])\s*", r"\1", t)
    return t


def _hash_text(t: str) -> str:
    return hashlib.md5(t.encode("utf-8")).hexdigest()


def _dedupe(texts: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for t in texts:
        h = _hash_text(t)
        if h in seen:
            continue
        seen.add(h)
        out.append(t)
    return out


def _score_of(x: Dict[str, Any]) -> float:
    try:
        return float(x.get("score", 0.0) or 0.0)
    except Exception:
        return 0.0


def _distill_to_bullets(rows: List[Dict[str, Any]], max_bullets: int, max_chars: int) -> List[str]:
    cands: List[str] = []
    for r in rows:
        c = _normalize_text(str(r.get("content", "") or ""))
        if not c:
            continue
        c = c[:max_chars]
        if len(c) < 10:
            continue
        cands.append(c)
    cands = _dedupe(cands)
    return cands[:max_bullets]


def retrieve_bullets(queries: List[str], min_sim: float = 0.50, top_k: int = DEFAULT_TOP_K) -> List[str]:
    """
    输入:
      - queries: List[str]（建议 ≤3 条）
      - min_sim: 相似度阈值（0~1）
      - top_k:   召回上限
    输出:
      - bullets: List[str]  (≤3, 每条≤120字)
    """
    if not queries:
        return []

    vs = get_vectorstore_adapter()
    rows: List[Dict[str, Any]] = vs.search(queries, top_k=top_k)

    filtered = [r for r in rows if _score_of(r) >= float(min_sim)]
    filtered.sort(key=_score_of, reverse=True)

    return _distill_to_bullets(filtered, MAX_BULLETS, MAX_CHARS_PER_BULLET)