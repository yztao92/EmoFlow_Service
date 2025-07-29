# File: dialogue/state_tracker.py
# 功能：对话状态跟踪器，管理用户会话状态和对话历史
# 实现：维护对话历史、情绪状态、技术栈等会话信息

from typing import Any, Dict, List, Tuple  # 类型提示

class StateTracker:
    """
    对话状态跟踪器类
    功能：管理单个用户会话的状态信息，包括对话历史、情绪、技术栈等
    
    状态组成：
        - current_emotion: 当前情绪状态
        - technique_stack: 使用的技术栈历史
        - technique_results: 技术使用结果
        - user_values: 用户价值观
        - history: 对话历史记录
    """
    
    def __init__(self):
        """
        初始化状态跟踪器
        创建空的状态字典和对话历史列表
        """
        # 状态字典：存储各种会话状态信息
        self.state: Dict[str, Any] = {
            "current_emotion": None,  # 当前情绪状态
            "technique_stack": [],  # 使用的技术栈历史
            "technique_results": [],  # 技术使用结果（成功/失败）
            "user_values": []  # 用户价值观列表
        }
        # 对话历史：存储所有对话消息，格式为 (role, content)
        self.history: List[Tuple[str, str]] = []

    def update_emotion(self, emotion: str):
        """
        更新当前情绪状态
        
        参数：
            emotion (str): 新的情绪标签
            参数来源：llm/emotion_detector.py 中 detect_emotion() 函数返回的情绪
        """
        self.state["current_emotion"] = emotion

    def record_technique(self, technique: str, success: bool):
        """
        记录使用的技术和结果
        
        参数：
            technique (str): 使用的技术名称
            参数来源：对话过程中AI使用的心理技术
            success (bool): 技术使用是否成功
            参数来源：用户反馈或AI判断
        """
        if technique:
            self.state["technique_stack"].append(technique)  # 添加到技术栈
            self.state["technique_results"].append(success)  # 记录结果

    def add_user_values(self, values: List[str]):
        """
        添加用户价值观
        
        参数：
            values (List[str]): 价值观列表
            参数来源：从对话中提取的用户价值观
        """
        for v in values:
            if v not in self.state["user_values"]:
                self.state["user_values"].append(v)  # 避免重复添加

    def should_switch_technique(self, window: int = 3) -> bool:
        """
        判断是否应该切换技术
        当连续多次技术使用失败时，建议切换技术
        
        参数：
            window (int): 检查窗口大小，默认3
            参数来源：调用方传入的配置参数
        
        返回：
            bool: 是否应该切换技术
        """
        results = self.state["technique_results"][-window:]  # 获取最近window次结果
        return len(results) == window and all(r is False for r in results)  # 连续失败则切换

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

    def summary(self, last_n: int = 3) -> str:
        """
        生成对话状态摘要
        
        参数：
            last_n (int): 最近n轮对话，默认3
            参数来源：main.py中调用时传入的参数
        
        返回：
            str: 格式化的状态摘要文本
        
        摘要内容：
            - 对话历史（全量或最近n轮）
            - 当前情绪状态
            - 最近使用的技术
            - 用户价值观
        """
        lines: List[str] = []
        total_rounds = len(self.history) // 2  # 计算总对话轮次
        
        # 根据对话轮次决定显示策略
        if total_rounds <= 100:  # 如果对话轮次较少，显示全部历史
            for role, content in self.history:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        else:  # 如果对话轮次较多，只显示最近n轮
            for role, content in self.history[-2 * last_n:]:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        
        # 添加状态信息
        lines.append(f"当前情绪：{self.state['current_emotion']}")
        lines.append(f"最近使用技术：{self.state['technique_stack'][-last_n:]}")
        lines.append(f"用户价值观：{self.state['user_values']}")
        
        return "【对话历史及状态】\n" + "\n".join(lines)

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