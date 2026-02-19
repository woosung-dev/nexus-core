"""
Bot 모델 — 마켓플레이스 확장 가능한 구조.
각 봇은 고유한 페르소나/시스템 프롬프트를 가지며,
관리자 페이지에서 CRUD로 관리된다.
"""

from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.enums import PlanType


class Bot(SQLModel, table=True):
    """AI 봇 모델 — 마켓플레이스 카드 UI와 매핑"""

    __tablename__ = "bots"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    description: str = Field(max_length=500)
    icon_url: str | None = Field(default=None, max_length=500)

    # 마켓플레이스 메타데이터
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_verified: bool = Field(default=False)
    is_new: bool = Field(default=False)
    plan_required: PlanType = Field(default=PlanType.FREE)

    # AI 관련 설정 — 봇마다 다른 모델/프롬프트 사용 가능
    system_prompt: str = Field(default="")
    llm_model: str = Field(default="gemini-2.0-flash", max_length=100)

    # 활성화 여부
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
