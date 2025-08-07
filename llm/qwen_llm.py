# File: llm/qwen_llm.py
# 功能：千问LLM API包装器
# 实现：封装千问Chat API调用，提供统一的LLM接口

import os
import json
import logging
import requests
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

class QwenLLM:
    """
    千问LLM API包装器类
    功能：封装千问Chat API调用，提供统一的LLM接口
    
    主要方法：
    - _call: 调用千问API生成回复
    - _make_request: 发送HTTP请求到千问API
    - _format_messages: 格式化消息为千问API格式
    """
    
    def __init__(self):
        """
        初始化千问LLM包装器
        
        配置：
        - 从环境变量获取千问API密钥
        - 设置千问API端点和模型名称
        """
        # 从环境变量获取千问API密钥
        import os
        self.api_key = os.getenv("QIANWEN_API_KEY")
        if not self.api_key:
            raise ValueError("QIANWEN_API_KEY 环境变量未设置")
        
        # 千问API配置
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen-plus"  # 使用的模型名称
        
        logger.info(f"✅ 千问LLM初始化成功: {self.model}")
    
    def _call(self, messages: List[BaseMessage]) -> str:
        """
        调用千问API生成回复
        
        参数：
            messages (List[BaseMessage]): LangChain消息列表
        
        返回：
            str: 生成的回复文本
        
        流程：
            1. 格式化消息为千问API格式
            2. 发送HTTP请求到千问API
            3. 解析响应并返回回复文本
        """
        try:
            # 格式化消息为千问API格式
            formatted_messages = self._format_messages(messages)
            
            # 发送请求到千问API
            response = self._make_request(formatted_messages)
            
            # 解析响应
            if response and "output" in response:
                reply = response["output"]["text"]
                logger.info(f"✅ 千问API调用成功，生成长度: {len(reply)}")
                return reply
            else:
                logger.error(f"❌ 千问API 响应格式异常: {response}")
                return "抱歉，我现在无法生成回复。"
                
        except Exception as e:
            logger.error(f"❌ 千问API 调用失败: {e}")
            return "抱歉，我现在无法生成回复。"
    
    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        将LangChain消息格式化为千问API格式
        
        参数：
            messages (List[BaseMessage]): LangChain消息列表
        
        返回：
            List[Dict[str, str]]: 千问API格式的消息列表
        
        格式转换：
            LangChain消息 → 千问API消息格式
        """
        formatted_messages = []
        
        for message in messages:
            if hasattr(message, 'content'):
                # 根据消息类型设置角色
                if hasattr(message, 'type') and message.type == 'human':
                    role = 'user'
                elif hasattr(message, 'type') and message.type == 'ai':
                    role = 'assistant'
                else:
                    role = 'user'  # 默认为用户消息
                
                formatted_messages.append({
                    "role": role,
                    "content": message.content
                })
        
        return formatted_messages
    
    def _make_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        发送HTTP请求到千问API
        
        参数：
            messages (List[Dict[str, str]]): 格式化的消息列表
        
        返回：
            Dict[str, Any]: API响应数据
        
        请求配置：
            - 使用POST方法
            - 包含Authorization头部
            - 发送JSON格式数据
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 修正千问API请求格式
        data = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.8
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            # 打印调试信息
            logger.info(f"🔍 千问API请求URL: {self.api_url}")
            logger.info(f"🔍 千问API请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            logger.info(f"🔍 千问API响应状态: {response.status_code}")
            logger.info(f"🔍 千问API响应内容: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ 千问API HTTP错误: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"   响应内容: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 千问API 请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ 千问API 响应解析失败: {e}")
            raise 