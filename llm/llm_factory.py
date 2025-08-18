# File: llm/llm_factory.py
# 功能：LLM工厂，统一管理不同的LLM调用
# 实现：提供统一的LLM接口，支持多种LLM模型

import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage

# 导入LLM包装器
from llm.deepseek_wrapper import DeepSeekLLM
from llm.qwen_llm import QwenLLM

# 全局LLM实例
_deepseek_llm = None
_qwen_llm = None

def get_deepseek_llm() -> DeepSeekLLM:
    """
    获取DeepSeek LLM实例（单例模式）
    
    返回：
        DeepSeekLLM: DeepSeek LLM实例
    """
    global _deepseek_llm
    if _deepseek_llm is None:
        _deepseek_llm = DeepSeekLLM()
    return _deepseek_llm

def get_qwen_llm() -> QwenLLM:
    """
    获取千问LLM实例（单例模式）
    
    返回：
        QwenLLM: 千问LLM实例
    """
    global _qwen_llm
    if _qwen_llm is None:
        _qwen_llm = QwenLLM()
    return _qwen_llm

def chat_with_llm(prompt: str) -> Dict[str, Any]:
    """
    统一的LLM调用接口（默认使用千问LLM）
    
    参数：
        prompt (str): 完整的提示词
    
    返回：
        Dict[str, Any]: 包含answer字段的响应字典
    """
    try:
        # 使用千问LLM作为默认LLM
        qwen_llm = get_qwen_llm()
        response_text = qwen_llm._call([HumanMessage(content=prompt)])
        
        return {"answer": response_text}
        
    except Exception as e:
        logging.error(f"❌ 千问LLM调用失败: {e}")
        # 如果千问失败，尝试使用DeepSeek作为备用
        try:
            deepseek_llm = get_deepseek_llm()
            response_text = deepseek_llm._call([HumanMessage(content=prompt)])
            logging.info(f"✅ DeepSeek备用LLM调用成功，生成长度: {len(response_text)}")
            return {"answer": response_text}
        except Exception as backup_e:
            logging.error(f"❌ 备用DeepSeek LLM也失败: {backup_e}")
            return {"answer": "抱歉，我现在无法生成回复，请稍后再试。"}

def chat_with_qwen_llm(prompt: str) -> Dict[str, Any]:
    """
    千问LLM调用接口
    
    参数：
        prompt (str): 完整的提示词
    
    返回：
        Dict[str, Any]: 包含answer字段的响应字典
    """
    try:
        qwen_llm = get_qwen_llm()
        response_text = qwen_llm._call([HumanMessage(content=prompt)])
        
        return {"answer": response_text}
        
    except Exception as e:
        logging.error(f"❌ 千问LLM调用失败: {e}")
        return {"answer": "抱歉，我现在无法生成回复，请稍后再试。"}

def chat_with_deepseek_llm(prompt: str) -> Dict[str, Any]:
    """
    DeepSeek LLM调用接口
    
    参数：
        prompt (str): 完整的提示词
    
    返回：
        Dict[str, Any]: 包含answer字段的响应字典
    """
    try:
        deepseek_llm = get_deepseek_llm()
        response_text = deepseek_llm._call([HumanMessage(content=prompt)])
        
        return {"answer": response_text}
        
    except Exception as e:
        logging.error(f"❌ DeepSeek LLM调用失败: {e}")
        return {"answer": "抱歉，我现在无法生成回复，请稍后再试。"} 