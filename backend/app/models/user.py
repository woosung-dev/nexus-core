"""
User 모델.
Supabase OAuth 연동을 위해 supabase_uid, provider 필드를 포함합니다.
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
    __table_args__ = {"schema": "nexus_core"}

    id: int | None = Field(default=None, primary_key=True)
    supabase_uid: str | None = Field(
        default=None, unique=True, index=True, max_length=255
    )
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str | None = Field(default=None, max_length=255)
    provider: str | None = Field(default=None, max_length=50)
    plan_type: PlanType = Field(
        default=PlanType.FREE,
        sa_column=Column(SAEnum(PlanType, name="plantype", schema="nexus_core"))
    )
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now
    )
