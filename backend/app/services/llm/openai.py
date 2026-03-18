"""
OpenAI GPT-4o 기반 LLM 서비스 (서브 모델).
openai SDK 사용.
"""

import logging
from collections.abc import AsyncGenerator

import openai
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.exceptions import ValidationError, NexusException
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class OpenAIService(LLMService):
    """OpenAI GPT-4o 모델 서비스"""

    def __init__(self, model_name: str = "gpt-4o") -> None:
        settings = get_settings()
        api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """GPT-4o 단일 응답 생성"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except openai.NotFoundError:
            logger.error(f"OpenAI 모델을 찾을 수 없습니다: {self._model_name}")
            raise ValidationError(f"존재하지 않는 LLM 모델명입니다: {self._model_name}")
        except openai.AuthenticationError:
            logger.error("OpenAI API 인증 실패")
            raise NexusException(error_code="LLM_AUTH_FAILED", message="LLM 서비스 인증에 실패했습니다.")
        except Exception as e:
            logger.error(f"OpenAI 호출 중 예외 발생: {e}")
            raise NexusException(error_code="LLM_PROVIDER_ERROR", message="LLM 서비스 호출 중 오류가 발생했습니다.")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """GPT-4o 스트리밍 응답 생성"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
        except openai.NotFoundError:
            logger.error(f"OpenAI 모델을 찾을 수 없습니다: {self._model_name}")
            raise ValidationError(f"존재하지 않는 LLM 모델명입니다: {self._model_name}")
        except openai.AuthenticationError:
            logger.error("OpenAI API 인증 실패")
            raise NexusException(error_code="LLM_AUTH_FAILED", message="LLM 서비스 인증에 실패했습니다.")
        except Exception as e:
            logger.error(f"OpenAI 호출 중 예외 발생: {e}")
            raise NexusException(error_code="LLM_PROVIDER_ERROR", message="LLM 서비스 호출 중 오류가 발생했습니다.")

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
