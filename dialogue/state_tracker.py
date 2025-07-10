# File: dialogue/state_tracker.py

from typing import Any, Dict, List, Tuple

class StateTracker:
    def __init__(self):
        self.state: Dict[str, Any] = {
            "current_emotion": None,
            "technique_stack": [],
            "technique_results": [],
            "user_values": []
        }
        self.history: List[Tuple[str, str]] = []

    def update_emotion(self, emotion: str):
        self.state["current_emotion"] = emotion

    def record_technique(self, technique: str, success: bool):
        if technique:
            self.state["technique_stack"].append(technique)
            self.state["technique_results"].append(success)

    def add_user_values(self, values: List[str]):
        for v in values:
            if v not in self.state["user_values"]:
                self.state["user_values"].append(v)

    def should_switch_technique(self, window: int = 3) -> bool:
        results = self.state["technique_results"][-window:]
        return len(results) == window and all(r is False for r in results)

    def update_message(self, role: str, content: str):
        self.history.append((role, content))

    def summary(self, last_n: int = 3) -> str:
        lines: List[str] = []
        total_rounds = len(self.history) // 2
        if total_rounds <= 100:
            for role, content in self.history:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        else:
            for role, content in self.history[-2 * last_n:]:
                speaker = "用户" if role == "user" else "AI"
                lines.append(f"• {speaker}: {content}")
        lines.append(f"当前情绪：{self.state['current_emotion']}")
        lines.append(f"最近使用技术：{self.state['technique_stack'][-last_n:]}")
        lines.append(f"用户价值观：{self.state['user_values']}")
        return "【对话历史及状态】\n" + "\n".join(lines)

    def get_recent_user_query(self, last_n: int = 1) -> str:
        return "，".join([c for r, c in self.history if r == "user"][-last_n:])