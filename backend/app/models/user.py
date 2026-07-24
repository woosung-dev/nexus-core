"""
User 모델.
외부 인증 식별자(clerk_user_id)와 provider 를 포함합니다.
clerk_user_id 는 이름과 달리 Clerk 전용이 아니며 "hanaro:{userid}",
"kakao:{bot_id}:{user_key}" 처럼 provider 별 네임스페이스를 담습니다.
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, func
from app.models.enums import PlanType


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """사용자 모델"""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    clerk_user_id: str | None = Field(
        default=None, unique=True, index=True, max_length=255
    )
    # 하나로 SSO 는 이메일을 제공하지 않으므로(규격서 8장) 없을 수 있다.
    # Postgres 의 unique 인덱스는 NULL 을 중복으로 보지 않아 제약과 공존한다.
    email: str | None = Field(default=None, max_length=255, unique=True, index=True)
    hashed_password: str | None = Field(default=None, max_length=255)
    provider: str | None = Field(default=None, max_length=50)
    plan_type: PlanType = Field(
        default=PlanType.FREE,
        sa_column=Column(SAEnum(PlanType, name="plantype"))
    )
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    is_official: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now
    )
