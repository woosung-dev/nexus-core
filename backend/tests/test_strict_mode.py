from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.models.bot import Bot
from app.models.chat import ChatSession
from app.schemas.bot import BotUpdateRequest
from app.schemas.chat import ChatCompletionRequest
from app.schemas.rag import RAGCitation, RAGResponse
from app.services import chat_service
from app.services.chat_service import ChatService
from app.services.strict_mode import (
    STRICT_EVIDENCE_MESSAGE,
    has_direct_citation,
    is_refusal_faq,
)


def test_strict_mode_accepts_only_supported_values():
    assert BotUpdateRequest(evidence_policy_mode="strict").evidence_policy_mode == "strict"
    with pytest.raises(ValidationError):
        BotUpdateRequest(evidence_policy_mode="strict-v5")


def test_direct_citation_and_refusal_faq_rules():
    assert has_direct_citation([RAGCitation(title="공식 자료")])
    assert not has_direct_citation([RAGCitation(title="재검색", approximate=True)])
    assert is_refusal_faq("이 항목은 답변할 수 없습니다.")
    assert is_refusal_faq("이 항목은 안내해 드릴 수 없습니다.")
    assert not is_refusal_faq("절차는 세 단계입니다.")


def _strict_bot() -> Bot:
    bot = Bot(name="축복 챗봇", description="test", evidence_policy_mode="strict")
    bot.id = 11
    return bot


def _chat_session() -> ChatSession:
    session = ChatSession(user_id=1, bot_id=11)
    session.id = 9
    return session


@pytest.mark.asyncio
async def test_strict_faq_allows_only_refusal_message(monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(chat_service.crud_chat, "create_message", AsyncMock())
    monkeypatch.setattr(
        chat_service,
        "search_faq_override",
        AsyncMock(return_value=SimpleNamespace(answer="이 항목은 답변할 수 없습니다.", faq_id=1, similarity=0.99)),
    )

    response = await ChatService(session).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="금지 항목", use_rag=True, stream=False),
        _strict_bot(),
        _chat_session(),
    )

    assert response.source == "faq_override"
    assert response.content == "이 항목은 답변할 수 없습니다."


@pytest.mark.asyncio
async def test_strict_faq_blocks_non_refusal_answer(monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(chat_service.crud_chat, "create_message", AsyncMock())
    monkeypatch.setattr(
        chat_service,
        "search_faq_override",
        AsyncMock(return_value=SimpleNamespace(answer="절차는 세 단계입니다.", faq_id=1, similarity=0.99)),
    )

    response = await ChatService(session).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="절차", use_rag=True, stream=False),
        _strict_bot(),
        _chat_session(),
    )

    assert response.source == "policy_block"
    assert response.content == STRICT_EVIDENCE_MESSAGE


@pytest.mark.asyncio
async def test_strict_rag_blocks_answer_without_direct_citation(monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()
    rag = MagicMock()
    rag.generate_with_rag = AsyncMock(
        return_value=RAGResponse(answer="근거 없는 답", citations=[])
    )
    monkeypatch.setattr(chat_service.crud_chat, "create_message", AsyncMock(return_value=SimpleNamespace(id=1)))
    monkeypatch.setattr(chat_service, "search_faq_override", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_service, "get_rag_service", MagicMock(return_value=rag))
    monkeypatch.setattr(ChatService, "_load_history", AsyncMock(return_value=[]))

    response = await ChatService(session).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="절차", use_rag=True, stream=False),
        _strict_bot(),
        _chat_session(),
    )

    assert response.content == STRICT_EVIDENCE_MESSAGE
    assert response.citations == []
