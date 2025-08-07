#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from bs4 import BeautifulSoup
from typing import Dict, Any

def process_journal_content(content: str) -> Dict[str, Any]:
    """
    处理前端发送的HTML内容，生成正确的数据格式
    
    参数：
        content (str): 前端发送的HTML内容
    
    返回：
        Dict[str, Any]: 处理后的数据格式
    """
    # 1. 验证HTML格式
    validation = validate_html_format(content)
    
    # 2. 修复HTML格式（如果有游离的CSS）
    if validation['has_loose_css']:
        content = fix_html_format(content)
    
    # 3. 提取纯文本
    plain_text = extract_plain_text(content)
    
    # 4. 返回处理后的数据
    return {
        'content': content,  # 原始HTML
        'content_html': content,  # 修复后的HTML
        'content_plain': plain_text,  # 纯文本
        'content_format': 'html',
        'is_safe': True
    }

def validate_html_format(html_content: str) -> Dict[str, bool]:
    """
    验证HTML格式是否正确
    
    参数：
        html_content (str): HTML内容
    
    返回：
        Dict[str, bool]: 验证结果
    """
    # 检查是否包含完整的HTML结构
    has_doctype = re.search(r'<!DOCTYPE html>', html_content, re.IGNORECASE)
    has_html = re.search(r'<html[^>]*>', html_content, re.IGNORECASE)
    has_head = re.search(r'<head[^>]*>', html_content, re.IGNORECASE)
    has_body = re.search(r'<body[^>]*>', html_content, re.IGNORECASE)
    
    # 检查CSS是否在style标签内
    style_pattern = r'<style[^>]*>.*?</style>'
    has_style_tag = re.search(style_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    # 检查是否有游离的CSS代码
    loose_css_pattern = r'\.text-center\s*\{[^}]*\}\s*\.text-left\s*\{[^}]*\}\s*\.text-right\s*\{[^}]*\}'
    has_loose_css = re.search(loose_css_pattern, html_content)
    
    return {
        'is_valid_html': bool(has_doctype and has_html and has_head and has_body),
        'has_style_tag': bool(has_style_tag),
        'has_loose_css': bool(has_loose_css)
    }

def fix_html_format(html_content: str) -> str:
    """
    修复HTML格式，将游离的CSS移动到style标签内
    
    参数：
        html_content (str): 原始HTML内容
    
    返回：
        str: 修复后的HTML内容
    """
    # 查找游离的CSS代码
    loose_css_pattern = r'\.text-center\s*\{[^}]*\}\s*\.text-left\s*\{[^}]*\}\s*\.text-right\s*\{[^}]*\}'
    loose_css_match = re.search(loose_css_pattern, html_content)
    
    if loose_css_match:
        loose_css = loose_css_match.group()
        
        # 从HTML中移除游离的CSS
        html_content = re.sub(loose_css_pattern, '', html_content)
        
        # 将CSS添加到style标签内
        style_pattern = r'(<style[^>]*>)(.*?)(</style>)'
        style_match = re.search(style_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if style_match:
            # 在现有style标签内添加CSS
            new_style_content = style_match.group(2) + '\n        ' + loose_css
            html_content = re.sub(style_pattern, r'\1' + new_style_content + r'\3', html_content, flags=re.DOTALL | re.IGNORECASE)
        else:
            # 创建新的style标签
            new_style = f'<style>\n        {loose_css}\n    </style>'
            html_content = re.sub(r'(</head>)', f'    {new_style}\n\\1', html_content)
    
    return html_content

def extract_plain_text(html_content: str) -> str:
    """
    从HTML中提取纯文本内容
    
    参数：
        html_content (str): HTML内容
    
    返回：
        str: 纯文本内容
    """
    # 方法1：使用BeautifulSoup（推荐）
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        plain_text = soup.get_text()
        # 清理多余空白字符
        plain_text = ' '.join(plain_text.split())
        return plain_text
    except Exception as e:
        print(f"BeautifulSoup提取失败: {e}")
        # 方法2：使用正则表达式（备用）
        # 移除所有HTML标签
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        # 移除HTML实体
        plain_text = re.sub(r'&lt;', '<', plain_text)
        plain_text = re.sub(r'&gt;', '>', plain_text)
        plain_text = re.sub(r'&amp;', '&', plain_text)
        # 清理多余空白字符
        plain_text = ' '.join(plain_text.split())
        return plain_text

def handle_journal_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理日记创建/更新请求
    
    参数：
        request_data (Dict[str, Any]): 请求数据
    
    返回：
        Dict[str, Any]: 处理后的数据
    """
    title = request_data.get('title', '')
    content = request_data.get('content', '')
    emotion = request_data.get('emotion', 'peaceful')
    
    # 处理内容
    processed_content = process_journal_content(content)
    
    # 返回给前端的数据格式
    return {
        'title': title,
        'content': processed_content['content'],
        'content_html': processed_content['content_html'],
        'content_plain': processed_content['content_plain'],
        'content_format': processed_content['content_format'],
        'is_safe': processed_content['is_safe'],
        'emotion': emotion
    } 