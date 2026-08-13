"""봇별 근거 조달 방식(`retrieval_mode`) — 세 분기와 **기본값 봇의 무변화**.

가장 중요한 것은 `test_기본값_봇은_기존_호출을_그대로_한다` 다.
지시서의 판정 기준이 "retrieval_mode 미설정 봇은 지금과 한 글자도 다르면 안 된다" 인데,
Gemini 하루 쿼터가 소진돼 실제 응답으로는 확인할 수 없었다. 대신 `generate_with_rag` 에
넘어가는 인자를 통째로 비교해 같은 호출임을 증명한다.
"""

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
from app.services.chat_service import ChatService, _effective_retrieval_mode


def _bot(**kw) -> Bot:
    kw.setdefault("llm_model", "gemini-3.5-flash-lite")
    bot = Bot(name="축복 챗봇", description="test", **kw)
    bot.id = 11
    return bot


def _session_mock():
    session = MagicMock()
    session.commit = AsyncMock()
    return session


def _chat_session() -> ChatSession:
    s = ChatSession(user_id=1, bot_id=11)
    s.id = 9
    return s


def _rag_response(answer="원문에 따르면 그렇습니다."):
    return RAGResponse(
        answer=answer,
        citations=[RAGCitation(title="규정집v20 제33조", content="제 33 조 …", uri="reg-33")],
        followups=["다음 질문"],
    )


def _patch_common(monkeypatch, rag_service):
    monkeypatch.setattr(chat_service.crud_chat, "create_message",
                        AsyncMock(return_value=SimpleNamespace(id=5)))
    monkeypatch.setattr(chat_service, "search_faq_override", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_service, "get_rag_service", lambda provider=None: rag_service)
    monkeypatch.setattr(chat_service, "load_runtime_facts", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_service, "build_prompt_overlay", lambda facts: "")
    monkeypatch.setattr(chat_service, "term_rules", lambda facts: [])
    monkeypatch.setattr(chat_service, "_schedule_evidence_fill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_schedule_citation_backfill", lambda **kw: None)
    # 「답변 못 함」 기록·shadow 판정. 여기 안 걸면 DB MagicMock 과 Gemini 호출이
    # 실제로 돌아 조용히 예외로 삼켜진다 — 이 파일은 조달 분기만 재는 자리다.
    monkeypatch.setattr(chat_service, "_record_unanswered", AsyncMock(return_value=None))


async def _run(bot, monkeypatch, stream=False):
    rag_service = SimpleNamespace(generate_with_rag=AsyncMock(return_value=_rag_response()))
    _patch_common(monkeypatch, rag_service)
    resp = await ChatService(_session_mock()).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="금식은 며칠인가요?", use_rag=True, stream=stream),
        bot,
        _chat_session(),
    )
    return resp, rag_service


# ---- 스키마 -----------------------------------------------------------------

def test_retrieval_mode_는_정해진_값만_받는다():
    assert BotUpdateRequest(retrieval_mode="lexical").retrieval_mode == "lexical"
    assert BotUpdateRequest(retrieval_mode="both").retrieval_mode == "both"
    assert BotUpdateRequest(retrieval_mode="file_search").retrieval_mode == "file_search"
    with pytest.raises(ValidationError):
        BotUpdateRequest(retrieval_mode="bm25")


def test_모델_기본값은_file_search():
    assert Bot(name="a", description="b").retrieval_mode == "file_search"


# ---- 폴백 규칙 ---------------------------------------------------------------

def test_비_gemini_봇은_file_search_로_폴백한다():
    assert _effective_retrieval_mode(
        _bot(retrieval_mode="lexical", llm_model="gpt-4o-mini")) == "file_search"
    assert _effective_retrieval_mode(
        _bot(retrieval_mode="lexical", llm_model="gemini-3.5-flash-lite")) == "lexical"


def test_알_수_없는_값은_file_search_로_처리한다():
    bot = _bot()
    bot.retrieval_mode = "bm25"
    assert _effective_retrieval_mode(bot) == "file_search"


def test_컬럼이_없는_옛_객체도_file_search_다():
    assert _effective_retrieval_mode(SimpleNamespace(id=1, llm_model="gemini-x")) == "file_search"


# ---- ★ 회귀: 기본값 봇의 무변화 ------------------------------------------------

@pytest.mark.asyncio
async def test_기본값_봇은_기존_호출을_그대로_한다(monkeypatch):
    """`generate_with_rag` 에 넘어가는 인자가 변경 전과 완전히 같아야 한다."""
    resp, rag_service = await _run(_bot(), monkeypatch)

    rag_service.generate_with_rag.assert_awaited_once_with(
        bot_id=11,
        prompt="금식은 며칠인가요?",
        system_prompt="",
        model_name="gemini-3.5-flash-lite",
        history=None,
    )
    assert resp.source == "rag"
    assert resp.content == "원문에 따르면 그렇습니다."
    assert resp.followups == ["다음 질문"]


@pytest.mark.asyncio
async def test_기본값_봇은_stream_true_면_스트리밍으로_간다(monkeypatch):
    """비스트리밍 강제는 lexical/both 에만 걸린다. file_search 는 예전 그대로다."""
    resp, rag_service = await _run(_bot(), monkeypatch, stream=True)
    assert resp.__class__.__name__ == "StreamingResponse"
    rag_service.generate_with_rag.assert_not_awaited()


# ---- 세 분기가 각기 다른 조달을 탄다 -------------------------------------------

