# File: dialogue/state_tracker.py

from typing import Any, Dict, List, Tuple

class StateTracker:
    def __init__(self):
        # 会话全局状态
        self.state: Dict[str, Any] = {
            "current_emotion": None,
            "technique_stack": [],     # 已使用的干预技术列表
            "technique_results": [],   # 干预技术成效记录
            "user_values": []          # 用户提到的核心价值观
        }
        # 记录完整的对话历史，元素为 (role, content)
        self.history: List[Tuple[str, str]] = []

    def update_emotion(self, emotion: str):
        """
        更新当前情绪
        """
        self.state["current_emotion"] = emotion

    def record_technique(self, technique: str, success: bool):
        """
        记录一次干预技术的使用及其成效。
        """
        if technique:
            self.state["technique_stack"].append(technique)
            self.state["technique_results"].append(success)

    def add_user_values(self, values: List[str]):
        """
        将用户在对话中提到的价值观加到列表里，避免重复。
        """
        for v in values:
            if v not in self.state["user_values"]:
                self.state["user_values"].append(v)

    def should_switch_technique(self, window: int = 3) -> bool:
        """
        如果最近 window 次技术使用都标记为失败，就返回 True。
        """
        results = self.state["technique_results"][-window:]
        return len(results) == window and all(r is False for r in results)

    def update_message(self, role: str, content: str):
        """
        在对话状态中添加新消息，role 为 'user' 或 'assistant'.
        """
        self.history.append((role, content))

    def summary(self, last_n: int = 3) -> str:
        """
        用于 Prompt 注入：输出最近对话历史和当前状态。
        如果轮次不超过10轮，全部传入；否则只传最近last_n轮。
        """
        lines: List[str] = []
        total_rounds = len(self.history) // 2
        if total_rounds <= 10:
            # 全量传入
            for role, content in self.history:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        else:
            # 只传最近last_n轮
            for role, content in self.history[-2 * last_n:]:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        # 状态信息
        lines.append(f"当前情绪：{self.state['current_emotion']}")
        techs = self.state["technique_stack"][-last_n:]
        vals  = self.state["user_values"]
        lines.append(f"最近使用技术：{techs}")
        lines.append(f"用户价值观：{vals}")
        # 添加统一头标识
        return "【对话历史及状态】\n" + "\n".join(lines)
