# 세이프티 차단 = 빈 응답 처리 (H25 회귀 방지) — candidates=None 이 TypeError 없이 빈 answer 가 되는지
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm.gemini import GeminiService, safe_response_text


def test_safe_response_text_normal():
    assert safe_response_text(SimpleNamespace(text="답변")) == "답변"
    assert safe_response_text(SimpleNamespace(text=None)) == ""


def test_safe_response_text_blocked_text_raises_returns_empty():
    # 차단 응답은 .text 접근이 예외를 던질 수 있다 → 빈 문자열
    class Blocked:
        @property
        def text(self):
            raise ValueError("blocked")

    assert safe_response_text(Blocked()) == ""


def _rag_service(monkeypatch):
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    svc._client = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_rag_generate_candidates_none_returns_empty_no_typeerror(monkeypatch):
    # H25: candidates=None 차단 응답이 TypeError 없이 빈 answer 로 처리됨
    svc = _rag_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(candidates=None, text=None)
    )

    result = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")

    assert result.answer == ""
    assert result.citations == []


@pytest.mark.asyncio
async def test_rag_generate_none_candidates_with_text_keeps_text(monkeypatch):
    # 차단이 아니라 candidates 만 없는 엣지 — 본문은 살린다
    svc = _rag_service(monkeypatch)
    svc._client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(candidates=None, text="본문")
    )

    result = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")

    assert result.answer == "본문"


@pytest.mark.asyncio
async def test_llm_generate_blocked_returns_empty(monkeypatch):
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    svc = GeminiService()
    svc._client = MagicMock()
    svc._client.aio.models.generate_content = AsyncMock(return_value=SimpleNamespace(text=None))

    assert await svc.generate(prompt="질문") == ""
