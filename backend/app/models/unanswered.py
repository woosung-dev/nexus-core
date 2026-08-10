"""못 답한 질문(unanswered_questions) 모델 — 「답변 못 함」이 데이터로 남는 자리.

## 왜 `messages` 컬럼이 아니라 새 표인가

셋 다 실제 이유다.

1. **`triage`·`ops_fact_id` 는 메시지가 아니라 질문 그룹의 속성이다.** 같은 질문이
   23번 들어와도 처리 판정은 하나다. 메시지 컬럼으로는 담을 자리가 없다.
2. `messages` 4,536행 백필이 필요 없다.
3. **보존 기간을 여기에만 걸 수 있다.** 테스트 문항에도 성폭력·이혼·불륜이 있었고
   실사용 질문을 관리자 화면에 그대로 띄우는 것이라 수명 제한이 필요하다.

⚠ 다만 정직하게: 90일 보존은 이 표에만 걸린다. `messages` 는 원문을 무기한 보관하므로
**실질 노출은 안 줄어든다.** 새로 만드는 데이터의 수명만 제한된다.

## 왜 `question_text` 를 복제하나

`message_id` 로 조인해도 원문을 얻을 수 있지만, 빈도 집계가 조인 없이 끝나야 한다.
그리고 `messages` 가 원문을 어차피 무기한 보관하므로 스냅샷이 노출 기간을 늘리지 않는다.

## 한 행 = 한 발생

그룹 상태(`triage`·`ops_fact_id`)는 같은 `question_norm` 을 가진 행들에 일괄로 쓴다.
새 발생이 들어와도 그룹 판정이 `미분류` 로 되돌아가지 않게, 집계는 **그룹 안에서
마지막으로 찍힌 비-미분류 값**을 그룹 상태로 본다.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class UnansweredQuestion(SQLModel, table=True):
    """못 답한 질문 1건(발생 단위) — unanswered_questions 테이블"""

    __tablename__ = "unanswered_questions"

    id: int | None = Field(default=None, primary_key=True)

    bot_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=True, index=True
        ),
    )
    # 관리자가 이 행에서 전체 대화로 넘어가는 열쇠. 화면은 `/chats` 에 위임한다 —
    # 민감한 사정이 섞인 대화 전문을 이 화면에서 다시 펴지 않기 위해서다.
    session_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True
        ),
    )
    # 이 신호를 낳은 어시스턴트 메시지
    message_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
    )

    question_text: str = Field(sa_column=Column(Text, nullable=False))
    # 빈도 집계 그룹핑 키 — `unanswered.normalize_question()` 의 결과만 들어간다
    question_norm: str = Field(sa_column=Column(String(), nullable=False, index=True))

    # unanswered.Reason 5종
    reason: str = Field(sa_column=Column(String(), nullable=False, index=True))
    # {missing: [...], src_ids: [...], retrieval_mode: "lexical"}
    detail: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}")
    )

    # ─── 관리자 판정 ─── (ops_facts 와 같은 규약)
    # unanswered.Triage 5종
    triage: str = Field(
        default="미분류",
        sa_column=Column(String(), nullable=False, server_default="미분류", index=True),
    )
    # triage='문서오류' 에서 등록한 운영 사실. 루프가 닫힌 자리를 가리킨다.
    ops_fact_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("ops_facts.id", ondelete="SET NULL"), nullable=True
        ),
    )
    triaged_by: str | None = Field(default=None)
    triaged_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    admin_note: str = Field(
        default="", sa_column=Column(String(), nullable=False, server_default="")
    )

    # 90일 보존의 기준. `scripts/purge_unanswered.py` 가 이걸 본다.
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        ),
        default_factory=get_utc_now,
    )
