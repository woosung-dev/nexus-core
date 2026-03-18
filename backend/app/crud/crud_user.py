"""
User 관련 DB 연산(CRUD)을 담당하는 Repository.
라우터(Controller)에서 비즈니스 로직과 DB 접근 코드를 분리하기 위해 사용합니다.
"""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from app.models.user import User
from app.schemas.user import UserAdminUpdateRequest


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """사용자 단일 조회"""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_users(
    session: AsyncSession,
    email: str | None = None,
    plan_type: str | None = None,
) -> Sequence[User]:
    """필터 조건에 맞는 사용자 목록 조회 (이메일 부분 일치, 플랜 타입 필터)"""
    statement = select(User)

    if email:
        statement = statement.where(col(User.email).ilike(f"%{email}%"))  # type: ignore[attr-defined]

    if plan_type:
        statement = statement.where(User.plan_type == plan_type)

    statement = statement.order_by(col(User.created_at).desc())  # type: ignore[attr-defined]

    result = await session.execute(statement)
    return result.scalars().all()


async def update_user(session: AsyncSession, user: User, request: UserAdminUpdateRequest) -> User:
    """사용자 정보 부분 업데이트 (exclude_unset 적용)"""
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def deactivate_user(session: AsyncSession, user: User) -> None:
    """사용자 비활성화 (소프트 삭제 — is_active=False)"""
    user.is_active = False
    session.add(user)
    await session.flush()
