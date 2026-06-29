"""
레드팀 피드백 대시보드 API 스키마 (요청/응답).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

REFLECT_VALUES = ("pending", "reflect", "skip")

# ─── 중간보고 입력관리 값 ─────────────────────────────────────
STATUS_VALUES = ("대기", "진행중", "검증완료")
DISPOSITION_VALUES = ("학습", "FAQ", "미정")
LEVEL_VALUES = (0, 1, 2, 3)  # 0 보완불필요 · 1 실무보완 · 2 가정국 정책결정 · 3 가정국 초과 합의
# 피드백 유형 태그 프리셋 (인앱 자유추가 가능, 사용자 확정 전 기본 시드)
TAG_PRESETS = (
    "분류 미정",
    "사실·정보 오류",
    "표현·어투",
    "내용 누락·불충분",
    "안전·민감",
    "출처·말씀자료",
    "UX·버그",
)


# ─── 응답 스키마 ─────────────────────────────────────────────


class ReviewItem(BaseModel):
    """리뷰어 피드백 단건"""

    model_config = ConfigDict(from_attributes=True)

    reviewer: str
    correct_answer: str
    week1_reflect: str
    week2_reflect: str
    week3_reflect: str
    updated_at: datetime | None = None


class ResponseItem(BaseModel):
    """레드팀 원본 응답 단건"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    week: int
    submitter: str | None
    submitted_at: datetime | None
    question: str
    category: str | None
    rating: float | None
    risk: str | None
    bot_responses: dict | None
    feedback_text: str | None
    match_score: float | None
    match_status: str


class ReviewerStatus(BaseModel):
    """리스트에서 리뷰어별 작성 여부 요약"""

    reviewer: str
    filled: bool


class GroupSummary(BaseModel):
    """기준 질문 리스트 항목"""

    id: int
    question: str
    category: str | None
    category_source: str
    risk: str | None
    # 중간보고 입력관리 상태
    status: str
    level: int | None
    disposition: str
    tags: list[str]
    assignee: str | None
    model_answer: str
    week2_matched: bool
    week1_matched: bool
    review_status: list[ReviewerStatus]


class GroupListResponse(BaseModel):
    """기준 질문 목록 응답"""

    groups: list[GroupSummary]
    total: int
    page: int
    page_size: int


class GroupDetail(BaseModel):
    """기준 질문 상세 — 주차별 응답 + 리뷰"""

    id: int
    question: str
    question_norm: str
    category: str | None
    category_source: str
    risk: str | None
    # 중간보고 입력관리 상태
    status: str
    level: int | None
    disposition: str
    tags: list[str]
    assignee: str | None
    model_answer: str
    base_responses: list[ResponseItem]  # 3주차
    week2_responses: list[ResponseItem]
    week1_responses: list[ResponseItem]
    reviews: list[ReviewItem]


class CandidateItem(BaseModel):
    """수동 매칭 후보 (미연결 1·2주차 응답)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    week: int
    question: str
    submitter: str | None
    category: str | None
    match_score: float | None


class StatsResponse(BaseModel):
    """대시보드 KPI"""

    total_groups: int
    total_responses: int
    by_category: dict[str, int]
    by_risk: dict[str, int]
    matched_week2: int
    matched_week1: int
    review_progress: dict[str, int]  # reviewer -> 작성 그룹 수


# ─── 중간보고 입력관리 ─────────────────────────────────────────


class CompareWeekResponse(BaseModel):
    """비교 탭 — 주차별 응답 1건 (봇 라벨 C/D 정규화)"""

    week: int
    submitter: str | None
    same_question: bool  # 매칭(auto/confirmed)으로 붙은 동일질문 여부
    match_score: float | None
    rating: float | None
    risk: str | None
    feedback_text: str | None
    bots: dict[str, str | None]  # C/D 정규화된 봇 응답
    bot_note: str | None  # 예: "원리B 단종", "1주차 단일봇(원문)"


class GroupCompare(BaseModel):
    """비교 탭 — 3주차 기준질문의 주차별 나란히 보기"""

    id: int
    question: str
    category: str | None
    risk: str | None
    week3: list[CompareWeekResponse]
    week2: list[CompareWeekResponse]
    week1: list[CompareWeekResponse]


class ManageStatsResponse(BaseModel):
    """중간보고 요약 KPI"""

    total_groups: int
    by_status: dict[str, int]
    by_level: dict[str, int]  # "0".."3" + "미분류"
    by_disposition: dict[str, int]
    by_tag: dict[str, int]
    unmatched_week2: int
    unmatched_week1: int
    assignee_load: dict[str, int]  # assignee -> 그룹 수


class UnmatchedItem(BaseModel):
    """미분류 큐 — 그룹에 연결되지 않은 1·2주차 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    week: int
    question: str
    submitter: str | None
    category: str | None
    match_status: str


# ─── 보고용 리포트 ─────────────────────────────────────────────


class ReportSummary(BaseModel):
    total_groups: int
    total_responses: int
    responses_by_week: dict[str, int]
    high_risk: int
    mid_risk: int
    avg_rating_week1: float | None
    avg_rating_week3: float | None
    bot_c: int
    bot_d: int
    bot_none: int


class TopRiskQuestion(BaseModel):
    group_id: int
    question: str
    category: str | None
    risk: str | None
    rating_avg: float | None


class ReportResponse(BaseModel):
    """윗선 보고용 종합 집계"""

    summary: ReportSummary
    risk_distribution: list[dict]
    category_distribution: list[dict]
    risk_by_category: list[dict]
    rating_by_week: list[dict]
    rating_trend: list[dict]
    bot_preference: list[dict]
    bot_by_category: list[dict]
    reflect_summary: list[dict]
    reflect_by_risk: list[dict]
    reviewer_agreement: dict
    pending_high_risk: list[dict]
    split_groups: list[dict]
    bot_improvement: dict
    top_risk_questions: list[TopRiskQuestion]


# ─── 요청 스키마 ─────────────────────────────────────────────


class GroupUpdateRequest(BaseModel):
    """기준 질문 카테고리 수동 변경"""

    category: str | None = Field(default=None, max_length=100)


class LinkActionRequest(BaseModel):
    """후보 매칭 확정/해제"""

    response_id: int
    action: str = Field(..., pattern="^(confirm|reject)$")


class ReviewUpsertRequest(BaseModel):
    """리뷰어 피드백 저장 (upsert)"""

    group_id: int
    reviewer: str = Field(..., min_length=1, max_length=50)
    correct_answer: str = Field(default="")
    week1_reflect: str = Field(default="pending", pattern="^(pending|reflect|skip)$")
    week2_reflect: str = Field(default="pending", pattern="^(pending|reflect|skip)$")
    week3_reflect: str = Field(default="pending", pattern="^(pending|reflect|skip)$")


class GroupManageUpdateRequest(BaseModel):
    """중간보고 입력관리 — 부분 업데이트 (보낸 필드만 갱신)

    level·assignee는 None으로 '미분류/미지정' 비우기가 가능하므로, 엔드포인트에서
    model_fields_set으로 '미전송 vs 명시적 null'을 구분해 적용한다.
    """

    status: str | None = Field(default=None, pattern="^(대기|진행중|검증완료)$")
    level: int | None = Field(default=None, ge=0, le=3)
    disposition: str | None = Field(default=None, pattern="^(학습|FAQ|미정)$")
    tags: list[str] | None = Field(default=None)
    assignee: str | None = Field(default=None, max_length=50)
    model_answer: str | None = Field(default=None)
