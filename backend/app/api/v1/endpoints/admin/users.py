"""
Admin — 사용자 관리 API 엔드포인트.
사용자 목록 조회, 정보 수정, 비활성화(소프트 삭제)를 담당한다.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.crud import crud_user
from app.schemas.user import UserAdminUpdateRequest, UserListResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=UserListResponse, tags=["Admin - 사용자 관리"])
async def list_users(
    email: str | None = Query(None, description="이메일 검색어"),
    plan_type: str | None = Query(None, description="플랜 필터 (FREE/PRO)"),
    session: AsyncSession = Depends(get_session),
) -> UserListResponse:
    """
    전체 사용자 목록 조회.
    이메일 검색 및 플랜 타입 필터링을 지원한다.
    """
    users = await crud_user.get_users(session, email=email, plan_type=plan_type)

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["Admin - 사용자 관리"])
async def update_user(
    user_id: int,
    request: UserAdminUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    사용자 정보 수정 (부분 업데이트).
    plan_type 및 is_active 변경을 지원한다.
    """
    user = await crud_user.get_user_by_id(session, user_id)

    if not user:
        raise NotFoundError("사용자를 찾을 수 없습니다.")

    user = await crud_user.update_user(session, user, request)

    logger.info(f"사용자 수정: id={user_id}, changes={request.model_dump(exclude_unset=True)}")
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204, tags=["Admin - 사용자 관리"])
async def deactivate_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    사용자 비활성화 (소프트 삭제 — is_active=False).
    실제 DB 레코드는 유지하여 데이터 무결성을 보장한다.
    """
    user = await crud_user.get_user_by_id(session, user_id)

    if not user:
        raise NotFoundError("사용자를 찾을 수 없습니다.")

    await crud_user.deactivate_user(session, user)

    logger.info(f"사용자 비활성화: id={user_id}")
