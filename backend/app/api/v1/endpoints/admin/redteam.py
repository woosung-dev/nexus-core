"""
Admin — 레드팀 피드백 검토 대시보드 API.
1·2·3주차 응답 조회, 동일질문 수동매칭, 카테고리 수정, 리뷰어별 피드백 저장.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.crud import crud_redteam
from app.schemas.redteam import (
    CandidateItem,
    CompareWeekResponse,
    GroupCompare,
    GroupDetail,
    GroupListResponse,
    GroupManageUpdateRequest,
    GroupSummary,
    GroupUpdateRequest,
    LinkActionRequest,
    ManageFeedbackCreate,
    ManageFeedbackItem,
    ManageReportResponse,
    ManageStatsResponse,
    ReportResponse,
    ResponseItem,
    ReviewerStatus,
    ReviewItem,
    ReviewUpsertRequest,
    StatsResponse,
    UnmatchedItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/redteam", tags=["Admin - 레드팀 피드백"])


def _review_filled(reviewer_correct: str, *reflects: str) -> bool:
    """리뷰어가 의미 있는 입력을 했는지 — 옳은답변 존재 또는 반영여부 결정"""
    if reviewer_correct.strip():
        return True
    return any(r != "pending" for r in reflects)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(session: AsyncSession = Depends(get_session)) -> StatsResponse:
    """대시보드 KPI"""
    stats = await crud_redteam.get_stats(session)
    return StatsResponse(**stats)


@router.get("/report", response_model=ReportResponse)
async def get_report(session: AsyncSession = Depends(get_session)) -> ReportResponse:
    """윗선 보고용 종합 집계 (위험도·품질, 주차별 추이, 봇 비교)"""
    report = await crud_redteam.get_report(session)
    return ReportResponse(**report)


@router.get("/groups", response_model=GroupListResponse)
async def list_groups(
    category: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    level: int | None = Query(default=None, ge=0, le=3),
    disposition: str | None = None,
    assignee: str | None = None,
    tag: str | None = None,
    origin: str | None = Query(default=None, pattern="^(week3|prior)$"),
    multiweek: bool = False,
    week_present: int | None = Query(default=None, ge=1, le=3),
    matched_only: bool = False,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> GroupListResponse:
    """질문 목록(전 주차 고유질문) — 필터/검색/페이지네이션"""
    groups, total = await crud_redteam.list_groups(
        session,
        category=category,
        risk=risk,
        status=status,
        level=level,
        disposition=disposition,
        assignee=assignee,
        tag=tag,
        origin=origin,
        multiweek=multiweek,
        week_present=week_present,
        matched_only=matched_only,
        q=q,
        page=page,
        page_size=page_size,
    )
    group_ids = [g.id for g in groups]
    matched_map = await crud_redteam.get_matched_weeks_map(session, group_ids)
    reviews_map = await crud_redteam.get_reviews_map(session, group_ids)

    summaries: list[GroupSummary] = []
    for g in groups:
        weeks = matched_map.get(g.id, set())
        review_status = [
            ReviewerStatus(
                reviewer=rv.reviewer,
                filled=_review_filled(
                    rv.correct_answer, rv.week1_reflect, rv.week2_reflect, rv.week3_reflect
                ),
            )
            for rv in reviews_map.get(g.id, [])
        ]
        summaries.append(
            GroupSummary(
                id=g.id,
                question=g.question,
                category=g.category,
                category_source=g.category_source,
                risk=g.risk,
                status=g.status,
                level=g.level,
                disposition=g.disposition,
                tags=g.tags or [],
                assignee=g.assignee,
                model_answer=g.model_answer,
                week3_present=3 in weeks,
                week2_matched=2 in weeks,
                week1_matched=1 in weeks,
                review_status=review_status,
            )
        )

    return GroupListResponse(groups=summaries, total=total, page=page, page_size=page_size)


@router.get("/groups/{group_id}", response_model=GroupDetail)
async def get_group_detail(
    group_id: int, session: AsyncSession = Depends(get_session)
) -> GroupDetail:
    """기준 질문 상세 — 주차별 응답 + 리뷰"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    responses = await crud_redteam.get_group_responses(session, group_id)
    reviews = await crud_redteam.get_reviews(session, group_id)
    feedback = await crud_redteam.get_feedback(session, group_id)

    base = [ResponseItem.model_validate(r) for r in responses if r.week == 3]
    week2 = [ResponseItem.model_validate(r) for r in responses if r.week == 2]
    week1 = [ResponseItem.model_validate(r) for r in responses if r.week == 1]

    return GroupDetail(
        id=group.id,
        question=group.question,
        question_norm=group.question_norm,
        category=group.category,
        category_source=group.category_source,
        risk=group.risk,
        status=group.status,
        level=group.level,
        disposition=group.disposition,
        tags=group.tags or [],
        assignee=group.assignee,
        model_answer=group.model_answer,
        base_responses=base,
        week2_responses=week2,
        week1_responses=week1,
        reviews=[ReviewItem.model_validate(rv) for rv in reviews],
        feedback=[ManageFeedbackItem.model_validate(f) for f in feedback],
    )


