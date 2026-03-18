from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_dashboard
from app.schemas.dashboard import (
    DashboardDataResponse,
    DashboardStatsResponse,
    DailyChatTrend,
    BotChatShare,
)
from app.schemas.chat import FeedbackMessageResponse


async def get_dashboard_stats(session: AsyncSession, days: int = 30, fb_page: int = 1, fb_size: int = 10) -> DashboardDataResponse:
    """대시보드 통계 데이터 집계"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_start = today_start - timedelta(days=days - 1)

    # 1. Total Bots & Total Users
    total_bots = await crud_dashboard.get_total_bots_count(session)
    total_users = await crud_dashboard.get_total_users_count(session)

    # 2. Today's Chats
    today_chats = await crud_dashboard.get_today_chats_count(session, today_start)

    # 3. Today's CS Score
    feedback_counts = await crud_dashboard.get_today_feedback_counts(session, today_start)
    total_feedbacks = sum(feedback_counts.values())
    up_feedbacks = feedback_counts.get("up", 0)
    cs_score_today = (up_feedbacks / total_feedbacks * 100) if total_feedbacks > 0 else 0.0

    # 4. Recent 30 Days Trend (Chats by Day)
    trend_rows = await crud_dashboard.get_recent_chat_trend(session, period_start)
    trend_dict = {
        (row[0] if isinstance(row[0], datetime) else row[0]).date().isoformat(): row[1] 
        for row in trend_rows
    }
    
    recent_trends: List[DailyChatTrend] = []
    # 요청된 days(ex: 30)일치 빈 날짜 0으로 채우기
    for i in range(days):
        target_date = (period_start + timedelta(days=i)).date().isoformat()
        recent_trends.append(
            DailyChatTrend(date=target_date, count=trend_dict.get(target_date, 0))
        )

    # 5. Bot Shares (최근 X일 기준)
    share_rows = await crud_dashboard.get_recent_bot_shares(session, period_start)
    bot_shares = [BotChatShare(bot_name=row[0], count=row[1]) for row in share_rows]

    # 6. Recent Feedbacks (Paginated)
    fb_offset = (fb_page - 1) * fb_size

    # Negative Feedbacks
    neg_total = await crud_dashboard.get_feedback_count_by_type(session, "down")
    neg_rows = await crud_dashboard.get_recent_feedbacks_by_type(session, "down", fb_size, fb_offset)
    
    recent_negatives = []
    for msg_obj, session_title, bot_name, user_email in neg_rows:
        data = msg_obj.model_dump()
        data["session_title"] = session_title
        data["bot_name"] = bot_name
        data["user_email"] = user_email
        recent_negatives.append(FeedbackMessageResponse.model_validate(data))

    # Positive Feedbacks
    pos_total = await crud_dashboard.get_feedback_count_by_type(session, "up")
    pos_rows = await crud_dashboard.get_recent_feedbacks_by_type(session, "up", fb_size, fb_offset)
    
    recent_positives = []
    for msg_obj, session_title, bot_name, user_email in pos_rows:
        data = msg_obj.model_dump()
        data["session_title"] = session_title
        data["bot_name"] = bot_name
        data["user_email"] = user_email
        recent_positives.append(FeedbackMessageResponse.model_validate(data))

    return DashboardDataResponse(
        stats=DashboardStatsResponse(
            total_bots=total_bots,
            total_users=total_users,
            today_chats=today_chats,
            cs_score_today=round(cs_score_today, 1),
        ),
        recent_trends=recent_trends,
        bot_shares=bot_shares,
        recent_negative_feedbacks=recent_negatives,
        recent_positive_feedbacks=recent_positives,
        neg_total=neg_total,
        pos_total=pos_total,
    )
