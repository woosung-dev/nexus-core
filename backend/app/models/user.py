"""
User 모델.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.enums import PlanType


class User(SQLModel, table=True):
    """사용자 모델"""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    plan_type: PlanType = Field(default=PlanType.FREE)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
