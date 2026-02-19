"""
카카오톡 i Open Builder 콜백 엔드포인트.
구조만 정의 — 로직은 추후 구현.
"""

import logging

from fastapi import APIRouter

from app.schemas.kakao import (
    KakaoCallbackRequest,
    KakaoCallbackResponse,
    KakaoOutput,
    KakaoSimpleText,
    KakaoTemplate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kakao", tags=["카카오톡"])


@router.post("/callback", response_model=KakaoCallbackResponse)
async def kakao_callback(request: KakaoCallbackRequest) -> KakaoCallbackResponse:
    """
    카카오톡 i Open Builder 콜백 처리.

    TODO: LLM 서비스 연동, 사용자 세션 관리
    현재는 에코 응답만 반환한다.
    """
    logger.info(f"카카오톡 콜백 수신: user={request.user.id}, utterance={request.userRequest.utterance}")

    # 임시 에코 응답
    return KakaoCallbackResponse(
        template=KakaoTemplate(
            outputs=[
                KakaoOutput(
                    simpleText=KakaoSimpleText(
                        text=f"[Nexus Core] 메시지를 수신했습니다: {request.userRequest.utterance}"
                    )
                )
            ]
        )
    )
