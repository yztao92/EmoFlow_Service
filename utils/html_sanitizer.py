# File: utils/html_sanitizer.py
# 功能：HTML安全处理工具
# 实现：HTML净化、纯文本提取、安全验证

import re
import html
from typing import Tuple, Optional

# ==================== HTML安全处理 ====================

# 允许的HTML标签
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code',
    'div', 'span', 'pre'
]

# 允许的属性
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    'p': ['class'],
    'div': ['class'],
    'span': ['class']
}

# 危险的HTML标签
DANGEROUS_TAGS = [
    'script', 'iframe', 'object', 'embed', 'form',
    'input', 'textarea', 'select', 'option',
    'style', 'link', 'meta', 'base'
]

def sanitize_html(html_content: str) -> str:
    """
    净化HTML内容
    
    Args:
        html_content: 原始HTML内容
        
    Returns:
        净化后的HTML内容
    """
    if not html_content:
        return ""
    
    # 1. 移除危险的HTML标签
    for tag in DANGEROUS_TAGS:
        # 移除开始标签
        html_content = re.sub(f'<{tag}[^>]*>', '', html_content, flags=re.IGNORECASE)
        # 移除结束标签
        html_content = re.sub(f'</{tag}>', '', html_content, flags=re.IGNORECASE)
        # 移除自闭合标签
        html_content = re.sub(f'<{tag}[^>]*/>', '', html_content, flags=re.IGNORECASE)
    
    # 2. 移除JavaScript事件处理器
    html_content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
    
    # 3. 移除javascript:协议
    html_content = re.sub(r'javascript:', '', html_content, flags=re.IGNORECASE)
    
    # 4. 移除data:协议（可能包含恶意内容）
    html_content = re.sub(r'data:', '', html_content, flags=re.IGNORECASE)
    
    # 5. 移除外部链接（可选，根据需求调整）
    # html_content = re.sub(r'<a[^>]*href\s*=\s*["\'](?!https?://)[^"\']*["\'][^>]*>', '', html_content)
    
    # 6. 清理多余的空白字符
    html_content = re.sub(r'\s+', ' ', html_content)
    html_content = html_content.strip()
    
    return html_content

def html_to_text(html_content: str) -> str:
    """
    从HTML中提取纯文本
    
    Args:
        html_content: HTML内容
        
    Returns:
        纯文本内容
    """
    if not html_content:
        return ""
    
    # 1. 移除HTML标签
    text = re.sub(r'<[^>]+>', '', html_content)
    
    # 2. 解码HTML实体
    text = html.unescape(text)
    
    # 3. 清理多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def validate_html_content(html_content: str) -> Tuple[bool, Optional[str]]:
    """
    验证HTML内容的安全性
    
    Args:
        html_content: HTML内容
        
    Returns:
        (是否安全, 错误信息)
    """
    if not html_content:
        return True, None
    
    # 检查危险标签
    for tag in DANGEROUS_TAGS:
        if f'<{tag}' in html_content.lower():
            return False, f"不允许的HTML标签: {tag}"
    
    # 检查JavaScript事件
    if re.search(r'on\w+\s*=', html_content, re.IGNORECASE):
        return False, "不允许的JavaScript事件处理器"
    
    # 检查javascript:协议
    if 'javascript:' in html_content.lower():
        return False, "不允许的javascript:协议"
    
    return True, None

def process_content(raw_content: str, content_format: str = 'html') -> Tuple[str, str, bool]:
    """
    处理内容，返回净化后的HTML和纯文本
    
    Args:
        raw_content: 原始内容
        content_format: 内容格式
        
    Returns:
        (净化后的HTML, 纯文本, 是否安全)
    """
    if content_format == 'html':
        # HTML格式处理
        clean_html = sanitize_html(raw_content)
        plain_text = html_to_text(clean_html)
        is_safe, error_msg = validate_html_content(clean_html)
        
        if not is_safe:
            # 如果不安全，降级为纯文本
            clean_html = f"<p>{html.escape(plain_text)}</p>"
            is_safe = True
        
        return clean_html, plain_text, is_safe
    
    elif content_format == 'plain':
        # 纯文本格式
        plain_text = raw_content.strip()
        clean_html = f"<p>{html.escape(plain_text)}</p>"
        return clean_html, plain_text, True
    
    else:
        # 默认按HTML处理
        return process_content(raw_content, 'html') 