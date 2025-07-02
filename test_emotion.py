#!/usr/bin/env python3

from llm.emotion_detector import emotion_classifier, detect_emotion

# 测试文本
test_text = "我好无语啊"

print("=== 测试 emotion_classifier 返回格式 ===")
result = emotion_classifier(test_text)
print(f"原始结果: {result}")
print(f"结果类型: {type(result)}")
print(f"结果长度: {len(result)}")

if len(result) > 0:
    print(f"第一个元素: {result[0]}")
    print(f"第一个元素类型: {type(result[0])}")

print("\n=== 测试 detect_emotion 函数 ===")
try:
    emotion = detect_emotion(test_text)
    print(f"检测到的情绪: {emotion}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc() 