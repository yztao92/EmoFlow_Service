# File: llm/qwen_vl_analyzer.py
# 功能：qwen-vl-plus图片分析服务
# 实现：使用qwen-vl-plus模型分析图片内容，生成文字描述

import os
import json
import logging
from typing import Dict, Any, Optional
from PIL import Image
import io
import base64
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class QwenVLAnalyzer:
    """
    qwen-vl-plus图片分析器
    功能：分析图片内容，生成详细的文字描述
    """
    
    def __init__(self):
        self.api_key = os.getenv("QIANWEN_API_KEY")
        if not self.api_key:
            raise ValueError("缺少QIANWEN_API_KEY环境变量")
        
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        self.model_name = "qwen-vl-plus"
    
    def analyze_image(self, image_data: bytes, user_message: str = "") -> Dict[str, Any]:
        """
        分析图片内容
        :param image_data: 图片数据（字节）
        :param user_message: 用户消息（可选）
        :return: 分析结果字典
        """
        try:
            # 将图片转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 构造分析提示词
            prompt = self._build_analysis_prompt(user_message)
            
            # 调用qwen-vl-plus API
            analysis_result = self._call_qwen_vl_api(image_base64, prompt)
            
            # 解析分析结果
            parsed_result = self._parse_analysis_result(analysis_result)
            
            logger.info(f"✅ 图片分析完成: {parsed_result.get('summary', '')[:50]}...")
            return parsed_result
            
        except Exception as e:
            logger.error(f"❌ 图片分析失败: {e}")
            return {
                "summary": "图片分析失败，无法识别内容",
                "emotion": "未知",
                "objects": [],
                "scene": "未知",
                "mood": "未知",
                "error": str(e)
            }
    
    def _build_analysis_prompt(self, user_message: str = "") -> str:
        """
        构造图片分析提示词
        """
        base_prompt = """
请详细分析这张图片，并提供以下信息：

1. 图片内容描述（详细描述，包含：主体对象、背景环境、光线条件、色彩搭配等，150字左右）
2. 主要情绪（开心、悲伤、愤怒、焦虑、平静、兴奋等）
3. 主要对象（人物、物品、场景等）
4. 场景类型（室内、室外、自然、城市等）
5. 整体氛围（温馨、紧张、轻松、严肃等）

请以JSON格式返回结果：
{
    "summary": "图片内容描述",
    "emotion": "主要情绪",
    "objects": ["对象1", "对象2"],
    "scene": "场景类型",
    "mood": "整体氛围"
}
"""
        
        if user_message:
            base_prompt += f"\n\n用户说：{user_message}\n请结合用户的描述来分析图片。"
        
        return base_prompt
    
    def _call_qwen_vl_api(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """
        调用qwen-vl-plus API
        根据阿里云百炼API文档：https://bailian.console.aliyun.com/
        """
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 根据阿里云百炼API文档修正请求格式
        data = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "image": f"data:image/jpeg;base64,{image_base64}"
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
        
        logger.info(f"🔍 调用qwen-vl-plus API: {self.model_name}")
        logger.debug(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers=headers,
            json=data,
            timeout=30
        )
        
        logger.info(f"API响应状态: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API调用失败: {response.status_code}, {response.text}")
            raise Exception(f"API调用失败: {response.status_code}, {response.text}")
        
        result = response.json()
        logger.debug(f"API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    
    def _parse_analysis_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析API返回结果
        """
        try:
            # 提取文本内容
            content = ""
            if "output" in api_result and "choices" in api_result["output"]:
                choices = api_result["output"]["choices"]
                if choices and len(choices) > 0:
                    message_content = choices[0].get("message", {}).get("content", "")
                    # 处理content可能是字符串或列表的情况
                    if isinstance(message_content, list):
                        # 如果是列表，提取文本部分
                        content = " ".join([item.get("text", "") for item in message_content if isinstance(item, dict) and "text" in item])
                    else:
                        content = str(message_content)
            
            logger.info(f"提取到的内容: {content}")
            
            # 清理内容，移除markdown代码块标记
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]  # 移除 ```json
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]  # 移除 ```
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]  # 移除结尾的 ```
            cleaned_content = cleaned_content.strip()
            
            # 尝试解析JSON
            try:
                parsed = json.loads(cleaned_content)
                return {
                    "summary": parsed.get("summary", "无法识别图片内容"),
                    "emotion": parsed.get("emotion", "未知"),
                    "objects": parsed.get("objects", []),
                    "scene": parsed.get("scene", "未知"),
                    "mood": parsed.get("mood", "未知"),
                    "raw_content": content
                }
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接使用原始内容
                return {
                    "summary": cleaned_content or "无法识别图片内容",
                    "emotion": "未知",
                    "objects": [],
                    "scene": "未知",
                    "mood": "未知",
                    "raw_content": content
                }
                
        except Exception as e:
            logger.error(f"解析分析结果失败: {e}")
            return {
                "summary": "图片分析失败",
                "emotion": "未知",
                "objects": [],
                "scene": "未知",
                "mood": "未知",
                "error": str(e)
            }

# 全局分析器实例
qwen_vl_analyzer = QwenVLAnalyzer()
