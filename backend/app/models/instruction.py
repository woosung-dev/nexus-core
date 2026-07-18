# 봇 지침 빌더의 구조화된 지침과 버전 정보를 저장하는 모델.

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, func
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class BotInstruction(SQLModel, table=True):
    """봇 지침 빌더 모델 — bot_instructions 테이블"""

    __tablename__ = "bot_instructions"

    id: int | None = Field(default=None, primary_key=True)
    bot_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    name: str = Field(max_length=200)
    description: str = Field(default="")
    role: str = Field(default="")
    goal: str = Field(default="")
    tone: str = Field(default="")
    audience: str = Field(default="")
    constraints: str = Field(default="")
    dos: list = Field(default_factory=list, sa_column=Column(JSON))
    donts: list = Field(default_factory=list, sa_column=Column(JSON))
    examples: list = Field(default_factory=list, sa_column=Column(JSON))
    system_prompt: str = Field(default="")
    llm_model: str = Field(default="gemini-2.5-flash", max_length=100)
    version: int = Field(default=1)
    is_applied: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
        default_factory=get_utc_now,
    )
