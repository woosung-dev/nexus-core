"""
운영 사실(ops_facts) 모델 — 문서가 답해주지 않는 확정 사실을 담는다.

규정집·공문은 "폐지된 기준"을 폐지됐다고 말해주지 않는다. 그래서 RAG 를 아무리 고쳐도
버전 드리프트(현행 미적용 기준을 현행처럼 안내)는 남는다 — 실측으로 4프롬프트 × 2회 = 8/8 오답이었다
(`exports/prompt4_2026-08-05/FINDINGS.md` §2-3).

이 테이블은 그 공백만 메운다. **positive 지식(무엇이 맞다)을 쓰지 않고**
"쓰면 안 되는 것 → 대신 쓸 것" 만 담는다. 문서가 못 채우는 칸을 창작으로 메우지 않기 위해서다.

런타임은 `status ∈ (승인, 수정승인)` 만 읽는다. 초안은 사용자에게 절대 닿지 않는다 —
초안을 LLM 이 쓰더라도 환각이 제품으로 새지 않게 하는 유일한 장치다.
회귀 하네스(`exports/regression/_l2.py`)도 같은 행을 읽어, 제품과 자가 갈라지지 않게 한다.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class OpsFact(SQLModel, table=True):
    """운영 확정 사실 1건 — ops_facts 테이블"""

    __tablename__ = "ops_facts"

    id: int | None = Field(default=None, primary_key=True)

    # NULL = 전역(모든 봇에 적용). 특정 봇에만 걸 때만 값을 넣는다.
    # 용어집(glossary_terms)과 같은 규약이라 조회 쿼리를 그대로 쓴다.
    bot_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )

    # 'deprecated' 폐지·현행 미적용 기준 | 'forbidden' 존재하지 않는 제도·용어
    # 'term' 표기 통일(후처리 치환 대상) | 'contact' 검증된 연락처 | 'crisis' 위기 자원
    kind: str = Field(sa_column=Column(String(), nullable=False, index=True))

    # 관리자 목록에서 한 줄로 식별하기 위한 라벨
    title: str = Field(default="", sa_column=Column(String(), nullable=False, server_default=""))

    # 쓰면 안 되는 것. '천일국매칭 20~30세' / '하나님' / '교제축복'
    # kind='contact' 처럼 대체 대상이 없는 종류는 빈 문자열이다.
    superseded: str = Field(
        default="", sa_column=Column(String(), nullable=False, server_default="")
    )
    # 대신 쓸 것 / 현행 사실. '현행 미적용' / '하늘부모님' / '가정행복국 02-3271-0500'
    statement: str = Field(
        default="", sa_column=Column(String(), nullable=False, server_default="")
    )

    # 비어 있으면 항상 주입한다. 값이 있으면 사용자 질문에 그 표현이 있을 때만 주입한다
    # (kind='crisis' 처럼 평소에 프롬프트를 늘릴 이유가 없는 종류용).
    triggers: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )

    # 채점기(L2)가 "챗봇이 이걸 말했나"를 판정할 정규식. 비면 `superseded` 문자열 포함으로 본다.
    # `superseded` 는 사람이 읽는 라벨('남 30세·여 28세')이고 실제 응답은 표현이 갈리므로
    # (`남성 만 30세`…) 검출 패턴을 따로 둔다. 이게 있어야 제품과 채점기가 같은 행을 쓴다.
    detect: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )

    # 근거 [{doc, locator, quote}] — redteam_goldens.evidence 와 같은 구조
    evidence: list[dict] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )
    # '공문' | '규정집v20' | '관리자확인'
    source_docs: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )

    # 같은 kind 안에서의 주입 순서. 큰 값이 먼저.
    priority: int = Field(
        default=100, sa_column=Column(Integer, nullable=False, server_default="100")
    )

    # ─── 관리자 판정 ─── (redteam_goldens 와 동일한 흐름)
    # '초안' | '승인' | '수정승인' | '반려'
    status: str = Field(
        default="초안",
        sa_column=Column(String(), nullable=False, server_default="초안", index=True),
    )
    approver: str | None = Field(default=None)
    approved_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    admin_note: str = Field(
        default="", sa_column=Column(String(), nullable=False, server_default="")
    )
    # 관리자가 고치기 전 초안 원문 — 무엇이 어떻게 바뀌었는지 사후 추적용
    draft_statement: str = Field(
        default="", sa_column=Column(String(), nullable=False, server_default="")
    )

    is_active: bool = Field(
        default=True, sa_column=Column(Boolean, nullable=False, server_default="true")
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
        ),
        default_factory=get_utc_now,
    )