@router.patch("/groups/{group_id}", response_model=GroupDetail)
async def update_group(
    group_id: int,
    request: GroupUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> GroupDetail:
    """카테고리 수동 변경"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    await crud_redteam.update_group_category(session, group, request.category)
    return await get_group_detail(group_id, session)


@router.get("/groups/{group_id}/candidates", response_model=list[CandidateItem])
async def list_candidates(
    group_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateItem]:
    """미연결 1·2주차 유사 후보 (수동 매칭용)"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    candidates = await crud_redteam.get_match_candidates(session, group, limit=limit)
    return [
        CandidateItem(
            id=resp.id,
            week=resp.week,
            question=resp.question,
            submitter=resp.submitter,
            category=resp.category,
            match_score=round(score, 3),
        )
        for resp, score in candidates
    ]


@router.post("/groups/{group_id}/links", response_model=ResponseItem)
async def link_candidate(
    group_id: int,
    request: LinkActionRequest,
    session: AsyncSession = Depends(get_session),
) -> ResponseItem:
    """후보 매칭 확정/해제"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    response = await crud_redteam.get_response(session, request.response_id)
    if not response:
        raise NotFoundError("응답을 찾을 수 없습니다.")

    response = await crud_redteam.link_response(session, group_id, response, request.action)
    return ResponseItem.model_validate(response)


@router.put("/reviews", response_model=ReviewItem)
async def upsert_review(
    request: ReviewUpsertRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewItem:
    """리뷰어 피드백 저장 (옳은 답변 + 주차별 반영여부)"""
    group = await crud_redteam.get_group(session, request.group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    review = await crud_redteam.upsert_review(
        session,
        group_id=request.group_id,
        reviewer=request.reviewer,
        correct_answer=request.correct_answer,
        week1_reflect=request.week1_reflect,
        week2_reflect=request.week2_reflect,
        week3_reflect=request.week3_reflect,
    )
    return ReviewItem.model_validate(review)


# ─── 중간보고 입력관리 (장우성 대시보드) ─────────────────────────


@router.patch("/groups/{group_id}/manage", response_model=GroupDetail)
async def update_group_manage(
    group_id: int,
    request: GroupManageUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> GroupDetail:
    """중간보고 입력관리 부분 갱신 (status/level/disposition/tags/assignee/model_answer)"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    fields = request.model_dump(exclude_unset=True)  # 보낸 필드만(명시적 null 포함)
    if fields:
        await crud_redteam.update_group_manage(session, group, fields)
    return await get_group_detail(group_id, session)


@router.get("/groups/{group_id}/compare", response_model=GroupCompare)
async def get_group_compare(
    group_id: int, session: AsyncSession = Depends(get_session)
) -> GroupCompare:
    """비교 탭 — 3주차 기준질문의 1·2·3주차 응답 나란히 (봇 C/D 정규화)"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")

    responses = await crud_redteam.get_group_responses(session, group_id)

    def _to_cmp(r) -> CompareWeekResponse:
        bots, note = crud_redteam.normalize_bots(r)
        return CompareWeekResponse(
            week=r.week,
            submitter=r.submitter,
            same_question=r.match_status in ("base", "member", "auto", "confirmed"),
            match_score=r.match_score,
            rating=r.rating,
            risk=r.risk,
            feedback_text=r.feedback_text,
            bots=bots,
            bot_note=note,
        )

    return GroupCompare(
        id=group.id,
        question=group.question,
        category=group.category,
        risk=group.risk,
        week3=[_to_cmp(r) for r in responses if r.week == 3],
        week2=[_to_cmp(r) for r in responses if r.week == 2],
        week1=[_to_cmp(r) for r in responses if r.week == 1],
    )


@router.get("/manage/stats", response_model=ManageStatsResponse)
async def get_manage_stats(session: AsyncSession = Depends(get_session)) -> ManageStatsResponse:
    """중간보고 요약 KPI — 상태·레벨·분류·태그·담당자·미분류 분포"""
    stats = await crud_redteam.get_manage_stats(session)
    return ManageStatsResponse(**stats)


@router.get("/manage/report", response_model=ManageReportResponse)
async def get_manage_report(session: AsyncSession = Depends(get_session)) -> ManageReportResponse:
    """보고서 탭 — 1~3주차 발전·위험·분류 분석 (만족도 분포 중심)"""
    report = await crud_redteam.get_manage_report(session)
    return ManageReportResponse(**report)


@router.get("/manage/unmatched", response_model=list[UnmatchedItem])
async def list_unmatched(
    week: int | None = Query(default=None, ge=1, le=2),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[UnmatchedItem]:
    """미분류 큐 — 그룹에 연결되지 않은 1·2주차 응답"""
    rows, _total = await crud_redteam.list_unmatched(
        session, week=week, q=q, page=page, page_size=page_size
    )
    return [UnmatchedItem.model_validate(r) for r in rows]


@router.get("/manage/tags", response_model=list[str])
async def list_tags(session: AsyncSession = Depends(get_session)) -> list[str]:
    """피드백 유형 태그 — 프리셋 ∪ 실제 사용된 distinct 태그"""
    return await crud_redteam.list_used_tags(session)


@router.post("/groups/{group_id}/feedback", response_model=ManageFeedbackItem)
async def create_feedback(
    group_id: int,
    request: ManageFeedbackCreate,
    session: AsyncSession = Depends(get_session),
) -> ManageFeedbackItem:
    """입력관리 담당자 피드백 추가 (코멘트 스레드)"""
    group = await crud_redteam.get_group(session, group_id)
    if not group:
        raise NotFoundError("질문 그룹을 찾을 수 없습니다.")
    fb = await crud_redteam.add_feedback(session, group_id, request.author, request.content)
    return ManageFeedbackItem.model_validate(fb)


@router.delete("/feedback/{feedback_id}")
async def remove_feedback(
    feedback_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    """담당자 피드백 삭제"""
    fb = await crud_redteam.get_feedback_obj(session, feedback_id)
    if not fb:
        raise NotFoundError("피드백을 찾을 수 없습니다.")
    await crud_redteam.delete_feedback(session, fb)
    return {"ok": True}