@pytest.mark.asyncio
async def test_lexical_은_file_search_를_부르지_않는다(monkeypatch):
    called = {}

    async def fake_wiki(**kw):
        called.update(kw)
        return _rag_response("어휘 검색 답변"), None

    monkeypatch.setattr(
        "app.services.wiki.service.answer_with_wiki", fake_wiki, raising=True)
    resp, rag_service = await _run(_bot(retrieval_mode="lexical"), monkeypatch)

    rag_service.generate_with_rag.assert_not_awaited()
    assert called["context_mode"] == "raw_budget"
    assert called["bot_id"] == 11
    assert resp.content == "어휘 검색 답변"


@pytest.mark.asyncio
async def test_lexical_은_stream_요청이어도_비스트리밍으로_답한다(monkeypatch):
    async def fake_wiki(**kw):
        return _rag_response("어휘 검색 답변"), None

    monkeypatch.setattr(
        "app.services.wiki.service.answer_with_wiki", fake_wiki, raising=True)
    resp, _ = await _run(_bot(retrieval_mode="lexical"), monkeypatch, stream=True)
    assert resp.__class__.__name__ == "ChatCompletionResponse"
    assert resp.content == "어휘 검색 답변"


# ---- 폴백: 코퍼스가 없거나 빈손일 때 사용자에게 고장이 보이면 안 된다 ----------------

@pytest.mark.asyncio
async def test_코퍼스가_없으면_file_search_로_되돌린다(monkeypatch):
    """배포 이미지엔 exports/ 가 없다. 예외가 새면 사용자에게 500 이 나간다."""
    from app.services.wiki.store import WikiCorpusUnavailable

    async def boom(**kw):
        raise WikiCorpusUnavailable("원문 없음")

    monkeypatch.setattr("app.services.wiki.service.answer_with_wiki", boom, raising=True)
    resp, rag_service = await _run(_bot(retrieval_mode="lexical"), monkeypatch)

    rag_service.generate_with_rag.assert_awaited_once()
    assert resp.content == "원문에 따르면 그렇습니다."


@pytest.mark.asyncio
async def test_어휘검색이_빈손이면_file_search_로_되돌린다(monkeypatch):
    """어휘 검색은 동의어·구어체 질문에서 빈손이 된다(핸드오프 §5 #13).
    빈 답변을 그대로 내보내면 사용자에게는 그냥 고장이다."""

    async def empty(**kw):
        return RAGResponse(answer="   ", citations=[], followups=[]), None

    monkeypatch.setattr("app.services.wiki.service.answer_with_wiki", empty, raising=True)
    resp, rag_service = await _run(_bot(retrieval_mode="lexical"), monkeypatch)

    rag_service.generate_with_rag.assert_awaited_once()
    assert resp.content == "원문에 따르면 그렇습니다."


@pytest.mark.asyncio
async def test_both_은_코퍼스가_없어도_file_search_로_답한다(monkeypatch):
    from app.services.wiki.store import WikiCorpusUnavailable

    async def boom(bot_id, question, top_k=3):
        raise WikiCorpusUnavailable("원문 없음")

    monkeypatch.setattr("app.services.wiki.service.build_hybrid_turns", boom, raising=True)
    resp, rag_service = await _run(_bot(retrieval_mode="both"), monkeypatch)

    assert rag_service.generate_with_rag.await_args.kwargs["history"] is None
    assert resp.content == "원문에 따르면 그렇습니다."


@pytest.mark.asyncio
async def test_both_은_원문을_앞선_턴으로_얹어_file_search_를_부른다(monkeypatch):
    turns = [
        {"role": "user", "content": "# 참고 규정 원문\n[reg-33] …"},
        {"role": "assistant", "content": "확인했습니다. 질문해 주세요."},
    ]

    async def fake_turns(bot_id, question, top_k=3):
        return turns

    monkeypatch.setattr(
        "app.services.wiki.service.build_hybrid_turns", fake_turns, raising=True)
    _, rag_service = await _run(_bot(retrieval_mode="both"), monkeypatch)

    kwargs = rag_service.generate_with_rag.await_args.kwargs
    assert kwargs["history"] == turns
    assert kwargs["prompt"] == "금식은 며칠인가요?"


@pytest.mark.asyncio
async def test_both_은_기존_대화기록_앞에_원문을_둔다(monkeypatch):
    """원문이 뒤에 붙으면 직전 턴이 아니게 되고, 앞에 붙어야 질의 오염도 없다."""
    turns = [{"role": "user", "content": "# 참고 규정 원문\n[reg-33] …"},
             {"role": "assistant", "content": "확인했습니다. 질문해 주세요."}]
    history = [{"role": "user", "content": "이전 질문"},
               {"role": "assistant", "content": "이전 답변"}]

    async def fake_turns(bot_id, question, top_k=3):
        return turns

    monkeypatch.setattr(
        "app.services.wiki.service.build_hybrid_turns", fake_turns, raising=True)
    rag_service = SimpleNamespace(generate_with_rag=AsyncMock(return_value=_rag_response()))
    _patch_common(monkeypatch, rag_service)
    monkeypatch.setattr(ChatService, "_load_history", AsyncMock(return_value=history))

    await ChatService(_session_mock()).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="금식은?", use_rag=True, stream=False),
        _bot(retrieval_mode="both"),
        _chat_session(),
    )
    assert rag_service.generate_with_rag.await_args.kwargs["history"] == turns + history
