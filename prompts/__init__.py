#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
情绪模式prompt配置包
"""

from .emotion_modes import (
    ROLE_DEFINITION,
    STYLE_AND_RULES,
    LOW_MOOD_BEHAVIOR,
    NEUTRAL_BEHAVIOR,
    CELEBRATION_BEHAVIOR,
    get_emotion_behavior,
    build_emotion_prompt,
    get_journal_generation_prompt
)

__all__ = [
    'ROLE_DEFINITION',
    'STYLE_AND_RULES', 
    'LOW_MOOD_BEHAVIOR',
    'NEUTRAL_BEHAVIOR',
    'CELEBRATION_BEHAVIOR',
    'get_emotion_behavior',
    'build_emotion_prompt',
    'get_journal_generation_prompt'
]
