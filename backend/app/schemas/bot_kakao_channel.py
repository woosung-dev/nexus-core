# 어드민 카카오 채널 등록/조회 스키마
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class KakaoChannelCreateRequest(BaseModel):
    kakao_bot_id: str

    @field_validator("kakao_bot_id")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("kakao_bot_id는 비어 있을 수 없습니다.")
        return v


class KakaoChannelResponse(BaseModel):
    id: int
    bot_id: int
    kakao_bot_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KakaoChannelListResponse(BaseModel):
    items: list[KakaoChannelResponse]
    total: int
