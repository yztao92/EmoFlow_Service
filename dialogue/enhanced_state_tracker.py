# File: dialogue/enhanced_state_tracker.py

from typing import Any, Dict, List, Tuple
import re

class EnhancedStateTracker:
    def __init__(self):
        # 会话全局状态
        self.state: Dict[str, Any] = {
            "current_emotion": None,
            "emotion_history": [],      # 情绪变化历史
            "technique_stack": [],      # 已使用的干预技术列表
            "technique_results": [],    # 干预技术成效记录
            "user_values": [],          # 用户提到的核心价值观
            "conversation_topics": [],  # 对话主题
            "user_concerns": []         # 用户关注的问题
        }
        # 记录完整的对话历史，元素为 (role, content)
        self.history: List[Tuple[str, str]] = []

    def update_emotion(self, emotion: str):
        """
        更新当前情绪并记录历史
        """
        self.state["current_emotion"] = emotion
        self.state["emotion_history"].append(emotion)

    def extract_user_values(self, text: str) -> List[str]:
        """
        从文本中提取用户价值观
        """
        # 价值观关键词模式
        value_patterns = [
            r"我觉得(.*?)很重要",
            r"我(.*?)很在意",
            r"对我来说(.*?)是",
            r"我(.*?)觉得",
            r"我认为(.*?)应该",
            r"我(.*?)希望",
            r"我(.*?)想要"
        ]
        
        values = []
        for pattern in value_patterns:
            matches = re.findall(pattern, text)
            values.extend(matches)
        
        return [v.strip() for v in values if len(v.strip()) > 2]

    def extract_techniques(self, text: str) -> List[str]:
        """
        从AI回复中提取使用的干预技术
        """
        technique_keywords = {
            "认知重构": ["换个角度", "重新思考", "另一种看法", "不同视角"],
            "正念冥想": ["深呼吸", "放松", "冥想", "专注当下", "觉察"],
            "行为激活": ["行动起来", "做点什么", "尝试", "改变", "行动"],
            "社交支持": ["找人聊聊", "朋友", "家人", "支持", "陪伴"],
            "问题解决": ["分析问题", "解决方案", "具体步骤", "计划"],
            "情绪调节": ["调节情绪", "控制情绪", "情绪管理", "冷静"]
        }
        
        techniques = []
        for technique, keywords in technique_keywords.items():
            if any(keyword in text for keyword in keywords):
                techniques.append(technique)
        
        return techniques

    def update_message(self, role: str, content: str):
        """
        在对话状态中添加新消息，并提取相关信息
        """
        self.history.append((role, content))
        
        if role == "user":
            # 提取用户价值观
            values = self.extract_user_values(content)
            for value in values:
                if value not in self.state["user_values"]:
                    self.state["user_values"].append(value)
            
            # 提取用户关注的问题
            concern_patterns = [
                r"我(.*?)问题",
                r"我(.*?)困难",
                r"我(.*?)困扰",
                r"我(.*?)担心",
                r"我(.*?)焦虑"
            ]
            
            for pattern in concern_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() not in self.state["user_concerns"]:
                        self.state["user_concerns"].append(match.strip())
        
        elif role == "assistant":
            # 提取AI使用的技术
            techniques = self.extract_techniques(content)
            for technique in techniques:
                if technique not in self.state["technique_stack"]:
                    self.state["technique_stack"].append(technique)

    def record_technique_result(self, technique: str, success: bool):
        """
        记录干预技术的使用结果
        """
        if technique:
            self.state["technique_stack"].append(technique)
            self.state["technique_results"].append(success)

    def should_switch_technique(self, window: int = 3) -> bool:
        """
        如果最近 window 次技术使用都标记为失败，就返回 True。
        """
        results = self.state["technique_results"][-window:]
        return len(results) == window and all(r is False for r in results)

    def get_emotion_trend(self) -> str:
        """
        分析情绪变化趋势
        """
        if len(self.state["emotion_history"]) < 2:
            return "情绪稳定"
        
        recent_emotions = self.state["emotion_history"][-3:]
        if all(e == "happy" for e in recent_emotions):
            return "情绪改善"
        elif all(e == "sad" for e in recent_emotions):
            return "情绪低落"
        elif all(e == "angry" for e in recent_emotions):
            return "情绪激动"
        else:
            return "情绪波动"

    def summary(self, last_n: int = 3) -> str:
        """
        生成增强版状态摘要
        """
        lines: List[str] = []
        
        # 对话历史
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
        lines.append(f"情绪趋势：{self.get_emotion_trend()}")
        
        # 技术信息
        recent_techs = self.state["technique_stack"][-last_n:]
        if recent_techs:
            lines.append(f"最近使用技术：{recent_techs}")
        
        # 用户价值观
        if self.state["user_values"]:
            lines.append(f"用户价值观：{self.state['user_values']}")
        
        # 用户关注的问题
        if self.state["user_concerns"]:
            lines.append(f"用户关注：{self.state['user_concerns']}")
        
        return "【对话历史及状态】\n" + "\n".join(lines) 