"""
공통 Enum 타입 정의.
"""

import enum


class PlanType(str, enum.Enum):
    """사용자/봇 요금제 타입"""
    FREE = "FREE"
    PRO = "PRO"


class MessageRole(str, enum.Enum):
    """메시지 발화자 역할"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


POSITIVE_FEEDBACK_REASONS: frozenset[str] = frozenset({
    "accurate",
    "helpful",
    "kind",
    "clear",
    "other",
})

NEGATIVE_FEEDBACK_REASONS: frozenset[str] = frozenset({
    "inaccurate",
    "not_helpful",
    "unsupported",
    "too_long",
    "inappropriate",
    "other",
})

ALL_FEEDBACK_REASONS: frozenset[str] = POSITIVE_FEEDBACK_REASONS | NEGATIVE_FEEDBACK_REASONS
