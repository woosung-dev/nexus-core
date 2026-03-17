from pydantic import BaseModel
from typing import List

from app.schemas.chat import FeedbackMessageResponse


class DashboardStatsResponse(BaseModel):
    total_bots: int
    total_users: int
    today_chats: int
    cs_score_today: float  # 0~100 사이, 피드백 없으면 0.0


class DailyChatTrend(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class BotChatShare(BaseModel):
    bot_name: str
    count: int


class DashboardDataResponse(BaseModel):
    stats: DashboardStatsResponse
    recent_trends: List[DailyChatTrend]
    bot_shares: List[BotChatShare]
    recent_negative_feedbacks: List[FeedbackMessageResponse]
    recent_positive_feedbacks: List[FeedbackMessageResponse]
    neg_total: int
    pos_total: int
