#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日记生成prompt管理
根据用户情绪状态生成个性化的日记生成策略
"""

def get_journal_generation_prompt(emotion: str, chat_history: str) -> str:
    """
    根据情绪状态获取日记生成prompt
    
    参数：
        emotion (str): 情绪状态
        chat_history (str): 对话历史
        
    返回：
        str: 日记生成prompt
    """
    # 构建结构化的prompt
    prompt = f"""# 心情日记生成任务

## 任务描述
请根据用户的对话内容，生成一篇个性化的心情日记。

## 用户情绪状态
当前情绪：{emotion}

## 写作要求"""
    
    # 根据情绪状态添加具体要求
    if emotion in ["悲伤", "不开心", "生气"]:
        prompt += """
- 承认负面情绪，但引导积极思考"""
    elif emotion == "平和":
        prompt += """
- 记录平静时光
- 体现内心的宁静和满足
- 展现生活中的美好细节
- 表达对现状的感恩"""
    elif emotion in ["开心", "幸福"]:
        prompt += """
- 放大美好感受
- 让快乐情绪更加丰富生动
- 鼓励用户珍惜和分享这份喜悦
- 记录幸福的瞬间和感受"""
    else:
        prompt += """
- 根据对话内容，生成真实、有温度的情感日记
- 体现用户的真实感受和经历
- 语言自然流畅，富有情感"""
    
    prompt += f"""


## 输出格式要求
- 尽量不要超过 100 字
- 不要在日记里面出现时间日期
- 以第一人称"我"的视角写作
- 语言自然、有情感
- 内容要真实、有温度、有代入感
- 不要提到对话或AI
- 只写个人的感受和经历
- 用纯文本格式输出，不要包含任何HTML标签

## 对话内容
{chat_history}

## 开始生成日记
请根据以上要求，生成一篇符合用户情绪状态的心情日记："""
    
    return prompt

def get_journal_title_prompt(emotion: str, journal_content: str) -> str:
    """
    根据情绪状态获取日记标题生成prompt
    
    参数：
        emotion (str): 情绪状态
        journal_content (str): 日记内容
        
    返回：
        str: 标题生成prompt
    """
    prompt = f"""# 日记标题生成任务

## 任务描述
请根据以下心情日记内容，生成一个简单的，不超过10个字的标题。

## 日记内容
{journal_content}

## 开始生成标题
请根据以上要求，生成一个合适的日记标题,不要用《》："""
    
    return prompt
