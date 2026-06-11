# 세이프티 차단 감지(find_block_reason)와 LLM/RAG 4경로의 ResponseBlockedError 발생 검증 — H25 회귀 방지
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import types

from app.core.exceptions import ResponseBlockedError
from app.services.llm.gemini import GeminiService, find_block_reason


def _ns(*, prompt_feedback=None, candidates=None, text=None):
    return SimpleNamespace(prompt_feedback=prompt_feedback, candidates=candidates, text=text)


def _blocked_prompt(reason=types.BlockedReason.SAFETY):
    return _ns(prompt_feedback=SimpleNamespace(block_reason=reason))


def _finish(finish_reason, text=None):
    return _ns(candidates=[SimpleNamespace(finish_reason=finish_reason)], text=text)


# --- find_block_reason ---


def test_find_block_reason_prompt_feedback():
    assert find_block_reason(_blocked_prompt()) == "prompt:SAFETY"


def test_find_block_reason_finish_safety():
    assert find_block_reason(_finish(types.FinishReason.SAFETY)) == "finish:SAFETY"


def test_find_block_reason_finish_prohibited_content():
    assert (
        find_block_reason(_finish(types.FinishReason.PROHIBITED_CONTENT))
        == "finish:PROHIBITED_CONTENT"
    )


def test_find_block_reason_normal_stop():
    assert find_block_reason(_finish(types.FinishReason.STOP, text="답변"), check_empty=True) is None


def test_find_block_reason_empty_candidates_with_check_empty():
    # H25 형상: 차단 응답은 candidates=None, text=None
    assert find_block_reason(_ns(), check_empty=True) == "empty:no_candidates"
    # 스트림 청크 모드(check_empty=False)에서는 빈 청크가 정상이므로 비차단
    assert find_block_reason(_ns()) is None


def test_find_block_reason_empty_candidates_with_text_ok():
    # candidates 는 비었지만 text 가 있으면 정상 응답으로 취급 (기존 RAG 테스트 mock 형상)
    assert find_block_reason(_ns(candidates=[], text="본문"), check_empty=True) is None


def test_find_block_reason_unspecified_not_blocked():
    resp = _ns(
        prompt_feedback=SimpleNamespace(block_reason=types.BlockedReason.BLOCKED_REASON_UNSPECIFIED),
        candidates=[],
        text="본문",
    )
    assert find_block_reason(resp, check_empty=True) is None


# --- LLM 경로 (GeminiService) ---


def _llm_service(monkeypatch) -> GeminiService:
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    svc = GeminiService()
    svc._client = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_gemini_generate_raises_on_block(monkeypatch):
    svc = _llm_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(return_value=_blocked_prompt())

    with pytest.raises(ResponseBlockedError) as ei:
        await svc.generate(prompt="질문")

    assert ei.value.reason == "prompt:SAFETY"
    assert ei.value.source == "gemini"


@pytest.mark.asyncio
async def test_gemini_generate_raises_on_empty_response(monkeypatch):
    svc = _llm_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(return_value=_ns())

    with pytest.raises(ResponseBlockedError) as ei:
        await svc.generate(prompt="질문")

    assert ei.value.reason == "empty:no_candidates"


@pytest.mark.asyncio
async def test_gemini_stream_raises_on_safety_chunk(monkeypatch):
    svc = _llm_service(monkeypatch)

    async def fake_stream():
        yield _ns(candidates=[SimpleNamespace(finish_reason=None)], text="안")
        yield _finish(types.FinishReason.SAFETY)

    svc._client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())

    collected = []
    with pytest.raises(ResponseBlockedError) as ei:
        async for chunk in svc.generate_stream(prompt="질문"):
            collected.append(chunk)

    assert collected == ["안"]  # 차단 전까지의 청크는 정상 전달
    assert ei.value.reason == "finish:SAFETY"


@pytest.mark.asyncio
async def test_gemini_stream_raises_on_empty_stream(monkeypatch):
    svc = _llm_service(monkeypatch)

    async def fake_stream():
        # text 없는 청크만 — 한 글자도 내보내지 못한 무음 차단
        yield _ns(candidates=[])

    svc._client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())

    with pytest.raises(ResponseBlockedError) as ei:
        async for _ in svc.generate_stream(prompt="질문"):
            pass

    assert ei.value.reason == "empty:stream"


# --- RAG 경로 (GeminiRAGService) ---


def _rag_service(monkeypatch):
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    svc._client = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_rag_generate_raises_on_block(monkeypatch):
    svc = _rag_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(
        return_value=_blocked_prompt(types.BlockedReason.PROHIBITED_CONTENT)
    )

    with pytest.raises(ResponseBlockedError) as ei:
        await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")

    assert ei.value.reason == "prompt:PROHIBITED_CONTENT"
    assert ei.value.source == "gemini-rag"


@pytest.mark.asyncio
async def test_rag_generate_h25_none_candidates_raises_not_typeerror(monkeypatch):
    # H25 실증 형상: candidates=None → 기존엔 376줄 인용 추출에서 TypeError 가 raw 노출
    svc = _rag_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(return_value=_ns())

    with pytest.raises(ResponseBlockedError) as ei:
        await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")

    assert ei.value.reason == "empty:no_candidates"


@pytest.mark.asyncio
async def test_rag_generate_none_candidates_with_text_no_typeerror(monkeypatch):
    # 차단은 아니지만 candidates=None 인 엣지 — 인용 추출 가드 회귀 검증
    svc = _rag_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(return_value=_ns(text="본문"))

    result = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")

    assert result.answer == "본문"
    assert result.citations == []


@pytest.mark.asyncio
async def test_rag_stream_raises_before_citations_dict(monkeypatch):
    # 빈 스트림이면 citations dict 를 내보내기 전에 차단 예외
    svc = _rag_service(monkeypatch)

    async def fake_stream():
        yield _ns(candidates=[])

    svc._client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())

    collected = []
    with pytest.raises(ResponseBlockedError) as ei:
        async for chunk in svc.generate_stream_with_rag(bot_id=3, prompt="질문"):
            collected.append(chunk)

    assert collected == []  # dict 포함 어떤 것도 yield 되지 않음
    assert ei.value.reason == "empty:stream"


@pytest.mark.asyncio
async def test_rag_stream_raises_on_blocked_chunk(monkeypatch):
    svc = _rag_service(monkeypatch)

    async def fake_stream():
        yield _ns(candidates=[SimpleNamespace(finish_reason=None, grounding_metadata=None)], text="부분")
        yield _finish(types.FinishReason.SAFETY)

    svc._client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())

    collected = []
    with pytest.raises(ResponseBlockedError):
        async for chunk in svc.generate_stream_with_rag(bot_id=3, prompt="질문"):
            collected.append(chunk)

    assert collected == ["부분"]
