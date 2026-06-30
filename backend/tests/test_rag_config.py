# RAG 검색 설정(top_k·temperature)이 interactions.create 의 tools/generation_config 에 주입되는지 검증
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.config import get_settings


def test_rag_settings_defaults():
    s = get_settings()
    assert s.RAG_TOP_K == 12
    assert s.RAG_TEMPERATURE == 0.3


def _fake_interaction(text="본문"):
    resp = MagicMock()
    resp.output_text = text
    resp.status = "completed"
    resp.model_dump = MagicMock(return_value={"steps": []})
    return resp


@pytest.mark.asyncio
async def test_generate_with_rag_injects_topk_and_temperature(monkeypatch):
    # genai client 생성을 mock 으로 대체해 API 키 없이 서비스 구성
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))

    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return _fake_interaction()

    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(side_effect=fake_create)

    # temperature 미지정 → 설정값(0.3) 적용되어야 함
    await svc.generate_with_rag(
        bot_id=3, prompt="질문", system_prompt="sp", model_name="gemini-3.1-flash-lite"
    )

    assert captured["generation_config"]["temperature"] == 0.3
    tool = captured["tools"][0]
    assert tool["type"] == "file_search"
    assert tool["top_k"] == 12
    assert tool["metadata_filter"] == "bot_id = 3"


@pytest.mark.asyncio
async def test_generate_with_rag_explicit_temperature_overrides(monkeypatch):
    # 명시 temperature 는 설정 기본값을 덮어써야 함
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))

    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return _fake_interaction()

    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(side_effect=fake_create)

    await svc.generate_with_rag(bot_id=3, prompt="질문", temperature=0.0)

    assert captured["generation_config"]["temperature"] == 0.0
