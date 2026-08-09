"""
Admin — 운영 사실(ops_facts) 관리 API.

등록은 항상 status='초안' 으로 들어가고, 런타임은 승인분만 읽는다.
쓰기마다 런타임 캐시를 비운다(60초 TTL 을 기다리지 않게).
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, NotFoundError
from app.crud import crud_bot, crud_ops_facts
from app.schemas.ops_facts import (
    OpsFactCreateRequest,
    OpsFactListResponse,
    OpsFactResponse,
    OpsFactUpdateRequest,
)
from app.services.ops_facts_service import invalidate_ops_facts_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/ops-facts",
    response_model=OpsFactListResponse,
    tags=["Admin - 운영 사실"],
)
async def list_ops_facts(
    bot_id: int | None = Query(default=None, description="이 봇에 적용되는 것(전역 포함)"),
    scope: str | None = Query(default=None, description="'global' 이면 전역만"),
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> OpsFactListResponse:
    """운영 사실 목록 — 초안 포함 전건 (관리자 검수용)"""
    rows = await crud_ops_facts.list_ops_facts(
        session, bot_id=bot_id, scope=scope, kind=kind, status=status
    )
    return OpsFactListResponse(
        items=[OpsFactResponse.model_validate(row) for row in rows],
        total=len(rows),
    )


@router.get(
    "/ops-facts/{fact_id}",
    response_model=OpsFactResponse,
    tags=["Admin - 운영 사실"],
)
async def get_ops_fact(
    fact_id: int,
    session: AsyncSession = Depends(get_session),
) -> OpsFactResponse:
    fact = await crud_ops_facts.get_ops_fact(session, fact_id)
    if not fact:
        raise NotFoundError("운영 사실을 찾을 수 없습니다.")
    return OpsFactResponse.model_validate(fact)


@router.post(
    "/ops-facts",
    response_model=OpsFactResponse,
    status_code=201,
    tags=["Admin - 운영 사실"],
)
async def create_ops_fact(
    request: OpsFactCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> OpsFactResponse:
    """운영 사실 등록. status 는 '초안' 고정 — 승인 전에는 런타임에 반영되지 않는다."""
    if request.bot_id is not None:
        bot = await crud_bot.get_bot(session, request.bot_id)
        if not bot:
            raise BotNotFoundError()

    data = request.model_dump()
    data["evidence"] = [e.model_dump() for e in request.evidence]

    fact = await crud_ops_facts.create_ops_fact(session, data)
    invalidate_ops_facts_cache(request.bot_id)
    return OpsFactResponse.model_validate(fact)


@router.put(
    "/ops-facts/{fact_id}",
    response_model=OpsFactResponse,
    tags=["Admin - 운영 사실"],
)
async def update_ops_fact(
    fact_id: int,
    request: OpsFactUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> OpsFactResponse:
    """관리자 판정 / 내용 수정 (부분 업데이트)"""
    fact = await crud_ops_facts.get_ops_fact(session, fact_id)
    if not fact:
        raise NotFoundError("운영 사실을 찾을 수 없습니다.")

    fields = request.model_dump(exclude_unset=True)
    if request.evidence is not None:
        fields["evidence"] = [e.model_dump() for e in request.evidence]

    fact = await crud_ops_facts.update_ops_fact(session, fact, fields)
    # 전역 사실(bot_id=None)은 모든 봇 캐시에 들어가 있으므로 전체를 비운다.
    invalidate_ops_facts_cache(fact.bot_id)
    logger.info("ops_fact 갱신: id=%s status=%s kind=%s", fact.id, fact.status, fact.kind)
    return OpsFactResponse.model_validate(fact)


@router.delete(
    "/ops-facts/{fact_id}",
    status_code=204,
    tags=["Admin - 운영 사실"],
)
async def delete_ops_fact(
    fact_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """비활성화 (소프트 삭제 — is_active=False)"""
    fact = await crud_ops_facts.get_ops_fact(session, fact_id)
    if not fact:
        raise NotFoundError("운영 사실을 찾을 수 없습니다.")

    await crud_ops_facts.soft_delete_ops_fact(session, fact)
    invalidate_ops_facts_cache(fact.bot_id)
    logger.info("ops_fact 비활성화: id=%s", fact_id)
