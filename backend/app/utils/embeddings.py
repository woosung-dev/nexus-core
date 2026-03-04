"""
텍스트 임베딩 유틸리티.
Google gemini-embedding-001 모델을 사용하여 텍스트를 768차원 벡터로 변환한다.

모델 선택 근거:
- 무료 티어(1,500 RPM) — FAQ 등록/수정은 저빈도라 충분
- MTEB Multilingual 1위급(68.32점) — 한국어 포함 100+ 언어 지원
- 기존 google-genai SDK 활용 — 추가 의존성 불필요
- SEMANTIC_SIMILARITY task_type — 질문 유사도 매칭에 최적
"""

import asyncio
import logging

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 임베딩 모델 설정
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768  # 768 / 1536 / 3072 중 선택


def _get_client() -> genai.Client:
    """google-genai 클라이언트 생성 (GEMINI_API_KEY 사용)"""
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def get_embedding(text: str) -> list[float]:
    """
    텍스트를 gemini-embedding-001 모델로 임베딩하여 768차원 벡터를 반환한다.

    Args:
        text: 임베딩할 텍스트 (FAQ 질문 등)

    Returns:
        768차원 float 리스트

    Raises:
        RuntimeError: 임베딩 API 호출 실패 시
    """
    try:
        client = _get_client()

        # google-genai SDK는 동기 방식이므로, 비동기 컨텍스트에서 별도 스레드로 실행
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="SEMANTIC_SIMILARITY",
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            ),
        )

        embedding = response.embeddings[0].values
        logger.debug(f"임베딩 완료: 차원={len(embedding)}, 텍스트 미리보기='{text[:50]}...'")
        return list(embedding)

    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        raise RuntimeError(f"임베딩 생성에 실패했습니다: {e}") from e
