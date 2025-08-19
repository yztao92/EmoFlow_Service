# File: llm/llm_factory.py
# 功能：LLM工厂，统一管理不同的LLM调用
# 实现：提供统一的LLM接口，支持多种LLM模型

import logging
from typing import Dict, Any, Callable
from langchain_core.messages import HumanMessage

# 导入LLM包装器
from llm.deepseek_wrapper import DeepSeekLLM
from llm.qwen_llm import QwenLLM

# 全局LLM实例
_deepseek_llm = None
_qwen_llm = None

def get_deepseek_llm() -> DeepSeekLLM:
    global _deepseek_llm
    if _deepseek_llm is None:
        _deepseek_llm = DeepSeekLLM()
    return _deepseek_llm

def get_qwen_llm() -> QwenLLM:
    global _qwen_llm
    if _qwen_llm is None:
        _qwen_llm = QwenLLM()
    return _qwen_llm

def _call_to_str(call_fn: Callable[[str], Any], prompt: str) -> str:
    """统一把模型输出转成字符串，避免上游类型不一致"""
    out = call_fn(prompt)
    return out if isinstance(out, str) else str(out)

# === 生成链路共用：返回【纯字符串】 ===
def chat_with_llm(prompt: str) -> str:
    """
    统一的LLM调用接口（默认使用千问LLM）
    返回：纯字符串
    """
    try:
        qwen = get_qwen_llm()
        return _call_to_str(lambda p: qwen._call([HumanMessage(content=p)]), prompt)
    except Exception as e:
        logging.error("❌ 千问LLM调用失败：%s", e)

        # 兜底重试 DeepSeek
        try:
            deepseek = get_deepseek_llm()
            resp = _call_to_str(lambda p: deepseek._call([HumanMessage(content=p)]), prompt)
            logging.info("✅ 使用 DeepSeek 作为备用成功，长度=%d", len(resp))
            return resp
        except Exception as backup_e:
            logging.error("❌ 备用 DeepSeek 也失败：%s", backup_e)
            return "抱歉，我现在无法生成回复，请稍后再试。"

# === 日记模块用：保持【dict】返回，兼容原有调用 ===
def chat_with_qwen_llm(prompt: str) -> Dict[str, Any]:
    """
    千问LLM调用接口（返回 dict，包含 answer 字段）
    """
    try:
        qwen = get_qwen_llm()
        resp = _call_to_str(lambda p: qwen._call([HumanMessage(content=p)]), prompt)
        return {"answer": resp}
    except Exception as e:
        logging.error("❌ 千问LLM调用失败：%s", e)
        return {"answer": "抱歉，我现在无法生成回复，请稍后再试。"}

def chat_with_deepseek_llm(prompt: str) -> str:
    """
    DeepSeek LLM调用接口（返回纯字符串，以便通用）
    """
    try:
        deepseek = get_deepseek_llm()
        return _call_to_str(lambda p: deepseek._call([HumanMessage(content=p)]), prompt)
    except Exception as e:
        logging.error("❌ DeepSeek LLM调用失败：%s", e)
        return "抱歉，我现在无法生成回复，请稍后再试。"