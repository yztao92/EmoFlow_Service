# prompts/knowledge_retriever.py
from typing import List, Dict, Any
import logging
from llm.llm_factory import chat_with_llm

MIN_SIM = 0.50
TOP_K = 15

# 按你的实现替换
from vectorstore.qwen_vectorstore import get_qwen_vectorstore

def _distill_snippets(docs: List[Dict[str, Any]], max_items:int=3) -> List[str]:
    if not docs:
        return []
    joined = "\n\n".join([f"【{i+1}】{d.get('content','')[:600]}" for i,d in enumerate(docs[:5])])
    logging.info("📝 [提炼] 输入材料条数=%d", len(docs))
    prompt = f"""请从以下材料提炼 2–3 条“可执行建议”，口语化，每条≤20字。
避免空话、诊断或处方，不要带来源口吻。

材料：
{joined}

只输出条目，每行一条。
"""
    res = chat_with_llm(prompt)
    answer = res.get("answer", "")
    
    # 确保answer是字符串类型
    if not isinstance(answer, str):
        logging.warning(f"⚠️ [提炼] answer不是字符串类型: {type(answer)}, 内容: {answer}")
        answer = str(answer) if answer else ""
    
    bullets = [line.strip(" -•·").strip() for line in (answer.split("\n")) if line.strip()]
    return bullets[:max_items]

def retrieve_bullets(queries: List[str]) -> List[str]:
    if not queries:
        logging.info("⚠️ [检索] 无 queries，返回空")
        return []

    logging.info(f"🚀 [检索] 开始知识检索，查询数量: {len(queries)}")
    logging.info(f"🔍 [检索] 查询列表: {queries}")
    
    vs = get_qwen_vectorstore()
    cands: List[Dict[str,Any]] = []

    for i, qtext in enumerate(queries):
        logging.info(f"📝 [检索] 处理第 {i+1}/{len(queries)} 个查询")
        
        # 处理字典格式的查询
        if isinstance(qtext, dict):
            qtext = qtext.get("q", "")
            logging.info(f"🔍 [检索] 从字典提取查询: '{qtext}'")
        elif not isinstance(qtext, str):
            logging.warning(f"⚠️ [检索] qtext不是字符串类型: {type(qtext)}, 内容: {qtext}")
            qtext = str(qtext) if qtext else ""
        
        if not qtext:
            continue
        
        qtext = qtext.strip()
        if not qtext:
            continue
        
        logging.info(f"🔎 [检索] 执行向量搜索: '{qtext}'")
        
        # 调用向量库搜索（去掉top_k参数）
        try:
            hits = vs.search(qtext)
            logging.info(f"✅ [检索] 搜索完成: '{qtext}' → 找到 {len(hits)} 条结果")
            
            # 打印前3个结果的详细信息
            for j, hit in enumerate(hits[:3]):
                similarity = hit.get('similarity', 0)
                title = hit.get('title', '无标题')[:50]
                logging.info(f"  📊 [检索] 结果 {j+1}: 相似度 {similarity:.3f} - {title}...")
            
            cands.extend(hits)
            
        except Exception as e:
            logging.error(f"❌ [检索] 搜索失败: '{qtext}' - 错误: {e}")
            continue

    # 去重 + 按相似度降序
    seen, uniq = set(), []
    for d in sorted(cands, key=lambda x: x.get("similarity",0), reverse=True):
        doc_id = d.get("id") or hash(d.get("content","")[:200])
        if doc_id in seen:
            continue
        seen.add(doc_id)
        uniq.append(d)

    # 阈值过滤
    filtered = [d for d in uniq if d.get("similarity",0) >= MIN_SIM]
    logging.info("✅ [阈值] 通过=%d / 去重后=%d (阈值=%.2f)", len(filtered), len(uniq), MIN_SIM)

    return _distill_snippets(filtered, max_items=3)