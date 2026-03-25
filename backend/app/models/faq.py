"""
FAQ Override 모델.
관리자가 정의한 우선순위 답변(FAQ)을 저장하며,
question_vector를 통해 사용자 질문과의 유사도를 계산한다.

참조:
- pgvector: https://github.com/pgvector/pgvector-python
- gemini-embedding-001: 768차원 (SEMANTIC_SIMILARITY task)
"""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class Faq(SQLModel, table=True):
    """FAQ Override 모델 — faqs 테이블"""

    __tablename__ = "faqs"

    id: int | None = Field(default=None, primary_key=True)

    # 봇 외래키 — 봇마다 독립적인 FAQ 세트를 가짐
    bot_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # FAQ 내용
    question: str = Field(max_length=1000)
    answer: str  # 길이 제한 없음 (TEXT 컬럼)

    # 유사도 임계값: 사용자 질문과의 코사인 유사도가 이 값 이상이면 FAQ 우선 출력
    threshold: float = Field(default=0.85)

    # 질문 임베딩 벡터 — gemini-embedding-001, 768차원
    # pgvector의 Vector 타입 사용 (SQLAlchemy 커스텀 컬럼)
    question_vector: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
    )

    # 활성화 여부 (소프트 삭제 지원)
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
