# File: llm/dairy_gen.py
# 功能：日记生成模块
# 实现：基于对话历史生成用户心情日记

import os  # 操作系统接口，用于环境变量
import requests  # HTTP请求库
from dotenv import load_dotenv  # 环境变量加载

# 加载环境变量
load_dotenv()

# ==================== 智谱AI配置 ====================
# 从环境变量获取智谱AI API密钥
# 参数来源：.env文件或系统环境变量
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")

# 智谱AI API端点
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def generate_diary(messages: list[str]) -> str:
    """
    基于对话历史生成用户心情日记
    
    参数：
        messages (list[str]): 对话历史列表
        参数来源：用户与AI的对话记录，包含用户输入和AI回复
    
    返回：
        str: 生成的心情日记内容
    
    异常：
        Exception: API调用失败时返回默认日记内容
    
    功能说明：
        1. 将对话历史整理成提示词
        2. 调用智谱AI GLM-4模型生成日记
        3. 以第一人称视角记录情绪体验
        4. 确保日记风格自然、真实、有情绪波动
    """
    
    # 构造日记生成提示词
    diary_prompt = (
        "你是用户的情绪助手。请将以下用户与 AI 的对话内容整理成一篇 100 字以内的心情日记，"
        "用第一人称表达情绪体验，风格自然、真实、有情绪波动。不要出现 AI 或聊天助手等字眼。\n\n"
        "对话内容如下：\n"
        + "\n".join(messages)  # 将对话历史拼接成文本
    )

    # 构造请求体
    payload = {
        "model": "glm-4",  # 使用智谱AI的GLM-4模型
        "messages": [
            {"role": "system", "content": "你是用户的情绪记录写手。"},  # 系统角色定义
            {"role": "user", "content": diary_prompt}  # 用户输入（日记生成提示词）
        ]
    }

    # 构造请求头
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",  # Bearer token认证
        "Content-Type": "application/json"  # 内容类型
    }

    try:
        # 发送POST请求到智谱AI API
        response = requests.post(
            ZHIPU_API_URL, 
            json=payload, 
            headers=headers, 
            timeout=30  # 30秒超时
        )
        
        # 解析JSON响应
        data = response.json()
        
        # 提取并返回生成的日记内容
        return data["choices"][0]["message"]["content"].strip()
        
    except Exception as e:
        # 记录错误信息
        print(f"[❌ ERROR] 日记生成失败: {e}")
        
        # 返回默认日记内容
        return "今天的心情有些复杂，暂时还没能整理好。"