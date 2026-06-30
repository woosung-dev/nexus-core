# 세이프티 차단 시 raw 에러/빈 응답 대신 간단한 안내 문구가 나오는지 (H25)
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm.gemini import (
    SAFETY_BLOCKED_MESSAGE,
    GeminiService,
    is_blocked,
    safe_response_text,
)


def test_is_blocked():
    # 입력 차단(candidates 없음) / 출력 차단(본문 없음) → 차단
    assert is_blocked(SimpleNamespace(candidates=None, text=None)) is True
    assert is_blocked(SimpleNamespace(candidates=[object()], text="")) is True
    # 정상 응답 → 비차단
    assert is_blocked(SimpleNamespace(candidates=[object()], text="답변")) is False


def test_safe_response_text():
    assert safe_response_text(SimpleNamespace(text="답변")) == "답변"
    assert safe_response_text(SimpleNamespace(text=None)) == ""

    class Blocked:
        @property
        def text(self):
            raise ValueError("blocked")

    assert safe_response_text(Blocked()) == ""


@pytest.mark.asyncio
async def test_rag_blocked_returns_message(monkeypatch):
    # interactions: status=failed/cancelled 또는 빈 output_text → 안내 문구(차단), 인용 없음
    import app.services.llm.gemini as g

    monkeypatch.setattr(g, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    svc._client = MagicMock()

    def _interaction(status, text):
        resp = MagicMock()
        resp.status = status
        resp.output_text = text
        resp.model_dump = MagicMock(return_value={"steps": []})
        return resp

    # status=failed → 차단
    svc._client.aio.interactions.create = AsyncMock(return_value=_interaction("failed", "무언가"))
    r = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")
    assert r.answer == SAFETY_BLOCKED_MESSAGE
    assert r.citations == []

    # status=completed 이나 빈 output_text → 차단
    svc._client.aio.interactions.create = AsyncMock(return_value=_interaction("completed", "  "))
    r2 = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")
    assert r2.answer == SAFETY_BLOCKED_MESSAGE


@pytest.mark.asyncio
async def test_llm_blocked_returns_message(monkeypatch):
    import app.services.llm.gemini as g

    monkeypatch.setattr(g, "_get_genai_client", lambda: MagicMock())
    svc = GeminiService()
    svc._client = MagicMock()
    svc._client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(candidates=None, text=None)
    )

    assert await svc.generate(prompt="질문") == SAFETY_BLOCKED_MESSAGE
