# interactions 기반 RAG 답변 경로 — 인용 파싱·input 매핑·청크·비스트림/의사스트림 단위 검증(무API)
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rag.gemini import (
    _build_interaction_input,
    _chunk_text,
    _citations_from_steps,
)


# --- _citations_from_steps ---

def _steps_with(*annotations):
    return [{"content": [{"annotations": list(annotations)}]}]


def test_citations_from_steps_maps_file_citation():
    steps = _steps_with(
        {"type": "file_citation", "file_name": "규정집.pdf", "source": "근거 텍스트",
         "document_uri": "uri1", "page_number": 3},
    )
    cits = _citations_from_steps(steps)
    assert len(cits) == 1
    c = cits[0]
    assert c.title == "규정집.pdf" and c.content == "근거 텍스트"
    assert c.uri == "uri1" and c.page_number == 3
    assert c.approximate is False  # 같은 호출 출처 → 근사 아님


def test_citations_from_steps_skips_non_file_citation_and_truncates():
    steps = _steps_with(
        {"type": "url_citation", "file_name": "x"},
        {"type": "file_citation", "file_name": "a", "source": "가" * 1000},
    )
    cits = _citations_from_steps(steps)
    assert len(cits) == 1 and len(cits[0].content) == 800


def test_citations_from_steps_empty():
    assert _citations_from_steps([]) == []
    assert _citations_from_steps([{"content": [{}]}]) == []


# --- _build_interaction_input ---

def test_build_interaction_input_no_history_returns_str():
    assert _build_interaction_input("질문", None) == "질문"
    assert _build_interaction_input("질문", []) == "질문"


def test_build_interaction_input_multiturn_steps():
    history = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}]
    inp = _build_interaction_input("q2", history)
    assert isinstance(inp, list) and len(inp) == 3
    assert inp[0] == {"type": "user_input", "content": [{"type": "text", "text": "q1"}]}
    assert inp[1] == {"type": "model_output", "content": [{"type": "text", "text": "a1"}]}
    assert inp[2] == {"type": "user_input", "content": [{"type": "text", "text": "q2"}]}


# --- _chunk_text ---

def test_chunk_text_concatenates_to_original():
    text = "가" * 95
    chunks = list(_chunk_text(text, size=40))
    assert len(chunks) == 3 and "".join(chunks) == text


def test_chunk_text_empty():
    assert list(_chunk_text("")) == []


# --- generate_with_rag (비스트림) interactions ---

def _fake_interaction(output_text, steps, status="completed"):
    resp = MagicMock()
    resp.output_text = output_text
    resp.status = status
    resp.model_dump = MagicMock(return_value={"steps": steps})
    return resp


def _svc(monkeypatch, interaction):
    import app.services.llm.gemini as llm_gemini
    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService
    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))
    svc._client = MagicMock()
    svc._client.aio.interactions.create = AsyncMock(return_value=interaction)
    return svc


@pytest.mark.asyncio
async def test_generate_with_rag_parses_answer_citations_followups(monkeypatch):
    interaction = _fake_interaction(
        output_text="본문 답변입니다.\n\n<followups>\n질문1\n질문2\n질문3\n</followups>",
        steps=_steps_with(
            {"type": "file_citation", "file_name": "규정집.pdf", "source": "근거", "page_number": 1}),
    )
    svc = _svc(monkeypatch, interaction)
    r = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")
    assert r.answer == "본문 답변입니다."          # <followups> 블록 제거됨
    assert "<followups>" not in r.answer
    assert [c.title for c in r.citations] == ["규정집.pdf"]
    assert r.citations[0].approximate is False
    assert r.followups == ["질문1", "질문2", "질문3"]


@pytest.mark.asyncio
async def test_generate_with_rag_blocked_status(monkeypatch):
    from app.services.llm.gemini import SAFETY_BLOCKED_MESSAGE
    svc = _svc(monkeypatch, _fake_interaction("무언가", [], status="failed"))
    r = await svc.generate_with_rag(bot_id=3, prompt="질문", system_prompt="sp")
    assert r.answer == SAFETY_BLOCKED_MESSAGE and r.citations == [] and r.followups == []


# --- generate_stream_with_rag (의사-스트림) ---

@pytest.mark.asyncio
async def test_generate_stream_pseudostream_yields_chunks_then_meta(monkeypatch):
    interaction = _fake_interaction(
        output_text="스트림 본문 답변.\n\n<followups>\n후속질문1\n후속질문2\n후속질문3\n</followups>",
        steps=_steps_with(
            {"type": "file_citation", "file_name": "doc.txt", "source": "근거", "document_uri": "u"}),
    )
    svc = _svc(monkeypatch, interaction)
    chunks, meta = [], None
    async for piece in svc.generate_stream_with_rag(bot_id=3, prompt="질문", system_prompt="sp"):
        if isinstance(piece, dict):
            meta = piece
        else:
            chunks.append(piece)
    assert "".join(chunks) == "스트림 본문 답변."          # followups 제거된 본문이 청크로
    assert meta is not None
    assert [c["title"] for c in meta["citations"]] == ["doc.txt"]
    assert meta["followups"] == ["후속질문1", "후속질문2", "후속질문3"]
