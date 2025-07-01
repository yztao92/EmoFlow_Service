# dialogue/state_tracker.py

from typing import Any, Dict, List

class StateTracker:
    def __init__(self):
        self.state: Dict[str, Any] = {
            "current_emotion": None,
            "technique_stack": [],     # 已使用的干预技术列表
            "technique_results": [],   # 干预技术的成效记录，比如 [True, False, False]
            "user_values": []          # 用户提到的核心价值观
        }
    
    def update_emotion(self, emotion: str):
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
        如果最近 window 次技术中，都标记为失败，就返回 True。
        """
        results = self.state["technique_results"][-window:]
        return len(results) == window and all(r is False for r in results)

    def summary(self, last_n: int = 3) -> str:
        """
        用于 Prompt 注入：简要输出最近情绪、用过的技术、用户价值观
        """
        techs = self.state["technique_stack"][-last_n:]
        vals  = self.state["user_values"]
        return (
            f"当前情绪：{self.state['current_emotion']}\n"
            f"最近使用技术：{techs}\n"
            f"用户价值观：{vals}"
        )