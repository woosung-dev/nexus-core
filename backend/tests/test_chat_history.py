# 멀티턴 대화 기억(history_window) — 히스토리 로드/드랍/직렬화가 LLM 호출에 반영되는지 검증
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import get_settings
from app.models.bot import Bot
from app.models.chat import Message
from app.models.enums import MessageRole
from app.services.chat_service import ChatService
from app.services.llm.gemini import build_gemini_contents


def _bot(window: int) -> Bot:
    return Bot(name="테스트봇", description="테스트", history_window=window)


def _msg(role: MessageRole, content: str) -> Message:
    return Message(session_id=1, role=role, content=content)


def test_history_settings_defaults():
    s = get_settings()
    assert s.CHAT_HISTORY_MAX_CHARS_PER_MESSAGE == 500


# --- ChatService._load_history ---


@pytest.mark.asyncio
async def test_load_history_disabled_when_window_zero(monkeypatch):
    svc = ChatService(session=MagicMock())
    crud_mock = AsyncMock()
    monkeypatch.setattr("app.services.chat_service.crud_chat.get_recent_messages", crud_mock)

    history = await svc._load_history(1, _bot(window=0), "현재 질문")

    assert history == []
    crud_mock.assert_not_awaited()  # 비활성 시 DB 조회 0회


@pytest.mark.asyncio
async def test_load_history_drops_presaved_current_message(monkeypatch):
    # call site가 현재 사용자 메시지를 선저장하므로 마지막 row가 현재 메시지면 드랍해야 함
    rows = [
        _msg(MessageRole.USER, "김치찌개 만드는 법 알려줘"),
        _msg(MessageRole.ASSISTANT, "김치찌개는 이렇게 만듭니다"),
        _msg(MessageRole.USER, "방금 뭐 물어봤지?"),
    ]
    svc = ChatService(session=MagicMock())
    monkeypatch.setattr(
        "app.services.chat_service.crud_chat.get_recent_messages",
        AsyncMock(return_value=rows),
    )

    history = await svc._load_history(1, _bot(window=8), "방금 뭐 물어봤지?")

    assert history == [
        {"role": "user", "content": "김치찌개 만드는 법 알려줘"},
        {"role": "assistant", "content": "김치찌개는 이렇게 만듭니다"},
    ]


@pytest.mark.asyncio
async def test_load_history_no_drop_then_trims_to_window(monkeypatch):
    # 마지막 row가 현재 메시지와 다르면 드랍하지 않고 윈도우 크기로만 트림
    rows = [
        _msg(MessageRole.ASSISTANT, "a0"),
        _msg(MessageRole.USER, "q1"),
        _msg(MessageRole.ASSISTANT, "a1"),
    ]
    svc = ChatService(session=MagicMock())
    crud_mock = AsyncMock(return_value=rows)
    monkeypatch.setattr("app.services.chat_service.crud_chat.get_recent_messages", crud_mock)

    history = await svc._load_history(1, _bot(window=2), "새로운 질문")

    # limit은 window+1로 조회
    assert crud_mock.await_args.kwargs["limit"] == 3
    assert history == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]


@pytest.mark.asyncio
async def test_load_history_truncates_long_messages(monkeypatch):
    rows = [_msg(MessageRole.ASSISTANT, "가" * 30)]
    svc = ChatService(session=MagicMock())
    monkeypatch.setattr(
        "app.services.chat_service.crud_chat.get_recent_messages",
        AsyncMock(return_value=rows),
    )
    monkeypatch.setattr(
        "app.services.chat_service.get_settings",
        lambda: SimpleNamespace(CHAT_HISTORY_MAX_CHARS_PER_MESSAGE=10),
    )

    history = await svc._load_history(1, _bot(window=4), "질문")

    assert history[0]["content"] == "가" * 10 + " …(이하 생략)"


# --- Gemini contents 직렬화 ---


def test_build_gemini_contents_without_history_returns_prompt_str():
    # 히스토리 없으면 기존 단일턴과 동일한 str — stateless 회귀 0 보장
    assert build_gemini_contents("질문", None) == "질문"
    assert build_gemini_contents("질문", []) == "질문"


def test_build_gemini_contents_with_history_builds_multiturn():
    history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    contents = build_gemini_contents("q2", history)

    assert isinstance(contents, list)
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[-1].parts[0].text == "q2"
    assert contents[1].parts[0].text == "a1"


# --- OpenAI messages 순서 ---


@pytest.mark.asyncio
async def test_openai_generate_prepends_history():
    from app.services.llm.openai import OpenAIService

    svc = OpenAIService.__new__(OpenAIService)  # API 키 검증 없이 구성
    svc._model_name = "gpt-4o"

    captured = {}

    async def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        resp = MagicMock()
        resp.choices[0].message.content = "답변"
        return resp

    svc._client = MagicMock()
    svc._client.chat.completions.create = AsyncMock(side_effect=fake_create)

    history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    await svc.generate(prompt="q2", system_prompt="sp", history=history)

    assert captured["messages"] == [
        {"role": "system", "content": "sp"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]


# --- Gemini RAG: 히스토리 전달 시에도 FileSearch tool 유지 ---


@pytest.mark.asyncio
async def test_gemini_rag_history_keeps_file_search_tool(monkeypatch):
    import app.services.llm.gemini as llm_gemini

    monkeypatch.setattr(llm_gemini, "_get_genai_client", lambda: MagicMock())
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    monkeypatch.setattr(svc, "ensure_store", AsyncMock(return_value="fileSearchStores/test"))

    captured = {}

    async def fake_generate_content(model, contents, config):
        captured["contents"] = contents
        captured["config"] = config
        resp = MagicMock()
        resp.text = "본문"
        resp.candidates = []
        resp.prompt_feedback = None  # MagicMock truthy 가 차단 감지(raise_if_blocked)에 오탐되지 않도록
        return resp

    svc._client = MagicMock()
    svc._client.aio.models.generate_content = AsyncMock(side_effect=fake_generate_content)

    history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    await svc.generate_with_rag(bot_id=3, prompt="q2", system_prompt="sp", history=history)

    # 멀티턴 contents 리스트로 전달되면서도 FileSearch tool 설정은 그대로 유지
    assert isinstance(captured["contents"], list)
    assert len(captured["contents"]) == 3
    assert captured["config"].tools[0].file_search.metadata_filter == "bot_id = 3"
