"""
봇 관련 API 스키마 (요청/응답).
"""

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlanType


# --- 응답 ---
class BotResponse(BaseModel):
    """봇 목록/상세 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    icon_url: str | None = None
    tags: list[str] = []
    is_verified: bool = False
    is_new: bool = False
    plan_required: PlanType = PlanType.FREE


class BotListResponse(BaseModel):
    """봇 목록 응답 래퍼"""
    bots: list[BotResponse]
    total: int


# --- Admin 요청 ---
class BotCreateRequest(BaseModel):
    """봇 생성 요청 (Admin)"""
    name: str
    description: str
    icon_url: str | None = None
    tags: list[str] = []
    is_verified: bool = False
    is_new: bool = False
    plan_required: PlanType = PlanType.FREE
    system_prompt: str = ""
    llm_model: str = "gemini-2.0-flash"


class BotUpdateRequest(BaseModel):
    """봇 수정 요청 (Admin) — 부분 업데이트"""
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    tags: list[str] | None = None
    is_verified: bool | None = None
    is_new: bool | None = None
    plan_required: PlanType | None = None
    system_prompt: str | None = None
    llm_model: str | None = None
    is_active: bool | None = None
