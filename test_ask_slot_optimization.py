#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ask_slot优化后的效果
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ask_slot_optimization():
    """
    测试ask_slot优化后的效果
    """
    from prompts.chat_prompts_generator import generate_prompt
    
    # 模拟分析结果
    analysis_result = {
        "mode": "低谷",
        "stage": "暖场",
        "context_type": "求安慰",
        "ask_slot": "gentle",  # 测试温和引导模式
        "need_empathy": True,
        "need_rag": False,
        "queries": []
    }
    
    print("=" * 60)
    print("测试 ask_slot = 'gentle' 模式（低谷情绪 + 需要共情）")
    print("=" * 60)
    
    # 生成prompt
    prompt = generate_prompt(analysis_result, [])
    print(prompt)
    
    print("\n" + "=" * 60)
    print("测试 ask_slot = 'active' 模式（低谷情绪 + 需要共情）")
    print("=" * 60)
    
    # 测试主动提问模式
    analysis_result["ask_slot"] = "active"
    prompt = generate_prompt(analysis_result, [])
    print(prompt)
    
    print("\n" + "=" * 60)
    print("测试 ask_slot = 'gentle' 模式（庆祝情绪 + 需要共情）")
    print("=" * 60)
    
    # 测试庆祝情绪下的温和引导模式
    analysis_result["mode"] = "庆祝"
    analysis_result["ask_slot"] = "gentle"
    prompt = generate_prompt(analysis_result, [])
    print(prompt)

if __name__ == "__main__":
    print("🧪 测试ask_slot优化后的效果")
    test_ask_slot_optimization()
    print("\n🎉 测试完成！")
