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
from app.core.exceptions import ResponseBlockedError
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

# 세이프티 필터에 의한 응답 중단으로 간주하는 finish_reason 집합.
# getattr 기반으로 SDK 버전에 없는 멤버는 조용히 제외한다.
_BLOCKED_FINISH_REASONS = frozenset(
    fr
    for name in (
        "SAFETY",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
    )
    if (fr := getattr(types.FinishReason, name, None)) is not None
)


def _enum_name(value) -> str:
    """Enum 멤버/문자열 양쪽에서 이름 문자열을 얻는다 (테스트 mock 호환)."""
    return getattr(value, "name", None) or str(value)


def find_block_reason(response, *, check_empty: bool = False) -> str | None:
    """Gemini 응답/스트림 청크에서 세이프티 차단 사유를 찾는다. 비차단이면 None.

    check_empty 는 완성 응답에만 True 로 — 스트림 청크는 candidates/text 가
    비어 있는 것이 정상이므로 빈 청크를 차단으로 오판하지 않는다.
    """
    # 1) 입력(프롬프트) 차단 — prompt_feedback.block_reason
    pf = getattr(response, "prompt_feedback", None)
    block_reason = getattr(pf, "block_reason", None) if pf else None
    if block_reason and "UNSPECIFIED" not in _enum_name(block_reason):
        return f"prompt:{_enum_name(block_reason)}"

    # 2) 출력 차단 — candidates[0].finish_reason
    candidates = getattr(response, "candidates", None)
    if candidates:
        finish_reason = getattr(candidates[0], "finish_reason", None)
        if finish_reason in _BLOCKED_FINISH_REASONS:
            return f"finish:{_enum_name(finish_reason)}"
        return None

    # 3) candidates 자체가 없는 무음 차단 — H25 실증 케이스 (TypeError 의 근원)
    if check_empty:
        try:
            text = getattr(response, "text", None)
        except Exception:  # SDK 가 차단 응답의 .text 접근에서 예외를 던지는 경우까지 방어
            text = None
        if not text:
            return "empty:no_candidates"
    return None


def raise_if_blocked(response, *, source: str, check_empty: bool = False) -> None:
    """차단 감지 시 ResponseBlockedError 를 발생시킨다."""
    reason = find_block_reason(response, check_empty=check_empty)
    if reason:
        raise ResponseBlockedError(reason=reason, source=source)


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

        # 차단 시 빈 응답이 조용히 저장되는 것을 막는다 — chat_service 가 고정문으로 변환.
        raise_if_blocked(response, source="gemini", check_empty=True)

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

        yielded_any = False
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=build_gemini_contents(prompt, history),
            config=config,
        ):
            raise_if_blocked(chunk, source="gemini")
            if chunk.text:
                yielded_any = True
                yield chunk.text

        # 한 글자도 내보내지 못한 빈 스트림 = 무음 차단으로 간주.
        if not yielded_any:
            raise ResponseBlockedError(reason="empty:stream", source="gemini")
