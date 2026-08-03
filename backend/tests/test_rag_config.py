# RAG 검색 설정(top_k·temperature)이 FileSearch/생성 config 에 실제 주입되는지 검증
import pytest
from pydantic import BaseModel
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from app.core.config import get_settings


def test_rag_settings_defaults():
    s = get_settings()
    assert s.RAG_TOP_K == 12
    assert s.RAG_TEMPERATURE == 0.3


def test_structured_rag_recovers_a_valid_bare_json_plan_but_not_plain_text():
    from app.services.rag.gemini import _structured_json_from_output

    assert _structured_json_from_output('{"route":"answer"}') == '{"route": "answer"}'
    assert _structured_json_from_output("문서 근거만 있습니다.") is None


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


@pytest.mark.asyncio
async def test_structured_rag_uses_one_interaction_call_with_same_call_citations(monkeypatch):
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    class Decision(BaseModel):
        status: str

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        interaction = MagicMock()
        interaction.output_text = '[EVIDENCE] 문서 근거\n[PLAN]\n{"status":"ready"}'
        interaction.model_dump.return_value = {
            "steps": [
                {
                    "content": [
                        {
                            "annotations": [
                                {
                                    "type": "file_citation",
                                    "file_name": "규정집.pdf",
                                    "source": "문서 근거",
                                    "page_number": 12,
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        return interaction

    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(side_effect=fake_create)

    result, citations = await svc.generate_structured_with_rag(
        bot_id=3,
        prompt="질문",
        system_prompt="문서만 근거로 답하세요.",
        model_name="gemini-3.5-flash-lite",
        response_schema=Decision,
    )

    assert result.status == "ready"
    assert citations[0].title == "규정집.pdf"
    assert citations[0].page_number == 12
    assert citations[0].approximate is False
    assert captured["model"] == "gemini-3.5-flash-lite"
    assert captured["store"] is False
    assert captured["tools"][0]["metadata_filter"] == "bot_id = 3"
    assert "response_format" not in captured
    assert "[EVIDENCE]" in captured["system_instruction"]
    assert "[PLAN]" in captured["system_instruction"]
    assert captured["generation_config"] == {"temperature": 0.0, "max_output_tokens": 1_200}
    svc._client.aio.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_read_only_store_missing_does_not_create_a_new_store(monkeypatch):
    import app.services.llm.gemini as llm_gemini
    import app.services.rag.gemini as rag_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    monkeypatch.setattr(
        rag_gemini,
        "get_settings",
        lambda: SimpleNamespace(
            FILE_SEARCH_STORE_NAME="existing-d1-store",
            FILE_SEARCH_STORE_READ_ONLY=True,
            RAG_TOP_K=12,
            RAG_TEMPERATURE=0.3,
        ),
    )
    from app.services.rag.gemini import GeminiRAGService

    async def no_stores():
        if False:
            yield None

    svc = GeminiRAGService()
    svc._client = MagicMock()
    svc._client.aio.file_search_stores.list = AsyncMock(return_value=no_stores())
    svc._client.aio.file_search_stores.create = AsyncMock()

    with pytest.raises(RuntimeError, match="찾지 못했습니다"):
        await svc.ensure_store()

    svc._client.aio.file_search_stores.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_only_store_blocks_document_uploads(monkeypatch):
    import app.services.llm.gemini as llm_gemini
    import app.services.rag.gemini as rag_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    monkeypatch.setattr(
        rag_gemini,
        "get_settings",
        lambda: SimpleNamespace(
            FILE_SEARCH_STORE_NAME="existing-d1-store",
            FILE_SEARCH_STORE_READ_ONLY=True,
            RAG_TOP_K=12,
            RAG_TEMPERATURE=0.3,
        ),
    )
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()

    with pytest.raises(PermissionError, match="업로드"):
        await svc.upload_document(11, b"test", "test.txt", "test", "text/plain")
