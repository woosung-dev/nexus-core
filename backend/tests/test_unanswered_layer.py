"""「답변 못 함」 3층 — 출력의 결정론과 기록의 관대함.

이 파일이 지키는 계약은 둘이다.

1. **사용자에게 문구가 나가는 조건은 「최종 답변이 빈 문자열」 하나뿐이다.**
   봇이 스스로 거절했을 때는 답변을 **건드리지 않는다** — 프롬프트가 시킨 그 문구가 맞다.
2. **폴백은 없어지지 않는다.** 어휘 검색이 빈손이거나 코퍼스가 없으면 file_search 로
   되돌아가고, 그 사실만 기록된다.

집계 SQL(`crud_unanswered.aggregate`)은 여기서 안 잰다 — 이 레포의 테스트는 DB 를
MagicMock 으로 대체하는 규약이라 윈도우 함수를 태울 수 없다. 로컬 Postgres 로 따로 확인했다.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.bot import Bot
from app.models.chat import ChatSession
from app.schemas.chat import ChatCompletionRequest
from app.schemas.rag import RAGCitation, RAGResponse
from app.services import chat_service
from app.services.chat_service import ChatService
from app.services.unanswered import (
    UNANSWERED_MESSAGE,
    Reason,
    RetrievalTrace,
    Triage,
    is_self_refusal,
    normalize_question,
)


def _bot(**kw) -> Bot:
    kw.setdefault("llm_model", "gemini-3.5-flash-lite")
    bot = Bot(name="축복 챗봇", description="test", **kw)
    bot.id = 11
    return bot


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


def _patch_common(monkeypatch, rag_service, recorded: list):
    session = MagicMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(chat_service.crud_chat, "create_message",
                        AsyncMock(return_value=SimpleNamespace(id=5)))
    monkeypatch.setattr(chat_service, "search_faq_override", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_service, "get_rag_service", lambda provider=None: rag_service)
    monkeypatch.setattr(chat_service, "load_runtime_facts", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_service, "build_prompt_overlay", lambda facts: "")
    monkeypatch.setattr(chat_service, "term_rules", lambda facts: [])
    monkeypatch.setattr(chat_service, "_schedule_evidence_fill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_schedule_citation_backfill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_schedule_answerability_judge", lambda **kw: None)

    async def capture(_session, **kw):
        recorded.append(kw)

    monkeypatch.setattr(chat_service, "_record_unanswered", capture)
    return session


async def _run(bot, monkeypatch, *, wiki=None, rag_answer="원문에 따르면 그렇습니다."):
    """한 턴 돌리고 (응답, 기록된 신호 목록) 을 돌려준다."""
    recorded: list[dict] = []
    rag_service = SimpleNamespace(
        generate_with_rag=AsyncMock(return_value=_rag_response(rag_answer))
    )
    session = _patch_common(monkeypatch, rag_service, recorded)
    if wiki is not None:
        monkeypatch.setattr("app.services.wiki.service.answer_with_wiki", wiki, raising=True)

    resp = await ChatService(session).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="축복 헌금이 얼마인가요?", use_rag=True, stream=False),
        bot,
        _chat_session(),
    )
    reasons = [r for kw in recorded for r in kw["reasons"]]
    return resp, reasons, rag_service


# ---- 순수 함수 ---------------------------------------------------------------

def test_정규화는_공백과_문장부호를_무시한다():
    """이게 성립해야 빈도순 화면이 성립한다.

    라이브 실측에서 사용자 메시지 2,268건 중 74%가 이 정규화 후 정확히 중복이다.
    """
    a = normalize_question("축복 헌금 금액이 얼마인가요?")
    assert a == normalize_question("축복헌금 금액이 얼마인가요")
    assert a == normalize_question("  축복 헌금  금액이, 얼마인가요!! ")
    assert a != normalize_question("축복 헌금 언제 내나요?")


def test_정규화는_전각과_대소문자를_통일한다():
    assert normalize_question("Ｂ４Ｕ 등록") == normalize_question("b4u등록")


def test_빈_질문은_빈_키가_된다():
    assert normalize_question("") == ""
    assert normalize_question("   ?? ") == ""


def test_자기_거절_판정은_라이브_실제_문구를_잡는다():
    """**시스템 프롬프트가 시키는 문구**를 잡아야 한다 — 관리자가 쓴 FAQ 거절문이 아니라.

    라이브 봇 11 프롬프트 1번 항목이 *"규정집에 없으면 확인되지 않습니다"* 다.
    `strict_mode._REFUSAL_RE` 를 재사용했다가 이 문구를 통째로 놓쳤다(2,268건 중 14건만 매칭).
    아래 문장들은 라이브 DB 에서 그대로 가져온 모양이다.
    """
    assert is_self_refusal("해당 내용은 규정집에서 확인되지 않습니다. 가정행복국으로 문의해 주세요.")
    assert is_self_refusal("청평 40일 수련을 대체할 수 있다는 내용은 확인되지 않습니다.")
    assert is_self_refusal("해당 질문은 답변할수 없는 항목입니다..")
    assert is_self_refusal("상세 절차까지는 안내해 드릴 수 없습니다.")
    assert is_self_refusal("상세한 내용을 바로 안내해 드리지 못해 마음이 무겁습니다.")


def test_자기_거절_판정은_격려문을_거절로_읽지_않는다():
    """`_REFUSAL_RE` 의 실제 거짓양성. `.{0,16}` 이 문장을 건너뛰어 생긴 것이라
    새 패턴은 `[^.]{0,N}` 로 문장 경계를 막는다."""
    assert not is_self_refusal(
        "신앙적 안내자 역할을 해주시는 것이니, 너무 어렵게 생각하지 마시고 편히 여쭤보세요."
    )
    assert not is_self_refusal("규정집 제33조에 따르면 3일 기도가 필요합니다.")


def test_trace_는_같은_이유를_두_번_담지_않는다():
    trace = RetrievalTrace()
    trace.mark(Reason.LEXICAL_EMPTY)
    trace.mark(Reason.LEXICAL_EMPTY)
    assert trace.reasons == [Reason.LEXICAL_EMPTY]


def test_처리경로에_문서오류만_ops_facts_로_간다():
    """`ops_facts` 는 문서를 못 고칠 때 쓰는 덮개다. 나머지 셋은 다른 트랙의 일이다."""
    assert Triage.DOC_WRONG == "문서오류"
    assert {Triage.NO_DOC, Triage.NOT_FOUND, Triage.NOT_APPLICABLE} != {Triage.DOC_WRONG}


# ---- 1층: 출력은 결정론이다 ----------------------------------------------------

@pytest.mark.asyncio
async def test_빈_답변은_고정_문구로_치환된다(monkeypatch):
    """지금은 빈 말풍선이 그대로 나간다. 그건 사용자에게 그냥 고장이다."""
    resp, reasons, _ = await _run(_bot(), monkeypatch, rag_answer="   ")

    assert resp.content == UNANSWERED_MESSAGE
    assert resp.citations == []
    assert resp.followups == []
    assert Reason.EMPTY_ANSWER in reasons


@pytest.mark.asyncio
async def test_고정_문구는_프롬프트가_아니라_상수다():
    """문구가 흔들리지 않는 유일한 방법이다. 연락처는 라이브 봇 11 프롬프트와 같아야 한다."""
    assert "02-3271-0502" in UNANSWERED_MESSAGE
    assert "정리되지 않은" in UNANSWERED_MESSAGE
    # 「학습」은 AI 모델 학습으로 오해될 수 있어 배제한 표현이다.
    assert "학습" not in UNANSWERED_MESSAGE


@pytest.mark.asyncio
async def test_봇이_스스로_거절하면_답변을_건드리지_않는다(monkeypatch):
    """프롬프트가 시킨 그 문구가 맞다. 기록만 남긴다 — 과잉 거절을 만들지 않는다."""
    refusal = "해당 내용은 규정집에서 확인되지 않습니다. 가정행복국(02-3271-0502)으로 문의해 주세요."
    resp, reasons, _ = await _run(_bot(), monkeypatch, rag_answer=refusal)

    assert resp.content == refusal
    assert resp.content != UNANSWERED_MESSAGE
    assert Reason.SELF_REFUSAL in reasons


@pytest.mark.asyncio
async def test_정상_답변은_아무것도_기록하지_않는다(monkeypatch):
    resp, reasons, _ = await _run(_bot(), monkeypatch)
    assert resp.content == "원문에 따르면 그렇습니다."
    assert reasons == []


# ---- 폴백은 살아 있다. 사실만 기록한다 -------------------------------------------

@pytest.mark.asyncio
async def test_어휘_빈손은_폴백하고_기록만_한다(monkeypatch):
    async def empty(**kw):
        return RAGResponse(answer="   ", citations=[], followups=[]), None

    resp, reasons, rag_service = await _run(
        _bot(retrieval_mode="lexical"), monkeypatch, wiki=empty
    )

    # 폴백이 살아 있다 — 사용자는 정상 답변을 받는다
    rag_service.generate_with_rag.assert_awaited_once()
    assert resp.content == "원문에 따르면 그렇습니다."
    # 그리고 그 사실이 데이터로 남는다
    assert Reason.LEXICAL_EMPTY in reasons
    assert Reason.EMPTY_ANSWER not in reasons


@pytest.mark.asyncio
async def test_코퍼스_없음도_폴백하고_기록만_한다(monkeypatch):
    from app.services.wiki.store import WikiCorpusUnavailable

    async def boom(**kw):
        raise WikiCorpusUnavailable("원문 없음")

    resp, reasons, rag_service = await _run(
        _bot(retrieval_mode="lexical"), monkeypatch, wiki=boom
    )

    rag_service.generate_with_rag.assert_awaited_once()
    assert resp.content == "원문에 따르면 그렇습니다."
    assert Reason.CORPUS_UNAVAILABLE in reasons


@pytest.mark.asyncio
async def test_어휘가_답하면_폴백도_기록도_없다(monkeypatch):
    async def ok(**kw):
        return _rag_response("어휘 검색 답변"), None

    resp, reasons, rag_service = await _run(
        _bot(retrieval_mode="lexical"), monkeypatch, wiki=ok
    )

    rag_service.generate_with_rag.assert_not_awaited()
    assert resp.content == "어휘 검색 답변"
    assert reasons == []


# ---- 2층은 사용자 답변을 건드리지 않는다 ------------------------------------------

@pytest.mark.asyncio
async def test_shadow_판정은_주입_원문이_없으면_모델을_안_부른다(monkeypatch):
    """`units` 가 비면 판정할 원문이 없다. Gemini 호출을 아끼고 조용히 통과한다."""
    called = []
    monkeypatch.setattr(
        chat_service, "_judge_answerability_async",
        lambda *a, **kw: called.append(a),
    )
    chat_service._schedule_answerability_judge(
        bot_id=11, model_name="gemini-3.5-flash-lite", message_id=5,
        session_id=9, question="질문", units=[],
    )
    assert called == []


@pytest.mark.asyncio
async def test_shadow_판정_실패는_답변을_막지_않는다(monkeypatch):
    """판정기가 고장 나서 제품이 벙어리가 되는 쪽이 더 나쁘다 — fail-open."""
    async def boom(**kw):
        raise RuntimeError("판정기 고장")

    monkeypatch.setattr(
        "app.services.clarification_trigger.judge_answerability", boom, raising=True
    )
    # 예외가 밖으로 새지 않는다
    await chat_service._judge_answerability_async(
        11, "gemini-3.5-flash-lite", 5, 9, "질문", [SimpleNamespace(src_id="reg-33")]
    )


# ---- 기록이 실패해도 답변은 살아야 한다 -------------------------------------------

@pytest.mark.asyncio
async def test_기록이_DB오류를_내도_바깥_트랜잭션은_살아_있다():
    """**`try/except` 만으로는 이게 안 된다.**

    DB 오류가 나면 파이썬 예외는 잡히지만 트랜잭션이 오염된 채로 남아 호출자의
    `commit()` 이 `PendingRollbackError` 로 죽는다. 그러면 어시스턴트 메시지까지
    통째로 날아가 사용자는 500 을 받는다 — 기록하려다 답변을 잃는 정반대 결과다.
    실제 Postgres 로 재현했고, SAVEPOINT 로 고쳤다.

    여기서는 `begin_nested()` 가 **실제로 호출되는지**와 실패가 밖으로 안 새는지를 잰다.
    """
    entered = {"n": 0}

    class _Savepoint:
        async def __aenter__(self):
            entered["n"] += 1
            return self

        async def __aexit__(self, *exc):
            # 실패를 SAVEPOINT 까지만 되감고 삼키지는 않는다(바깥 except 가 받는다).
            return False

    session = MagicMock()
    session.begin_nested = lambda: _Savepoint()
    session.add = MagicMock(side_effect=RuntimeError("insert 실패"))

    # 예외가 밖으로 새지 않는다
    await chat_service._record_unanswered(
        session,
        bot=SimpleNamespace(id=11),
        chat_session=SimpleNamespace(id=9),
        message_id=5,
        question="축복 헌금이 얼마인가요?",
        reasons=[Reason.SELF_REFUSAL],
    )
    assert entered["n"] == 1, "SAVEPOINT 없이 쓰면 바깥 트랜잭션이 오염된다"


@pytest.mark.asyncio
async def test_신호가_없으면_기록_자체를_시도하지_않는다():
    """정상 답변이 대부분이다. 빈 SAVEPOINT 왕복을 만들지 않는다."""
    session = MagicMock()
    session.begin_nested = MagicMock(side_effect=AssertionError("불려선 안 된다"))

    await chat_service._record_unanswered(
        session,
        bot=SimpleNamespace(id=11),
        chat_session=SimpleNamespace(id=9),
        message_id=5,
        question="축복 헌금이 얼마인가요?",
        reasons=[],
    )
