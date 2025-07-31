# File: llm/deepseek_wrapper.py
# 功能：DeepSeek LLM API包装器
# 实现：封装DeepSeek Chat API调用，提供统一的LLM接口

import os  # 操作系统接口，用于环境变量
import requests  # HTTP请求库
import json  # JSON处理
from typing import List, Dict, Any  # 类型提示
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage  # LangChain消息类型
import logging  # 日志记录

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekLLM:
    """
    DeepSeek LLM API包装器类
    功能：封装DeepSeek Chat API调用，提供统一的LLM接口
    
    主要方法：
        - _call: 调用DeepSeek API生成回复
        - _format_messages: 格式化消息为API格式
        - _make_request: 发送HTTP请求到DeepSeek API
    """
    
    def __init__(self):
        """
        初始化DeepSeek LLM包装器
        从环境变量获取API密钥和配置
        """
        # 从环境变量获取DeepSeek API密钥
        # 参数来源：.env文件或系统环境变量
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        
        # DeepSeek API配置
        self.api_url = "https://api.deepseek.com/v1/chat/completions"  # API端点
        self.model = "deepseek-chat"  # 使用的模型名称
        self.max_tokens = 2000  # 最大生成token数
        self.temperature = 0.7  # 生成温度（控制随机性）

    def _call(self, messages: List[BaseMessage]) -> str:
        """
        调用DeepSeek API生成回复
        
        参数：
            messages (List[BaseMessage]): LangChain消息列表
            参数来源：rag/rag_chain.py中的chat_with_llm函数调用
        
        返回：
            str: 生成的回复文本
        
        异常：
            Exception: API调用失败时抛出异常
        """
        try:
            # 格式化消息为DeepSeek API格式
            formatted_messages = self._format_messages(messages)
            
            # 发送请求到DeepSeek API
            response = self._make_request(formatted_messages)
            
            # 提取回复内容
            if response and "choices" in response:
                return response["choices"][0]["message"]["content"]
            else:
                logger.error(f"❌ DeepSeek API 响应格式异常: {response}")
                return "抱歉，生成回复时出现错误。"
                
        except Exception as e:
            logger.error(f"❌ DeepSeek API 调用失败: {e}")
            return "抱歉，生成回复时出现错误。"

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        将LangChain消息格式化为DeepSeek API格式
        
        参数：
            messages (List[BaseMessage]): LangChain消息列表
            参数来源：_call方法的输入参数
        
        返回：
            List[Dict[str, str]]: DeepSeek API格式的消息列表
        
        格式转换：
            - SystemMessage → {"role": "system", "content": "..."}
            - HumanMessage → {"role": "user", "content": "..."}
            - AIMessage → {"role": "assistant", "content": "..."}
        """
        formatted_messages = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                formatted_messages.append({
                    "role": "system",
                    "content": message.content
                })
            elif isinstance(message, HumanMessage):
                formatted_messages.append({
                    "role": "user", 
                    "content": message.content
                })
            else:
                # 其他类型的消息（如AIMessage）转换为assistant角色
                formatted_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
        
        return formatted_messages

    def _make_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        发送HTTP请求到DeepSeek API
        
        参数：
            messages (List[Dict[str, str]]): 格式化的消息列表
            参数来源：_format_messages方法的输出
        
        返回：
            Dict[str, Any]: API响应的JSON数据
        
        异常：
            requests.RequestException: 网络请求失败时抛出异常
            json.JSONDecodeError: JSON解析失败时抛出异常
        """
        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"  # Bearer token认证
        }
        
        # 构造请求体
        payload = {
            "model": self.model,  # 使用的模型
            "messages": messages,  # 消息列表
            "max_tokens": self.max_tokens,  # 最大生成token数
            "temperature": self.temperature,  # 生成温度
            "stream": False  # 禁用流式响应
        }
        
        try:
            # 发送POST请求
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30  # 30秒超时
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            # 解析JSON响应
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"❌ DeepSeek API 请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ DeepSeek API 响应解析失败: {e}")
            raise