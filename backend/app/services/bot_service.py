"""
Bot 관련 비즈니스 서비스 레이어.
이미지 업로드 등 복합 로직(파일 검증 + 외부 스토리지 + DB 갱신)을 조립합니다.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BotNotFoundError, ValidationError
from app.crud import crud_bot
from app.services.storage.base import FileStorageService

logger = logging.getLogger(__name__)


async def upload_bot_image(
    session: AsyncSession,
    storage: FileStorageService,
    bot_id: int,
    file_data: bytes,
    filename: str,
    content_type: str,
) -> str:
    """
    봇 대표 이미지 업로드 서비스.

    1. 봇 존재 확인
    2. 파일 크기 · 타입 검증
    3. 스토리지(Supabase/R2) 업로드
    4. DB bot.image_url 갱신 후 commit

    Returns:
        업로드된 이미지의 Public URL

    Raises:
        BotNotFoundError: 봇이 존재하지 않을 때
        ValidationError: 파일 크기·타입 오류
    """
    settings = get_settings()

    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # 파일 크기 제한
    if len(file_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"파일 크기가 {settings.MAX_UPLOAD_SIZE_MB}MB를 초과합니다.")

    # 이미지 타입 한정
    if not content_type.startswith("image/"):
        raise ValidationError("이미지 파일만 업로드 가능합니다.")

    # 스토리지 업로드 (구현체에 따라 로컬/Supabase/R2 분기)
    public_url = await storage.upload(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
    )

    # DB 갱신
    bot.image_url = public_url
    bot.updated_at = datetime.now(timezone.utc)
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    logger.info(f"봇 이미지 업로드 완료: bot_id={bot_id}, url={public_url}")
    return public_url
