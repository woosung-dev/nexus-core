# M2 인용 캡처(search_citations) 의 annotations→RAGCitation 매핑을 API 없이 단위 검증
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.rag import RAGCitation


def _make_service(monkeypatch):
    # genai client 생성을 mock 으로 대체해 API 키 없이 서비스 구성
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    return svc


def _fake_interaction(dump: dict):
    obj = SimpleNamespace()
    obj.model_dump = lambda mode=None, exclude_none=None: dump
    return obj


def test_citation_schema_new_fields_serialize():
    c = RAGCitation(title="문서A", content="본문", uri="files/abc", page_number=3)
    d = c.model_dump()
    assert d["approximate"] is False
    assert d["uri"] == "files/abc"
    assert d["page_number"] == 3
    # 기본값 (정확 인용 + 부가필드 없음)
    assert RAGCitation(title="t").model_dump() == {
        "title": "t",
        "content": None,
        "approximate": False,
        "uri": None,
        "page_number": None,
    }


@pytest.mark.asyncio
async def test_search_citations_maps_file_citation(monkeypatch):
    svc = _make_service(monkeypatch)
    dump = {
        "steps": [
            {
                "content": [
                    {
                        "annotations": [
                            {
                                "type": "file_citation",
                                "file_name": "축복식안내.txt",
                                "document_uri": "files/doc1",
                                "source": "x" * 1000,
                                "page_number": 4,
                            },
                            # file_citation 이 아닌 항목은 무시되어야 함
                            {"type": "other", "file_name": "noise"},
                        ]
                    }
                ]
            }
        ]
    }
    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(return_value=_fake_interaction(dump))

    out = await svc.search_citations(bot_id=5, prompt="질문", system_prompt="persona")

    assert len(out) == 1
    c = out[0]
    assert c.title == "축복식안내.txt"
    assert c.uri == "files/doc1"
    assert c.page_number == 4
    assert c.approximate is False
    assert len(c.content) == 800  # source[:800] 로 잘림


@pytest.mark.asyncio
async def test_search_citations_empty_when_no_annotations(monkeypatch):
    svc = _make_service(monkeypatch)
    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(
        return_value=_fake_interaction({"steps": []})
    )
    out = await svc.search_citations(bot_id=5, prompt="질문", system_prompt="persona")
    assert out == []


@pytest.mark.asyncio
async def test_search_citations_returns_empty_on_api_error(monkeypatch):
    svc = _make_service(monkeypatch)
    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(side_effect=RuntimeError("400 bad"))
    out = await svc.search_citations(bot_id=5, prompt="질문")
    assert out == []


@pytest.mark.asyncio
async def test_search_citations_appends_cite_instruction(monkeypatch):
    # persona + 인용 지침이 system_instruction 으로 전달되고 temperature 는 지정되지 않아야 함.
    svc = _make_service(monkeypatch)
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return _fake_interaction({"steps": []})

    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(side_effect=fake_create)

    from app.services.rag.gemini import _CITATION_INSTRUCTION

    await svc.search_citations(bot_id=5, prompt="질문", system_prompt="PERSONA")

    assert captured["system_instruction"] == "PERSONA" + _CITATION_INSTRUCTION
    assert "generation_config" not in captured  # temperature 0 금지 → 미지정
    assert captured["tools"][0]["metadata_filter"] == "bot_id = 5"


@pytest.mark.asyncio
async def test_update_message_citations(monkeypatch):
    # crud 의 None 케이스(메시지 없음) → False
    from app.crud import crud_chat

    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    ok = await crud_chat.update_message_citations(session, 999, [{"title": "t"}])
    assert ok is False
