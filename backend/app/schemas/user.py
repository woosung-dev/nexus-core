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
    is_active: bool  # 어드민 관리 화면에서 활성/비활성 상태 표시 용도
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """어드민 사용자 목록 응답"""
    users: list[UserResponse] = []
    total: int = 0


class UserAdminUpdateRequest(BaseModel):
    """어드민 사용자 수정 요청 (부분 업데이트)"""
    plan_type: PlanType | None = None
    is_active: bool | None = None
