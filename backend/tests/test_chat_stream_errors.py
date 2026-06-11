# 스트리밍 에러 새니타이즈·차단 고정문·citations SSE·위기 턴 버퍼링 검증
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ResponseBlockedError
from app.services.chat_service import _GENERIC_STREAM_ERROR_MESSAGE, ChatService
from app.services.crisis_service import BLOCKED_FALLBACK_MESSAGE


def _events(chunks: list[str]) -> list:
    """SSE 청크 문자열 목록을 (kind, payload) 튜플 목록으로 파싱."""
    out = []
    for c in chunks:
        for line in c.splitlines():
            if line.startswith("data: "):
                body = line[len("data: ") :]
                out.append(("DONE", None) if body == "[DONE]" else ("data", json.loads(body)))
    return out


def _bot():
    return SimpleNamespace(id=1, system_prompt="sp", llm_model="gemini-2.5-flash")


def _request(message="정상 질문"):
    return SimpleNamespace(message=message)


def _service(monkeypatch):
    svc = ChatService(session=MagicMock())
    svc.session.commit = AsyncMock()
    msg = SimpleNamespace(id=99)
    monkeypatch.setattr(
        "app.services.chat_service.crud_chat.create_message", AsyncMock(return_value=msg)
    )
    monkeypatch.setattr(
        "app.services.chat_service.generate_followups", AsyncMock(return_value=[])
    )
    return svc


def _rag_with_stream(items):
    """items 를 순서대로 yield(또는 raise)하는 fake rag_service."""

    async def gen(**kwargs):
        for it in items:
            if isinstance(it, Exception):
                raise it
            yield it

    return SimpleNamespace(generate_stream_with_rag=gen)


async def _collect(agen):
    return [chunk async for chunk in agen]


# --- 에러 새니타이즈 (B) ---


@pytest.mark.asyncio
async def test_rag_stream_generic_error_sanitized(monkeypatch):
    svc = _service(monkeypatch)
    create_mock = AsyncMock()
    monkeypatch.setattr("app.services.chat_service.crud_chat.create_message", create_mock)
    rag = _rag_with_stream([RuntimeError("내부키=secret-abc DB연결문자열")])

    chunks = await _collect(
        svc._generate_rag_stream(rag, _request(), _bot(), SimpleNamespace(id=1))
    )

    joined = "".join(chunks)
    assert "secret-abc" not in joined and "RuntimeError" not in joined
    events = _events(chunks)
    assert ("data", {"error": _GENERIC_STREAM_ERROR_MESSAGE}) in events
    create_mock.assert_not_awaited()  # 불완전 메시지 미저장


# --- 차단 고정문 (B) ---


@pytest.mark.asyncio
async def test_rag_stream_blocked_yields_fallback_and_saves(monkeypatch):
    svc = _service(monkeypatch)
    create_mock = AsyncMock(return_value=SimpleNamespace(id=99))
    monkeypatch.setattr("app.services.chat_service.crud_chat.create_message", create_mock)
    rag = _rag_with_stream([ResponseBlockedError("prompt:SAFETY", "gemini-rag")])

    chunks = await _collect(
        svc._generate_rag_stream(rag, _request(), _bot(), SimpleNamespace(id=1))
    )

    events = _events(chunks)
    assert ("data", {"content": BLOCKED_FALLBACK_MESSAGE}) in events
    assert ("DONE", None) == events[-1]
    # 고정문이 assistant 메시지로 저장됨
    create_mock.assert_awaited_once()
    assert create_mock.await_args.kwargs["content"] == BLOCKED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_rag_stream_blocked_after_partial_appends(monkeypatch):
    svc = _service(monkeypatch)
    create_mock = AsyncMock(return_value=SimpleNamespace(id=99))
    monkeypatch.setattr("app.services.chat_service.crud_chat.create_message", create_mock)
    rag = _rag_with_stream(["부분 응답", ResponseBlockedError("finish:SAFETY", "gemini-rag")])

    chunks = await _collect(
        svc._generate_rag_stream(rag, _request(), _bot(), SimpleNamespace(id=1))
    )

    events = _events(chunks)
    # 와이어: 부분 응답 content + 고정문 content
    assert ("data", {"content": "부분 응답"}) in events
    assert ("data", {"content": BLOCKED_FALLBACK_MESSAGE}) in events
    # DB: 부분 + 고정문 이어붙임
    saved = create_mock.await_args.kwargs["content"]
    assert saved.startswith("부분 응답") and BLOCKED_FALLBACK_MESSAGE in saved


