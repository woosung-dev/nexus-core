# RAG 검색 설정(top_k·temperature)이 FileSearch/생성 config 에 실제 주입되는지 검증
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.config import get_settings


def test_rag_settings_defaults():
    s = get_settings()
    assert s.RAG_TOP_K == 12
    assert s.RAG_TEMPERATURE == 0.3


@pytest.mark.asyncio
async def test_generate_with_rag_injects_topk_and_temperature(monkeypatch):
    # genai client 생성을 mock 으로 대체해 API 키 없이 서비스 구성
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))

    captured = {}

    async def fake_generate_content(model, contents, config):
        captured["config"] = config
        resp = MagicMock()
        resp.text = "본문"
        resp.candidates = []  # grounding 추출은 try/except 로 안전 처리됨
        return resp

    svc._client = MagicMock()
    svc._client.aio.models.generate_content = AsyncMock(side_effect=fake_generate_content)

    # temperature 미지정 → 설정값(0.3) 적용되어야 함
    await svc.generate_with_rag(
        bot_id=3, prompt="질문", system_prompt="sp", model_name="gemini-3.1-flash-lite"
    )

    cfg = captured["config"]
    assert cfg.temperature == 0.3, f"temperature 기본 0.3 기대, 실제 {cfg.temperature}"
    file_search = cfg.tools[0].file_search
    assert file_search.top_k == 12, f"top_k 12 기대, 실제 {file_search.top_k}"
    assert file_search.metadata_filter == "bot_id = 3"


@pytest.mark.asyncio
async def test_generate_with_rag_explicit_temperature_overrides(monkeypatch):
    # 명시 temperature 는 설정 기본값을 덮어써야 함(프로브 등에서 사용)
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))

    captured = {}

    async def fake_generate_content(model, contents, config):
        captured["config"] = config
        resp = MagicMock()
        resp.text = "본문"
        resp.candidates = []
        return resp

    svc._client = MagicMock()
    svc._client.aio.models.generate_content = AsyncMock(side_effect=fake_generate_content)

    await svc.generate_with_rag(bot_id=3, prompt="질문", temperature=0.0)

    assert captured["config"].temperature == 0.0
