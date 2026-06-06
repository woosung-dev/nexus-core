# 오픈빌더 봇(요청 본문 bot.id) ↔ 내부 봇 매핑 모델
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, func


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BotKakaoChannel(SQLModel, table=True):
    __tablename__ = "bot_kakao_channels"

    id: int | None = Field(default=None, primary_key=True)
    bot_id: int = Field(foreign_key="bots.id", index=True)
    kakao_bot_id: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )
