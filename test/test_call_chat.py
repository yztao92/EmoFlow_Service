# File: test/test_call_chat.py
# 功能：聊天接口测试
# 实现：测试FastAPI聊天接口的调用

import requests  # HTTP请求库
import json  # JSON处理

def test_chat_endpoint():
    """
    测试聊天接口
    
    功能：
        向FastAPI的/chat接口发送POST请求
        验证聊天功能的正常工作
    
    请求参数：
        - session_id: 会话ID，用于标识对话会话
        - messages: 消息列表，包含对话历史
        - emotion: 情绪标签（可选）
    
    返回：
        包含AI回复的JSON响应
    """
    
    # 测试数据：模拟用户聊天请求
    test_data = {
        "session_id": "test_session_001",  # 测试会话ID
        "messages": [
            {
                "role": "user",  # 用户角色
                "content": "我今天心情不太好"  # 用户输入
            }
        ],
        "emotion": "sad"  # 情绪标签（可选）
    }
    
    # API端点URL
    url = "http://localhost:8000/chat"  # 本地FastAPI服务器地址
    
    try:
        # 发送POST请求到聊天接口
        response = requests.post(
            url,
            json=test_data,  # 将测试数据作为JSON发送
            headers={"Content-Type": "application/json"}  # 设置请求头
        )
        
        # 检查HTTP状态码
        if response.status_code == 200:
            # 解析响应JSON
            result = response.json()
            print("✅ 聊天接口测试成功")
            print(f"AI回复: {result.get('response', {}).get('answer', '无回复')}")
        else:
            print(f"❌ 聊天接口测试失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：请确保FastAPI服务器正在运行")
        print("💡 启动命令: python main.py")
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")

if __name__ == "__main__":
    """
    主函数：执行聊天接口测试
    
    说明：
        当直接运行此文件时，执行test_chat_endpoint函数
        用于验证聊天接口的功能
    """
    test_chat_endpoint() 