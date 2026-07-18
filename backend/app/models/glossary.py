"""
용어집 모델.
전역 또는 봇별 도메인 용어 정의를 저장하며, 채팅 답변을 대체하지 않고 프롬프트 보강에만 사용한다.
"""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, func
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class Glossary(SQLModel, table=True):
    """용어집 모델 — glossary_terms 테이블"""

    __tablename__ = "glossary_terms"

    id: int | None = Field(default=None, primary_key=True)

    # NULL은 전역 용어집, 값이 있으면 해당 봇 전용 용어집
    bot_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )

    term: str = Field(max_length=200, index=True)
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    definition: str

    # 선택적 의미 매칭용 임베딩 벡터 — gemini-embedding-001, 768차원
    term_vector: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
    )

    priority: int = Field(default=100)
    threshold: float = Field(default=0.88)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        ),
        default_factory=get_utc_now
    )
