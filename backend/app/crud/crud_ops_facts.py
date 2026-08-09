"""
운영 사실(ops_facts) DB 연산.

`get_approved_for_bot` 만 런타임이 쓴다 — 승인분·활성행만 돌려준다.
나머지는 관리자 화면용이다.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.ops_facts import OpsFact

# 런타임 주입 대상. 초안·반려는 사용자에게 닿지 않는다.
RUNTIME_STATUS = ("승인", "수정승인")
# 관리자 판정이 끝난 상태 — approved_at 을 찍는 기준
DECIDED = ("승인", "수정승인", "반려")


async def get_ops_fact(session: AsyncSession, fact_id: int) -> OpsFact | None:
    result = await session.execute(select(OpsFact).where(OpsFact.id == fact_id))
    return result.scalar_one_or_none()


async def get_approved_for_bot(session: AsyncSession, bot_id: int) -> Sequence[OpsFact]:
    """런타임용 — 이 봇에 적용되는 승인된 운영 사실 (전역 + 봇 전용).

    용어집(crud_glossary.get_active_glossary_for_bot)과 같은 규약이다.
    """
    result = await session.execute(
        select(OpsFact)
        .where(
            OpsFact.is_active == True,  # noqa: E712
            OpsFact.status.in_(RUNTIME_STATUS),
            or_(OpsFact.bot_id == bot_id, OpsFact.bot_id.is_(None)),
        )
        .order_by(OpsFact.priority.desc(), OpsFact.id)
    )
    return result.scalars().all()


async def list_ops_facts(
    session: AsyncSession,
    bot_id: int | None = None,
    scope: str | None = None,
    kind: str | None = None,
    status: str | None = None,
) -> Sequence[OpsFact]:
    """관리자용 목록 — 초안 포함 전건"""
    statement = select(OpsFact)
    if scope == "global":
        statement = statement.where(OpsFact.bot_id.is_(None))
    elif bot_id is not None:
        statement = statement.where(or_(OpsFact.bot_id == bot_id, OpsFact.bot_id.is_(None)))
    if kind:
        statement = statement.where(OpsFact.kind == kind)
    if status:
        statement = statement.where(OpsFact.status == status)

    result = await session.execute(
        statement.order_by(OpsFact.kind, OpsFact.priority.desc(), OpsFact.id)
    )
    return result.scalars().all()


async def create_ops_fact(session: AsyncSession, data: dict) -> OpsFact:
    """등록 — status 는 모델 기본값('초안')을 그대로 쓴다."""
    fact = OpsFact(**data)
    session.add(fact)
    await session.flush()
    await session.refresh(fact)
    return fact


async def update_ops_fact(session: AsyncSession, fact: OpsFact, fields: dict) -> OpsFact:
    """부분 업데이트 + 관리자 판정 반영.

    statement 를 처음 고칠 때 초안 원문을 `draft_statement` 에 보존한다
    (redteam_goldens.draft_golden 과 같은 이유 — 무엇이 어떻게 바뀌었는지 사후 추적).
    """
    if fields.get("statement") is not None and not fact.draft_statement:
        fact.draft_statement = fact.statement

    for key, value in fields.items():
        if value is not None:
            setattr(fact, key, value)

    if fields.get("status") in DECIDED and fact.approved_at is None:
        fact.approved_at = datetime.now(timezone.utc)

    fact.updated_at = datetime.now(timezone.utc)
    session.add(fact)
    await session.flush()
    await session.refresh(fact)
    return fact


async def soft_delete_ops_fact(session: AsyncSession, fact: OpsFact) -> None:
    """비활성화 (소프트 삭제)"""
    fact.is_active = False
    fact.updated_at = datetime.now(timezone.utc)
    session.add(fact)
    await session.flush()
