from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.dashboard import DashboardDataResponse
from app.services.dashboard import get_dashboard_stats

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - 대시보드"])


@router.get("/stats", response_model=DashboardDataResponse)
async def get_dashboard_statistics(
    days: int = Query(30, description="조회 기간 (일)", ge=1, le=365),
    fb_page: int = Query(1, description="피드백 페이지", ge=1),
    fb_size: int = Query(10, description="피드백 페이지 크기", ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> DashboardDataResponse:
    """
    관리자 대시보드용 주요 통계 데이터를 반환한다.
    - KPI: 총 봇/사용자, 금일 대화수, 금일 CS 점수
    - 30일 대화 추이
    - 최근 30일 봇별 대화 점유율
    - 최근 피드백 목록 (페이징 지원)
    """
    return await get_dashboard_stats(session, days, fb_page, fb_size)
