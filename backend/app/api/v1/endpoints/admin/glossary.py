"""
Admin — 용어집 관리 API 엔드포인트.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.crud import crud_glossary
from app.schemas.glossary import (
    GlossaryCreateRequest,
    GlossaryListResponse,
    GlossaryResponse,
    GlossaryUpdateRequest,
)
from app.services import glossary_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/bots/{bot_id}/glossary",
    response_model=GlossaryListResponse,
    tags=["Admin - 용어집"],
)
async def list_bot_glossary(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> GlossaryListResponse:
    """봇별 및 전역 용어집 목록 조회"""
    terms = await crud_glossary.list_glossary(session, bot_id=bot_id)
    return GlossaryListResponse(
        terms=[GlossaryResponse.model_validate(term) for term in terms],
        total=len(terms),
    )


@router.get(
    "/glossary",
    response_model=GlossaryListResponse,
    tags=["Admin - 용어집"],
)
async def list_glossary(
    scope: str | None = None,
    bot_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> GlossaryListResponse:
    """전체 또는 범위별 용어집 목록 조회"""
    terms = await crud_glossary.list_glossary(session, bot_id=bot_id, scope=scope)
    return GlossaryListResponse(
        terms=[GlossaryResponse.model_validate(term) for term in terms],
        total=len(terms),
    )


@router.get(
    "/glossary/{glossary_id}",
    response_model=GlossaryResponse,
    tags=["Admin - 용어집"],
)
async def get_glossary(
    glossary_id: int,
    session: AsyncSession = Depends(get_session),
) -> GlossaryResponse:
    """용어집 단일 조회"""
    glossary = await crud_glossary.get_glossary(session, glossary_id)
    if not glossary:
        raise HTTPException(status_code=404, detail="용어집 항목을 찾을 수 없습니다.")
    return GlossaryResponse.model_validate(glossary)


@router.post(
    "/glossary",
    response_model=GlossaryResponse,
    status_code=201,
    tags=["Admin - 용어집"],
)
async def create_glossary(
    request: GlossaryCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> GlossaryResponse:
    """전역 또는 봇별 용어집 등록"""
    glossary = await glossary_service.create_glossary_with_embedding(
        session,
        request.model_dump(),
    )
    return GlossaryResponse.model_validate(glossary)


@router.post(
    "/bots/{bot_id}/glossary",
    response_model=GlossaryResponse,
    status_code=201,
    tags=["Admin - 용어집"],
)
async def create_bot_glossary(
    bot_id: int,
    request: GlossaryCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> GlossaryResponse:
    """봇별 용어집 등록"""
    data = request.model_dump()
    data["bot_id"] = bot_id
    glossary = await glossary_service.create_glossary_with_embedding(session, data)
    return GlossaryResponse.model_validate(glossary)


@router.put(
    "/glossary/{glossary_id}",
    response_model=GlossaryResponse,
    tags=["Admin - 용어집"],
)
async def update_glossary(
    glossary_id: int,
    request: GlossaryUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> GlossaryResponse:
    """용어집 부분 수정"""
    glossary = await crud_glossary.get_glossary(session, glossary_id)
    if not glossary:
        raise HTTPException(status_code=404, detail="용어집 항목을 찾을 수 없습니다.")
    updated = await glossary_service.update_glossary_with_embedding(
        session,
        glossary,
        request.model_dump(exclude_unset=True),
    )
    return GlossaryResponse.model_validate(updated)


@router.delete(
    "/glossary/{glossary_id}",
    tags=["Admin - 용어집"],
)
async def delete_glossary(
    glossary_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """용어집 비활성화"""
    glossary = await crud_glossary.get_glossary(session, glossary_id)
    if not glossary:
        raise HTTPException(status_code=404, detail="용어집 항목을 찾을 수 없습니다.")
    await crud_glossary.soft_delete_glossary(session, glossary)
    glossary_service.invalidate_glossary_cache(glossary.bot_id)
    return {"deleted": True}
