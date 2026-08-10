"""
Admin — 못 답한 질문 관리 API.

**빈도순이 핵심이다.** 「무엇부터 채울지」를 이 순서가 정해 준다. 그래서 기본 정렬이
`count` 고, 관리자는 위에서부터 처리하면 된다.

인증은 다른 admin 라우터와 같다(없다). 실사용자 질문 원문이 뜨는 화면이지만
`/chats` 가 이미 같은 조건으로 대화 전문을 노출하고 있어 노출 등급이 올라가지 않는다.
대신 목록·상세는 기본 90일 창만 본다 — `crud_unanswered.RETENTION_DAYS`.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError, ValidationError
from app.crud import crud_unanswered
from app.schemas.unanswered import (
    UnansweredGroupResponse,
    UnansweredListResponse,
    UnansweredOccurrenceListResponse,
    UnansweredOccurrenceResponse,
    UnansweredTriageRequest,
    UnansweredTriageResponse,
)
from app.services.unanswered import ALL_REASONS, ALL_TRIAGE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/unanswered",
    response_model=UnansweredListResponse,
    tags=["Admin - 못 답한 질문"],
)
async def list_unanswered(
    bot_id: int | None = Query(default=None),
    reason: str | None = Query(default=None, description=f"이유코드 {ALL_REASONS}"),
    triage: str | None = Query(default=None, description=f"처리 경로 {ALL_TRIAGE}"),
    days: int = Query(default=crud_unanswered.RETENTION_DAYS, ge=1, le=3650),
    sort: str = Query(default="count", pattern="^(count|recent)$"),
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> UnansweredListResponse:
    """빈도순 질문 그룹 목록."""
    items, total = await crud_unanswered.aggregate(
        session,
        bot_id=bot_id,
        reason=reason,
        triage=triage,
        days=days,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return UnansweredListResponse(
        items=[UnansweredGroupResponse(**item) for item in items],
        total=total,
    )


@router.get(
    "/unanswered/occurrences",
    response_model=UnansweredOccurrenceListResponse,
    tags=["Admin - 못 답한 질문"],
)
async def list_unanswered_occurrences(
    question_norm: str = Query(description="그룹 식별자"),
    days: int = Query(default=crud_unanswered.RETENTION_DAYS, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
) -> UnansweredOccurrenceListResponse:
    """한 그룹의 개별 발생 — `session_id` 로 `/chats` 로 넘어간다.

    경로 파라미터가 아니라 쿼리로 받는다. `question_norm` 은 정규화 결과라 임의 유니코드가
    들어와 URL 경로에서 깨질 수 있다.
    """
    rows = await crud_unanswered.list_occurrences(session, question_norm, days=days)
    if not rows:
        raise NotFoundError("해당 질문 기록을 찾을 수 없습니다.")
    return UnansweredOccurrenceListResponse(
        items=[UnansweredOccurrenceResponse.model_validate(row) for row in rows],
        total=len(rows),
    )


@router.patch(
    "/unanswered/triage",
    response_model=UnansweredTriageResponse,
    tags=["Admin - 못 답한 질문"],
)
async def set_unanswered_triage(
    request: UnansweredTriageRequest,
    session: AsyncSession = Depends(get_session),
) -> UnansweredTriageResponse:
    """그룹 전체에 처리 경로를 찍는다."""
    if not request.validate_triage():
        raise ValidationError(f"알 수 없는 처리 경로입니다: {request.triage}")

    updated = await crud_unanswered.set_triage(
        session,
        request.question_norm,
        triage=request.triage,
        ops_fact_id=request.ops_fact_id,
        admin_note=request.admin_note,
        triaged_by=request.triaged_by,
    )
    if not updated:
        raise NotFoundError("해당 질문 기록을 찾을 수 없습니다.")
    await session.commit()
    logger.info(
        "못 답한 질문 판정: norm=%.30s triage=%s ops_fact_id=%s rows=%d",
        request.question_norm,
        request.triage,
        request.ops_fact_id,
        updated,
    )
    return UnansweredTriageResponse(
        question_norm=request.question_norm,
        triage=request.triage,
        updated=updated,
    )
