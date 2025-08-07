# File: dialogue/state_tracker.py
# 功能：对话状态跟踪器，管理用户会话状态和对话历史

from typing import List, Tuple

class StateTracker:
    """
    对话状态跟踪器类
    功能：管理单个用户会话的状态信息，包括对话历史
    
    状态组成：
        - history: 对话历史记录
    """
    
    def __init__(self):
        """
        初始化状态跟踪器
        创建空的对话历史列表
        """
        # 对话历史：存储所有对话消息，格式为 (role, content)
        self.history: List[Tuple[str, str]] = []

    def update_message(self, role: str, content: str):
        """
        更新对话历史
        
        参数：
            role (str): 消息角色（user/assistant）
            参数来源：main.py中的消息处理
            content (str): 消息内容
            参数来源：用户输入或AI回复
        """
        self.history.append((role, content))

    def get_round_count(self) -> int:
        """
        获取当前对话轮次
        
        返回：
            int: 当前对话轮次（用户消息数量）
        """
        return len([r for r, _ in self.history if r == "user"])

    def summary(self, last_n: int = 3) -> str:
        """
        生成对话状态摘要
        
        参数：
            last_n (int): 最近n轮对话，默认3
            参数来源：main.py中调用时传入的参数
        
        返回：
            str: 格式化的状态摘要文本
        
        摘要内容：
            - 对话历史（最近n轮）
        """
        lines: List[str] = []
        
        # 显示最近n轮对话
        for role, content in self.history[-2 * last_n:]:
            speaker = "用户" if role == "user" else "AI"
            lines.append(f"• {speaker}: {content}")
        
        return "【对话历史】\n" + "\n".join(lines)

    def get_recent_user_query(self, last_n: int = 1) -> str:
        """
        获取最近n次用户查询
        
        参数：
            last_n (int): 获取最近n次查询，默认1
            参数来源：调用方传入的参数
        
        返回：
            str: 最近n次用户查询的合并文本
        """
        return "，".join([c for r, c in self.history if r == "user"][-last_n:])