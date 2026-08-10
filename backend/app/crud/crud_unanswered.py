"""못 답한 질문 DB 연산.

`record` 만 런타임이 쓴다. 나머지는 관리자 화면용이다.

집계는 `question_norm` 으로 GROUP BY 한다 — 라이브 실측에서 사용자 메시지 2,268건 중
74%가 정규화 후 정확히 중복이라(고유 1,195 / 2회 이상 603) 문자열 정규화만으로 성립한다.
"""

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unanswered import UnansweredQuestion
from app.services.unanswered import Triage

# 목록·삭제의 기본 보존 기간. 실사용자 질문 원문이라 수명을 제한한다.
RETENTION_DAYS = 90


async def record(
    session: AsyncSession,
    *,
    bot_id: int | None,
    session_id: int | None,
    message_id: int | None,
    question_text: str,
    question_norm: str,
    reason: str,
    detail: dict | None = None,
) -> UnansweredQuestion:
    """발생 1건 기록. 커밋은 호출자가 한다 (어시스턴트 메시지와 같은 트랜잭션)."""
    row = UnansweredQuestion(
        bot_id=bot_id,
        session_id=session_id,
        message_id=message_id,
        question_text=question_text,
        question_norm=question_norm,
        reason=reason,
        detail=detail or {},
    )
    session.add(row)
    await session.flush()
    return row


def _window(days: int | None):
    if not days:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


# 그룹 판정은 「마지막으로 찍힌 비-미분류 값」이다. 새 발생이 들어와도 `미분류` 로
# 되돌아가지 않게, 미분류 행은 정렬에서 뒤로 밀고 최신 판정 하나만 집는다.
_TRIAGE_RANK = case((UnansweredQuestion.triage == Triage.UNSET, 0), else_=1)


async def aggregate(
    session: AsyncSession,
    *,
    bot_id: int | None = None,
    reason: str | None = None,
    triage: str | None = None,
    days: int | None = RETENTION_DAYS,
    sort: str = "count",
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[dict], int]:
    """빈도순 질문 그룹 목록과 전체 그룹 수.

    **빈도순이 핵심이다** — 「무엇부터 채울지」를 이 순서가 정해 준다.
    """
    since = _window(days)

    base = select(
        UnansweredQuestion.question_norm.label("question_norm"),
        func.count().label("count"),
        func.max(UnansweredQuestion.created_at).label("last_seen"),
        # 대표 행 = 가장 최근 발생. 원문·봇을 여기서 집는다.
        func.max(UnansweredQuestion.id).label("last_id"),
    ).group_by(UnansweredQuestion.question_norm)

    if since is not None:
        base = base.where(UnansweredQuestion.created_at >= since)
    if bot_id is not None:
        base = base.where(UnansweredQuestion.bot_id == bot_id)
    if reason:
        base = base.where(UnansweredQuestion.reason == reason)

    grouped = base.subquery()

    # 대표 원문·판정은 그룹의 최신 행에서 가져온다. 판정이 찍힌 행이 있으면 그쪽이 이긴다.
    verdict = (
        select(
            UnansweredQuestion.question_norm.label("qn"),
            UnansweredQuestion.triage.label("triage"),
            UnansweredQuestion.ops_fact_id.label("ops_fact_id"),
            UnansweredQuestion.admin_note.label("admin_note"),
            func.row_number()
            .over(
                partition_by=UnansweredQuestion.question_norm,
                order_by=[desc(_TRIAGE_RANK), desc(UnansweredQuestion.triaged_at), desc(UnansweredQuestion.id)],
            )
            .label("rn"),
        )
    ).subquery()
    verdict_top = select(verdict).where(verdict.c.rn == 1).subquery()

    stmt = (
        select(
            grouped.c.question_norm,
            grouped.c.count,
            grouped.c.last_seen,
            UnansweredQuestion.bot_id,
            UnansweredQuestion.question_text,
            verdict_top.c.triage,
            verdict_top.c.ops_fact_id,
            verdict_top.c.admin_note,
        )
        .join(UnansweredQuestion, UnansweredQuestion.id == grouped.c.last_id)
        .join(verdict_top, verdict_top.c.qn == grouped.c.question_norm)
    )
    if triage:
        stmt = stmt.where(verdict_top.c.triage == triage)

    order = (
        [desc(grouped.c.last_seen), desc(grouped.c.count)]
        if sort == "recent"
        else [desc(grouped.c.count), desc(grouped.c.last_seen)]
    )
    stmt = stmt.order_by(*order)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await session.execute(stmt.limit(limit).offset(offset))).all()

    # 그룹별 이유코드 — 한 질문이 여러 신호를 낳을 수 있어 목록으로 준다.
    norms = [r.question_norm for r in rows]
    reasons: dict[str, list[str]] = {}
    if norms:
        reason_q = select(UnansweredQuestion.question_norm, UnansweredQuestion.reason).where(
            UnansweredQuestion.question_norm.in_(norms)
        )
        if since is not None:
            reason_q = reason_q.where(UnansweredQuestion.created_at >= since)
        for norm, rsn in (await session.execute(reason_q.distinct())).all():
            reasons.setdefault(norm, []).append(rsn)

    items = [
        {
            "question_norm": r.question_norm,
            "question_text": r.question_text,
            "count": r.count,
            "last_seen": r.last_seen,
            "bot_id": r.bot_id,
            "reasons": sorted(reasons.get(r.question_norm, [])),
            "triage": r.triage,
            "ops_fact_id": r.ops_fact_id,
            "admin_note": r.admin_note or "",
        }
        for r in rows
    ]
    return items, int(total or 0)


async def list_occurrences(
    session: AsyncSession, question_norm: str, *, days: int | None = RETENTION_DAYS, limit: int = 100
) -> Sequence[UnansweredQuestion]:
    """한 그룹의 개별 발생 — 관리자가 `/chats` 로 넘어가는 통로."""
    stmt = select(UnansweredQuestion).where(UnansweredQuestion.question_norm == question_norm)
    since = _window(days)
    if since is not None:
        stmt = stmt.where(UnansweredQuestion.created_at >= since)
    result = await session.execute(stmt.order_by(desc(UnansweredQuestion.created_at)).limit(limit))
    return result.scalars().all()


async def set_triage(
    session: AsyncSession,
    question_norm: str,
    *,
    triage: str,
    ops_fact_id: int | None = None,
    admin_note: str | None = None,
    triaged_by: str | None = None,
) -> int:
    """그룹 전체에 판정을 쓴다. 고친 행 수를 돌려준다."""
    rows = (
        (
            await session.execute(
                select(UnansweredQuestion).where(UnansweredQuestion.question_norm == question_norm)
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.triage = triage
        row.triaged_at = now
        if ops_fact_id is not None:
            row.ops_fact_id = ops_fact_id
        if admin_note is not None:
            row.admin_note = admin_note
        if triaged_by is not None:
            row.triaged_by = triaged_by
        session.add(row)
    await session.flush()
    return len(rows)
