"""
Google Gemini Flash 기반 LLM 서비스 (메인 모델).
google-genai SDK 사용.
"""

import logging
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class GeminiService(LLMService):
    """Google Gemini Flash 모델 서비스"""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Gemini를 통한 단일 응답 생성"""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

        return response.text or ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Gemini 스트리밍 응답 생성"""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
