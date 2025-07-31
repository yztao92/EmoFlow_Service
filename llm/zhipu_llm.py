# File: llm/zhipu_llm.py
# 功能：智谱AI LLM API调用封装
# 实现：封装智谱AI GLM-4模型调用，主要用于日记生成

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

def zhipu_chat_llm(prompt: str) -> dict:
    """
    调用智谱AI GLM-4模型生成回复
    
    参数：
        prompt (str): 输入给LLM的提示词
        参数来源：日记生成或其他需要LLM回复的场景
    
    返回：
        dict: 包含生成回复的字典，格式 {"answer": "生成的回复"}
    
    异常：
        ValueError: API调用失败时抛出异常
        Exception: 其他异常情况
    
    说明：
        此函数主要用于日记生成功能，使用智谱AI的GLM-4模型
        相比DeepSeek，智谱AI在中文理解和生成方面有优势
    """
    # 构造请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"  # Bearer token认证
    }

    # 构造请求体
    payload = {
        "model": "glm-4",  # 使用智谱AI的GLM-4模型
        "messages": [
            {"role": "system", "content": "你是一个善解人意的情绪日记助手。"},  # 系统角色定义
            {"role": "user", "content": prompt}  # 用户输入
        ]
    }

    try:
        # 发送POST请求到智谱AI API
        response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)
        
        # 调试信息：打印状态码和返回内容
        print("🧠 Zhipu LLM 状态码:", response.status_code)
        print("🧠 Zhipu LLM 返回内容:", response.text)

        # 检查HTTP状态码
        if response.status_code == 200:
            # 解析JSON响应
            data = response.json()
            return {
                "answer": data["choices"][0]["message"]["content"].strip()  # 提取并清理回复内容
            }
        else:
            # API调用失败，抛出异常
            raise ValueError(f"调用失败: {response.status_code} - {response.text}")

    except Exception as e:
        # 记录错误信息
        print("[❌ ERROR] LLM 日记生成失败:", e)
        return {
            "answer": "生成失败"  # 返回错误提示
        }