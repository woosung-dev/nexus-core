"""
카카오톡 i 오픈빌더 스킬 콜백 엔드포인트.
5초 안에 useCallback:true 만 반환하고, 실제 답변은 백그라운드 워커가 콜백 URL로 전송한다.
"""

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.kakao import KakaoCallbackRequest
from app.services import kakao_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kakao", tags=["카카오"])


def _waiting_response() -> dict:
    return {"version": "2.0", "useCallback": True, "data": {"text": "답변을 준비하고 있어요 🙏"}}


def _simple_text_response(text: str) -> dict:
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}]}}


@router.post("/callback")
async def kakao_callback(
    request: KakaoCallbackRequest,
    background_tasks: BackgroundTasks,
    raw_request: Request,
):
    settings = get_settings()

    # 1. 인바운드 인증 (헤더 시크릿). 미설정 환경(로컬)에서는 스킵.
    if settings.KAKAO_SKILL_SECRET:
        provided = raw_request.headers.get(settings.KAKAO_SKILL_SECRET_HEADER, "")
        if not hmac.compare_digest(provided, settings.KAKAO_SKILL_SECRET):
            logger.warning("카카오 콜백 인증 실패")
            return JSONResponse(status_code=401, content={"message": "unauthorized"})

    # 2. callbackUrl 없으면 비동기 불가 → 동기 안내(블록 미설정/콜백 미승인)
    callback_url = request.userRequest.callbackUrl
    if not callback_url:
        return _simple_text_response("콜백이 설정되지 않았습니다. 관리자에게 문의해 주세요.")

    # 3. 백그라운드 작업 예약 + 즉시 useCallback 반환
    background_tasks.add_task(
        kakao_worker.process_kakao_callback,
        kakao_bot_id=request.bot.id,
        bot_user_key=request.userRequest.user.id,
        utterance=request.userRequest.utterance,
        callback_url=callback_url,
    )
    return _waiting_response()
