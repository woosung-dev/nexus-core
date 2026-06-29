"""
레드팀 피드백 검토 대시보드 모델.
1·2·3주차 레드팀 응답(xlsx)을 적재하고, 3주차를 기준으로 동일/유사 질문을
그룹으로 묶으며, 관리자(리뷰어)의 "옳은 답변" + 주차별 반영여부를 저장한다.

- redteam_question_groups: 기준 단위(3주차 고유 질문 1개 = 1행)
- redteam_responses: 3개 주차의 모든 원본 응답 행(읽기 위주)
- redteam_reviews: 리뷰어별 독립 피드백(옳은 답변 + 주차별 반영여부)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlmodel import Field, SQLModel


def get_utc_now() -> datetime:
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class RedteamQuestionGroup(SQLModel, table=True):
    """기준 질문 그룹 — 3주차 고유 질문 단위"""

    __tablename__ = "redteam_question_groups"

    id: int | None = Field(default=None, primary_key=True)

    # 대표 질문(최초 등장 원문)과 매칭용 정규화 키
    question: str
    question_norm: str = Field(index=True)

    # 카테고리: 자동분류 결과 또는 관리자 수동수정
    category: str | None = Field(default=None, index=True)
    category_source: str = Field(default="auto")  # 'auto' | 'manual'

    # 3주차 위험도 중 가장 높은 값 (없음 < 하 < 중 < 상)
    risk: str | None = Field(default=None)

    # ─── 중간보고 입력관리 필드 (장우성 대시보드) ───
    # 검증 상태: '대기' | '진행중' | '검증완료'
    status: str = Field(
        default="대기",
        sa_column=Column(String(), nullable=False, server_default="대기"),
    )
    # 보완 레벨: 0 보완불필요 · 1 실무보완 · 2 가정국 정책결정 · 3 가정국 초과 합의 (None=미분류)
    level: int | None = Field(default=None)
    # 처리 분류: '학습' | 'FAQ' | '미정'
    disposition: str = Field(
        default="미정",
        sa_column=Column(String(), nullable=False, server_default="미정"),
    )
    # 피드백 유형 태그: 프리셋 + 자유추가 문자열 배열
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # 담당자 자유 입력 이름
    assignee: str | None = Field(default=None)
    # 그룹 단위 확정 모범답변 (리뷰어별 correct_answer와 별개)
    model_answer: str = Field(
        default="",
        sa_column=Column(String(), nullable=False, server_default=""),
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


class RedteamResponse(SQLModel, table=True):
    """레드팀 원본 응답 — 3개 주차의 모든 제출 행"""

    __tablename__ = "redteam_responses"

    id: int | None = Field(default=None, primary_key=True)

    week: int = Field(index=True)  # 1 | 2 | 3
    group_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("redteam_question_groups.id", ondelete="CASCADE"), index=True
        ),
    )

    submitter: str | None = Field(default=None)
    submitted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    question: str
    question_norm: str = Field(index=True)

    # 원본 유형(1·2주차 유형 칸), 평점(1-5), 위험도(3주차)
    category: str | None = Field(default=None)
    rating: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    risk: str | None = Field(default=None)

    # 주차별로 구조가 다른 봇 응답을 JSON으로 저장
    # 1주차: {"원문": ...}, 2주차: {"A_통합": ..., "B_원리": ..., "C_정밀": ...},
    # 3주차: {"C": ..., "D": ..., "적절챗봇": ...}
    bot_responses: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    feedback_text: str | None = Field(default=None)  # 통합 자유서술 피드백
    raw: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))  # 잔여 칼럼

    # 3주차 그룹과의 매칭 정보
    match_score: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    match_status: str = Field(default="none")  # 'base' | 'auto' | 'confirmed' | 'rejected' | 'none'

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )


class RedteamReview(SQLModel, table=True):
    """관리자(리뷰어) 피드백 — (그룹, 리뷰어)당 1행, 리뷰어별 독립"""

    __tablename__ = "redteam_reviews"
    __table_args__ = (UniqueConstraint("group_id", "reviewer", name="uq_redteam_review_group_reviewer"),)

    id: int | None = Field(default=None, primary_key=True)

    group_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("redteam_question_groups.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    reviewer: str = Field(index=True)  # 리뷰어 슬롯/이름 (최대 3명)

    correct_answer: str = Field(default="")  # 이 질문에 대한 옳은 답변

    # 주차별 반영여부: 'pending' | 'reflect' | 'skip'
    week1_reflect: str = Field(default="pending")
    week2_reflect: str = Field(default="pending")
    week3_reflect: str = Field(default="pending")

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
        ),
        default_factory=get_utc_now,
    )


class RedteamManageFeedback(SQLModel, table=True):
    """입력관리 — 질문(그룹)별 복수 담당자 피드백 (코멘트 스레드, 작성자·내용·시각)"""

    __tablename__ = "redteam_manage_feedback"

    id: int | None = Field(default=None, primary_key=True)

    group_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("redteam_question_groups.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    author: str = Field()  # 작성자 이름 (프리셋 또는 자유 입력)
    content: str = Field()  # 피드백 내용

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )
