"""
User 응답 스키마.
클라이언트에게 안전하게 반환할 수 있는 필드만 포함합니다.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import PlanType


class UserResponse(BaseModel):
    id: int
    email: str
    provider: str | None
    plan_type: PlanType
    avatar_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
