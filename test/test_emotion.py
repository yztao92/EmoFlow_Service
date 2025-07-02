#!/usr/bin/env python3
# File: test/test_emotion.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.emotion_detector import detect_emotion

def test_emotion_detection():
    """测试情绪检测功能"""
    
    test_cases = [
        ("我好生气啊", "angry"),
        ("我真的很愤怒", "angry"),
        ("我好难过", "sad"),
        ("我很伤心", "sad"),
        ("我很开心", "happy"),
        ("我很快乐", "happy"),
        ("我好累", "tired"),
        ("我很疲惫", "tired"),
        ("今天天气不错", "neutral"),
        ("你好", "neutral"),
    ]
    
    print("🧪 测试情绪检测功能")
    print("=" * 40)
    
    success_count = 0
    total_count = len(test_cases)
    
    for text, expected in test_cases:
        result = detect_emotion(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' -> {result} (期望: {expected})")
        
        if result == expected:
            success_count += 1
    
    print("=" * 40)
    print(f"测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，需要检查")

if __name__ == "__main__":
    test_emotion_detection() 