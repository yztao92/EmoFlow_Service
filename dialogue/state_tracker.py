# File: dialogue/state_tracker.py
# 功能：对话状态跟踪器（纯存储 + 兜底阶段推断）
# 职责：仅管理对话历史与摘要；不做复杂语义分析
# 额外：提供按轮次的 stage 兜底推断（warmup/mid/wrap）

from __future__ import annotations
from typing import List, Tuple, Optional, Dict

class StateTracker:
    """
    轻量会话状态容器：
    - 保存对话历史 (role, content)
    - 提供最近若干条的摘要
    - 统计用户轮次
    - 提供按轮次的 stage 兜底推断：1-2→warmup，3-6→mid，≥7→wrap
    """

    def __init__(self, max_history: int = 10000):
        """
        初始化
        :param max_history: 最大保留的消息条数（超过则从最早开始丢弃）
        """
        self._max_history = max_history
        self.history: List[Tuple[str, str]] = []  # [(role, content)]

    # ========== 基础 API ==========

    def update_message(self, role: str, content: str) -> None:
        """
        写入一条消息
        :param role: "user" | "assistant"
        :param content: 文本内容
        """
        self.history.append((role, content))
        # 控制上限
        overflow = len(self.history) - self._max_history
        if overflow > 0:
            self.history = self.history[overflow:]

    def get_round_count(self) -> int:
        """
        获取当前对话轮次（按 user 消息计数）
        """
        return sum(1 for r, _ in self.history if r == "user")

    def summary(self, last_n: int = 10) -> str:
        """
        生成极简摘要：取最近 last_n 条消息（user/assistant 各自作为一条）
        :param last_n: 取最近多少条消息（非"轮"）
        """
        tail = self.history[-last_n:]
        lines: List[str] = []
        for role, content in tail:
            speaker = "用户" if role == "user" else "AI"
            # 单行清洗：去换行，保留完整内容
            text = (content or "").strip().replace("\n", " ")
            lines.append(f"• {speaker}: {text}")
        return "【对话历史】\n" + "\n".join(lines)

    def get_conversation_messages(self, last_n: int = 1000) -> List[Dict[str, str]]:
        """
        获取对话历史的消息列表格式，用于LLM API调用
        :param last_n: 取最近多少条消息
        :return: 消息列表，每个元素包含role和content
        """
        tail = self.history[-last_n:]
        messages = []
        for role, content in tail:
            messages.append({
                "role": role,
                "content": (content or "").strip()
            })
        return messages

    def get_recent_user_query(self, last_n: int = 1) -> str:
        """
        获取最近 n 次用户输入（合并为一句）
        """
        recent = [c for r, c in self.history if r == "user"][-last_n:]
        return "，".join(s.strip() for s in recent if s and s.strip())

    def last_user_message(self) -> Optional[str]:
        """
        获取最近一条用户消息
        """
        for role, content in reversed(self.history):
            if role == "user":
                return content
        return None

    def last_assistant_message(self) -> Optional[str]:
        """
        获取最近一条助手消息
        """
        for role, content in reversed(self.history):
            if role == "assistant":
                return content
        return None

    # ========== 兜底阶段推断（仅按轮次） ==========

    def get_stage_by_round(self) -> str:
        """
        按轮次做兜底阶段推断（不依赖 LLM）：
        - 轮次 ≤ 2        → "warmup"
        - 3 ≤ 轮次 ≤ 6    → "mid"
        - 轮次 ≥ 7        → "wrap"
        """
        rounds = self.get_round_count()
        if rounds <= 2:
            return "warmup"
        if rounds <= 6:
            return "mid"
        return "wrap"

    # ========== 可选：快速导出 ==========

    def to_dict(self) -> dict:
        """
        导出完整状态（用于数据库存储）
        """
        return {
            "history": self.history,
            "rounds": self.get_round_count(),
            "stage_by_round": self.get_stage_by_round(),
            "history_len": len(self.history),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StateTracker':
        """
        从字典创建StateTracker实例（用于数据库恢复）
        """
        instance = cls()
        if 'history' in data:
            instance.history = data['history']
        return instance