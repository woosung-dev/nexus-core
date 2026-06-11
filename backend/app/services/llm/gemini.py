"""
Google Gemini Flash 기반 LLM 서비스 (메인 모델).
google-genai SDK 사용.
"""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_genai_client() -> genai.Client:
    """프로세스 레벨 싱글톤 — TCP 핸드셰이크/SDK 초기화 비용을 메인 LLM/followup/RAG에서 공유."""
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())


def build_gemini_contents(
    prompt: str, history: list[dict[str, str]] | None
) -> str | list[types.Content]:
    """히스토리를 Gemini 멀티턴 contents로 직렬화한다 (rag/gemini.py에서도 재사용).

    히스토리가 없으면 기존 단일턴 동작(str)을 그대로 유지해 요청이 바이트 단위로 동일하다.
    history 규약: [{"role": "user"|"assistant", "content": str}], 과거→현재, 현재 질문 미포함.
    """
    if not history:
        return prompt
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
    return contents


class GeminiService(LLMService):
    """Google Gemini Flash 모델 서비스"""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        self._client = _get_genai_client()
        self._model_name = model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Gemini를 통한 단일 응답 생성"""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=build_gemini_contents(prompt, history),
            config=config,
        )

        return response.text or ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Gemini 스트리밍 응답 생성"""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=build_gemini_contents(prompt, history),
            config=config,
        ):
            if chunk.text:
                yield chunk.text
