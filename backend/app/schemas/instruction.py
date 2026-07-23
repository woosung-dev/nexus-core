# 봇 지침 생성, 미리보기, 저장 API의 요청과 응답 스키마.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import RAGCitation


class ExamplePair(BaseModel):
    input: str = ""
    output: str = ""


# --- AI wand (지침 생성/개선) ---
class InstructionGenerateRequest(BaseModel):
    mode: Literal["generate", "improve"] = "generate"
    role: str = ""
    goal: str = ""
    tone: str = ""
    audience: str = ""
    constraints: str = ""
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    examples: list[ExamplePair] = Field(default_factory=list)
    draft: str = ""
    llm_model: str = "gemini-2.5-flash"


class InstructionGenerateResponse(BaseModel):
    system_prompt: str


# --- 실시간 테스트(미저장) ---
class InstructionPreviewRequest(BaseModel):
    system_prompt: str
    message: str
    bot_id: int | None = None
    use_rag: bool = False
    llm_model: str = "gemini-2.5-flash"


class InstructionPreviewResponse(BaseModel):
    answer: str
    citations: list[RAGCitation] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)


# --- CRUD (bot_instructions 테이블) ---
class BotInstructionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int | None
    name: str
    description: str
    role: str
    goal: str
    tone: str
    audience: str
    constraints: str
    dos: list = Field(default_factory=list)
    donts: list = Field(default_factory=list)
    examples: list = Field(default_factory=list)
    system_prompt: str
    llm_model: str
    version: int
    is_applied: bool
    created_at: datetime
    updated_at: datetime


class BotInstructionListResponse(BaseModel):
    instructions: list[BotInstructionResponse]
    total: int


class BotInstructionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    bot_id: int | None = None
    description: str = ""
    role: str = ""
    goal: str = ""
    tone: str = ""
    audience: str = ""
    constraints: str = ""
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    examples: list[ExamplePair] = Field(default_factory=list)
    system_prompt: str = ""
    llm_model: str = "gemini-2.5-flash"


class BotInstructionUpdateRequest(BaseModel):
    name: str | None = None
    bot_id: int | None = None
    description: str | None = None
    role: str | None = None
    goal: str | None = None
    tone: str | None = None
    audience: str | None = None
    constraints: str | None = None
    dos: list[str] | None = None
    donts: list[str] | None = None
    examples: list[ExamplePair] | None = None
    system_prompt: str | None = None
    llm_model: str | None = None
    is_applied: bool | None = None
