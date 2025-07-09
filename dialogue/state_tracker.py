# File: dialogue/state_tracker.py

from typing import Any, Dict, List, Tuple, Callable, Optional

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

    def generate_brief_summary(
        self,
        llm: Optional[Callable[[str], str]] = None,
        last_n: int = 3
    ) -> str:
        """
        用 LLM 生成一句“主线摘要”，用于RAG检索。
        llm: 接收prompt字符串并返回回答的可调用对象（如 call_llm_api）
        last_n: 最近n轮对话（user+AI为一轮）
        """
        # 只取最近 last_n 轮（即最近 2*last_n 条）
        history_slice = self.history[-2 * last_n:]
        history_text = "\n".join([f"{'用户' if r == 'user' else 'AI'}: {c}" for r, c in history_slice])
        prompt = (
            "你是对话摘要助手。请根据以下多轮对话，"
            "用一句自然语言准确概括此刻用户的主要困扰或需求：\n"
            f"{history_text}\n"
            "输出示例：用户最近睡眠浅，经常夜醒，想听睡前放松的方法。"
        )
        if llm is not None:
            try:
                result = llm(prompt).strip()
                # 防止空返回
                if result:
                    return result
            except Exception as e:
                print(f"[StateTracker] LLM摘要失败: {e}")
        # 如果没给llm或llm失败，则兜底：直接拼接最近用户消息
        fallback = "，".join([c for r, c in history_slice if r == "user"])
        return fallback if fallback else (self.history[-1][1] if self.history else "")