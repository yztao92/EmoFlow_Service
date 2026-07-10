# File: llm/llm_factory.py
# 功能：LLM工厂，统一管理不同的LLM调用
# 实现：提供统一的LLM接口，支持多种LLM模型

import logging
from typing import Dict, Any, Callable, List
from langchain_core.messages import HumanMessage

# 导入LLM包装器
from llm.deepseek_wrapper import DeepSeekLLM
from llm.doubao_llm import DoubaoLLM

# 全局LLM实例
_deepseek_llm = None
_doubao_llm = None

def get_deepseek_llm() -> DeepSeekLLM:
    global _deepseek_llm
    if _deepseek_llm is None:
        _deepseek_llm = DeepSeekLLM()
    return _deepseek_llm

def get_doubao_llm() -> DoubaoLLM:
    global _doubao_llm
    if _doubao_llm is None:
        _doubao_llm = DoubaoLLM()
    return _doubao_llm

def _call_to_str(call_fn: Callable[[str], Any], prompt: str) -> str:
    """统一把模型输出转成字符串，避免上游类型不一致"""
    out = call_fn(prompt)
    return out if isinstance(out, str) else str(out)

# === 生成链路共用：返回【纯字符串】 ===
def chat_with_llm(prompt: str) -> str:
    """
    统一的LLM调用接口（默认使用豆包LLM）
    返回：纯字符串
    """
    try:
        doubao = get_doubao_llm()
        return _call_to_str(lambda p: doubao._call([HumanMessage(content=p)]), prompt)
    except Exception as e:
        logging.error("❌ 豆包LLM调用失败：%s", e)

        # 兜底重试 DeepSeek
        try:
            deepseek = get_deepseek_llm()
            resp = _call_to_str(lambda p: deepseek._call([HumanMessage(content=p)]), prompt)
            logging.debug("✅ 使用 DeepSeek 作为备用成功，长度=%d", len(resp))
            return resp
        except Exception as backup_e:
            logging.error("❌ 备用 DeepSeek 也失败：%s", backup_e)
            return "抱歉，我现在无法生成回复，请稍后再试。"

def chat_with_llm_messages(messages: List[Dict[str, str]]) -> str:
    """
    使用消息列表格式调用LLM（支持system + 历史对话 + 当前输入）
    返回：纯字符串
    """
    try:
        doubao = get_doubao_llm()
        # 将字典格式转换为LangChain消息格式
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                from langchain_core.messages import SystemMessage
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                from langchain_core.messages import HumanMessage
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                from langchain_core.messages import AIMessage
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # 打印最终输入到LLM API的原始JSON数据（降为DEBUG）
        logging.debug("=" * 80)
        logging.debug("🚀 最终输入到LLM API的原始JSON数据")
        logging.debug("=" * 80)
        
        # 将LangChain消息转换回JSON格式
        import json
        json_messages = []
        for msg in langchain_messages:
            # 根据LangChain消息类型映射到标准角色名称
            if msg.__class__.__name__ == "HumanMessage":
                role = "user"
            elif msg.__class__.__name__ == "AIMessage":
                role = "assistant"
            elif msg.__class__.__name__ == "SystemMessage":
                role = "system"
            else:
                role = "user"  # 默认为用户消息
            
            json_messages.append({
                "role": role,
                "content": msg.content
            })
        
        # 打印完整的JSON数据（降为DEBUG）
        logging.debug(json.dumps(json_messages, ensure_ascii=False, indent=2))
        logging.debug("=" * 80)
        
        return _call_to_str(lambda msgs: doubao._call(msgs), langchain_messages)
    except Exception as e:
        logging.error("❌ 豆包LLM消息列表调用失败：%s", e)
        return "抱歉，我现在无法生成回复，请稍后再试。"

# === 日记模块用：保持【dict】返回，兼容原有调用 ===
def chat_with_doubao_llm(prompt: str) -> Dict[str, Any]:
    """
    豆包LLM调用接口（返回 dict，包含 answer 字段）
    """
    try:
        doubao = get_doubao_llm()
        resp = _call_to_str(lambda p: doubao._call([HumanMessage(content=p)]), prompt)
        return {"answer": resp}
    except Exception as e:
        logging.error("❌ 豆包LLM调用失败：%s", e)
        return {"answer": "抱歉，我现在无法生成回复，请稍后再试。"}


# 保留旧函数名，避免外部调用方升级时立即中断。
chat_with_qwen_llm = chat_with_doubao_llm

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