# --- citations SSE (D) ---


@pytest.mark.asyncio
async def test_rag_stream_emits_citations_event(monkeypatch):
    svc = _service(monkeypatch)
    citations = [{"title": "doc.pdf", "content": "근거 본문"}]
    rag = _rag_with_stream(["안녕", {"citations": citations}])

    chunks = await _collect(
        svc._generate_rag_stream(rag, _request(), _bot(), SimpleNamespace(id=1))
    )

    events = _events(chunks)
    cit_event = next(e[1] for e in events if e[0] == "data" and e[1].get("type") == "citations")
    assert cit_event["items"] == citations
    assert cit_event["message_id"] == 99

    # 순서: content → citations → DONE
    content_idx = next(i for i, e in enumerate(events) if e[0] == "data" and "content" in e[1])
    cit_idx = next(i for i, e in enumerate(events) if e[0] == "data" and e[1].get("type") == "citations")
    assert content_idx < cit_idx < len(events) - 1
    assert events[-1] == ("DONE", None)


@pytest.mark.asyncio
async def test_rag_stream_no_citations_event_when_empty(monkeypatch):
    svc = _service(monkeypatch)
    rag = _rag_with_stream(["안녕", {"citations": []}])

    chunks = await _collect(
        svc._generate_rag_stream(rag, _request(), _bot(), SimpleNamespace(id=1))
    )

    events = _events(chunks)
    assert not any(e[0] == "data" and e[1].get("type") == "citations" for e in events)


# --- 위기 턴 스트림 버퍼링 + 번호 필터 (C) ---


@pytest.mark.asyncio
async def test_crisis_stream_buffers_and_filters_phone(monkeypatch):
    svc = _service(monkeypatch)
    create_mock = AsyncMock(return_value=SimpleNamespace(id=99))
    monkeypatch.setattr("app.services.chat_service.crud_chat.create_message", create_mock)
    # 청크가 쪼개져 들어와도 버퍼링 후 한 번에 필터
    rag = _rag_with_stream(["힘드시겠어요. ", "급하면 010-1234-5678로 연락 주세요. ", "혼자가 아니에요."])

    chunks = await _collect(
        svc._generate_rag_stream(
            rag, _request("죽고 싶어"), _bot(), SimpleNamespace(id=1), crisis_keyword="죽고 싶"
        )
    )

    events = _events(chunks)
    content_events = [e[1]["content"] for e in events if e[0] == "data" and "content" in e[1]]
    # 위기 턴은 content 이벤트가 1회로 합쳐짐
    assert len(content_events) == 1
    body = content_events[0]
    assert "010" not in body  # 번호 문장 제거
    assert "힘드시겠어요." in body and "혼자가 아니에요." in body
    # DB 저장본도 필터된 본문
    assert "010" not in create_mock.await_args.kwargs["content"]


# --- 비스트리밍 차단 fallback (B) ---


@pytest.mark.asyncio
async def test_nonstream_rag_blocked_returns_fallback(monkeypatch):
    svc = _service(monkeypatch)
    monkeypatch.setattr("app.services.chat_service.search_faq_override", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.services.chat_service.crud_chat.get_recent_messages", AsyncMock(return_value=[])
    )

    rag = SimpleNamespace(
        generate_with_rag=AsyncMock(side_effect=ResponseBlockedError("prompt:SAFETY", "gemini-rag"))
    )
    monkeypatch.setattr("app.services.chat_service.get_rag_service", lambda provider: rag)

    bot = SimpleNamespace(
        id=1, system_prompt="sp", llm_model="gemini-2.5-flash", use_rag=True, history_window=0
    )
    request = SimpleNamespace(
        message="강간 당했어요", stream=False, use_rag=True
    )
    chat_session = SimpleNamespace(id=1)

    resp = await svc.process_chat_request(request=request, bot=bot, chat_session=chat_session)

    assert resp.source == "blocked_fallback"
    assert resp.content == BLOCKED_FALLBACK_MESSAGE
