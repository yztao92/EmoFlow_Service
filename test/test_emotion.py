#!/usr/bin/env python3
# File: test/test_emotion.py
# 功能：情绪检测模块测试
# 实现：测试情绪检测功能的各种场景

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.emotion_detector import detect_emotion  # 导入情绪检测函数

def test_emotion_detection():
    """
    测试情绪检测功能
    
    功能：
        测试不同输入文本的情绪检测结果
        验证关键词匹配和LLM fallback机制
    
    测试用例：
        - 开心情绪：包含"开心"、"高兴"等关键词
        - 悲伤情绪：包含"难过"、"伤心"等关键词
        - 愤怒情绪：包含"生气"、"愤怒"等关键词
        - 疲惫情绪：包含"累"、"疲惫"等关键词
        - 中性情绪：不包含明显情绪关键词的文本
    """
    
    # 测试用例列表：每个元组包含(输入文本, 期望情绪)
    test_cases = [
        # 开心情绪测试
        ("我今天很开心", "happy"),
        ("今天心情不错，感觉很轻松", "happy"),
        ("哈哈，太棒了", "happy"),
        ("放假了，美滋滋", "happy"),
        
        # 悲伤情绪测试
        ("我很难过", "sad"),
        ("今天心情很差", "sad"),
        ("感觉很失落", "sad"),
        ("想哭", "sad"),
        
        # 愤怒情绪测试
        ("我很生气", "angry"),
        ("气死我了", "angry"),
        ("太让人愤怒了", "angry"),
        ("火大", "angry"),
        
        # 疲惫情绪测试
        ("我好累", "tired"),
        ("感觉很疲惫", "tired"),
        ("没力气了", "tired"),
        ("压力很大", "tired"),
        
        # 中性情绪测试（可能触发LLM fallback）
        ("今天天气不错", "neutral"),
        ("我想吃饭", "neutral"),
        ("这个项目很有趣", "neutral"),
    ]
    
    print("🧪 开始情绪检测测试...")
    print("=" * 50)
    
    # 执行测试用例
    for i, (input_text, expected_emotion) in enumerate(test_cases, 1):
        # 调用情绪检测函数
        detected_emotion = detect_emotion(input_text)
        
        # 判断测试结果
        result = "✅ PASS" if detected_emotion == expected_emotion else "❌ FAIL"
        
        # 输出测试结果
        print(f"测试 {i}: {result}")
        print(f"  输入: {input_text}")
        print(f"  期望: {expected_emotion}")
        print(f"  实际: {detected_emotion}")
        print("-" * 30)
    
    print("=" * 50)
    print("🎯 情绪检测测试完成")

if __name__ == "__main__":
    """
    主函数：执行情绪检测测试
    
    说明：
        当直接运行此文件时，执行test_emotion_detection函数
        用于验证情绪检测功能的正确性
    """
    test_emotion_detection() 