"""
LLM 서비스 추상 인터페이스.
모델 교체(Gemini ↔ OpenAI)가 비즈니스 로직 변경 없이 가능하도록 설계.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMService(ABC):
    """LLM 호출 추상 클래스"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        단일 응답 생성 (Non-Streaming).

        Args:
            prompt: 사용자 입력
            system_prompt: 시스템 프롬프트 (봇 페르소나)
            temperature: 생성 다양성 (0.0~1.0)
            max_tokens: 최대 토큰 수

        Returns:
            생성된 텍스트
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성 (SSE용).

        Args:
            prompt: 사용자 입력
            system_prompt: 시스템 프롬프트
            temperature: 생성 다양성
            max_tokens: 최대 토큰 수

        Yields:
            텍스트 청크
        """
        ...
