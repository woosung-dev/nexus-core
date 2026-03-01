"""
사용자(User) API 엔드포인트.
"""

import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["사용자"])


@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    현재 인증된 사용자의 프로필 정보를 조회합니다.
    """
    return UserResponse.model_validate(current_user)
