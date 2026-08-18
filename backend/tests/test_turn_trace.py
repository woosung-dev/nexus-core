"""턴 trace — 관리자에게는 다 남기고, 사용자에게는 한 글자도 안 나간다.

이 파일이 지키는 계약은 셋이다.

1. **사용자 응답에 trace 가 없다.** 기계 id 가 화면에 새어 나간 전례가 있어(#63)
   「안 넣었으니 됐다」로 두지 않는다. 스키마에 필드가 없다는 것까지 검증한다.
2. **여덟 단계가 순서대로 남는다.** 무엇을 보고 무엇을 정했는지가 단계마다 있어야
   「유보율」과 「과잉 거절」을 사후에 가를 수 있다.
3. **원문은 안 남는다.** 주입 원문은 건당 3,000자까지 가고, 그게 매 턴 박히면
   관리자 화면이 먼저 죽는다. 참조(`src_id:locator`)만 남긴다.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.bot import Bot
from app.models.chat import ChatSession
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.schemas.rag import RAGCitation, RAGResponse
from app.services import chat_service
from app.services.chat_service import ChatService
from app.services.turn_trace import MAX_LIST, TurnTrace, prompt_sha8, unit_refs


def _bot(**kw) -> Bot:
    kw.setdefault("llm_model", "gemini-3.5-flash-lite")
    bot = Bot(name="축복 챗봇", description="test", **kw)
    bot.id = 11
    return bot


def _chat_session() -> ChatSession:
    s = ChatSession(user_id=1, bot_id=11)
    s.id = 9
    return s


def _rag_response(answer="제55조에 따르면 그렇습니다."):
    return RAGResponse(
        answer=answer,
        citations=[RAGCitation(title="규정집v20 제55조", content="제 55 조 …", uri="reg-55")],
        followups=["다음 질문"],
    )


async def _run(bot, monkeypatch, *, answer="제55조에 따르면 그렇습니다.", faq=None):
    """한 턴 돌리고 (응답, 저장된 trace) 를 돌려준다."""
    saved: dict = {}
    session = MagicMock()
    session.commit = AsyncMock()

    async def capture_message(**kw):
        saved.update(kw)
        return SimpleNamespace(id=5)

    monkeypatch.setattr(chat_service.crud_chat, "create_message", capture_message)
    monkeypatch.setattr(chat_service, "search_faq_override", AsyncMock(return_value=faq))
    monkeypatch.setattr(
        chat_service, "get_rag_service",
        lambda provider=None: SimpleNamespace(
            generate_with_rag=AsyncMock(return_value=_rag_response(answer))
        ),
    )
    monkeypatch.setattr(chat_service, "load_runtime_facts", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_service, "build_prompt_overlay", lambda facts: "")
    monkeypatch.setattr(chat_service, "term_rules", lambda facts: [])
    monkeypatch.setattr(chat_service, "_schedule_evidence_fill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_schedule_citation_backfill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_record_unanswered", AsyncMock())

    resp = await ChatService(session).process_chat_request(
        ChatCompletionRequest(bot_id=11, message="축복 헌금이 얼마인가요?", use_rag=True, stream=False),
        bot,
        _chat_session(),
    )
    return resp, saved.get("trace")


# ---- 계약 1. 사용자에게 안 나간다 ---------------------------------------------


def test_사용자_응답_스키마에_trace_필드가_없다():
    """필드가 존재하면 언젠가 채워진다. 스키마 단계에서 막는다."""
    assert "trace" not in ChatCompletionResponse.model_fields


def test_사용자_메시지_스키마에도_trace_가_없다():
    """`MessageResponse` 는 사용자 API 와 관리자 API 가 **함께 쓴다.**
    여기에 얹으면 한 줄로 실행 추적이 사용자에게 나간다. 관리자용은 상속본이다."""
    from app.schemas.chat import AdminMessageResponse, MessageResponse

    assert "trace" not in MessageResponse.model_fields
    assert "trace" in AdminMessageResponse.model_fields


def test_사용자_메시지_엔드포인트가_관리자_스키마를_쓰지_않는다():
    """엔드포인트 결선까지 본다. 스키마만 갈라 두고 사용자 라우터가 관리자 스키마를
    반환하면 분리가 무의미하다."""
    from app.schemas.chat import AdminMessageResponse

    from app.api.v1.endpoints import chat as user_chat

    for route in getattr(user_chat.router, "routes", []):
        model = getattr(route, "response_model", None)
        assert model is not AdminMessageResponse, f"{route.path} 가 관리자 스키마를 쓴다"
        assert AdminMessageResponse not in getattr(model, "__args__", ()), (
            f"{route.path} 가 관리자 스키마를 리스트로 반환한다"
        )


@pytest.mark.asyncio
async def test_응답_직렬화에_trace_가_없다(monkeypatch):
    resp, trace = await _run(_bot(), monkeypatch)
    assert trace is not None, "관리자용 trace 는 저장돼야 한다"
    assert "trace" not in resp.model_dump()


# ---- 계약 2. 단계가 남는다 -----------------------------------------------------


@pytest.mark.asyncio
async def test_기본_경로가_단계를_순서대로_남긴다(monkeypatch):
    _, trace = await _run(_bot(), monkeypatch)
    names = [s["stage"] for s in trace["stages"]]
    assert names == ["faq", "ops_facts", "retrieval", "strict", "strip", "unanswered",
                     "term", "record"]
    assert trace["v"] == 1
    assert trace["total_ms"] >= 0
    assert all("ms" in s for s in trace["stages"])


@pytest.mark.asyncio
async def test_faq_가_가로채면_거기서_끝난다(monkeypatch):
    """FAQ hit 턴은 검색도 생성도 안 탄다. 그 사실이 데이터로 남아야 한다."""
    faq = SimpleNamespace(faq_id=3, answer="답변 드리기 어렵습니다.", similarity=0.97,
                          question="q")
    _, trace = await _run(_bot(), monkeypatch, faq=faq)
    names = [s["stage"] for s in trace["stages"]]
    assert names == ["faq"]
    assert trace["stages"][0]["decision"] == "faq_override"
    assert trace["stages"][0]["faq_id"] == 3


@pytest.mark.asyncio
async def test_strict_가_막으면_판정_전_표기가_남는다(monkeypatch):
    """차단되면 답변이 고정 문구로 갈린다. 무엇을 보고 막았는지는 그 전에 떠 둬야 한다."""
    bot = _bot(evidence_policy_mode="strict", retrieval_mode="file_search")
    resp, trace = await _run(bot, monkeypatch, answer="근거 없이 단정합니다.")
    strict = next(s for s in trace["stages"] if s["stage"] == "strict")
    assert strict["decision"] in ("blocked", "pass")


@pytest.mark.asyncio
async def test_설정_스냅샷이_프롬프트_지문을_남긴다(monkeypatch):
    """「이 답변이 어느 프롬프트에서 나왔나」를 되짚을 유일한 열쇠다."""
    bot = _bot()
    bot.system_prompt = "너는 축복 안내자다."
    _, trace = await _run(bot, monkeypatch)
    cfg = trace["config"]
    assert cfg["prompt_sha8"] == prompt_sha8("너는 축복 안내자다.")
    assert cfg["bot_id"] == 11
    assert cfg["model"] == "gemini-3.5-flash-lite"
    assert cfg["evidence_policy_mode"] == "legacy"


# ---- 계약 3. 원문은 안 남는다 --------------------------------------------------


def test_unit_refs_는_본문을_안_싣는다():
    units = [SimpleNamespace(src_id="reg-55", locator="제55조", text="가" * 3000)]
    assert unit_refs(units) == ["reg-55:제55조"]


def test_긴_목록은_잘리고_남은_수를_알린다():
    t = TurnTrace()
    t.stage("retrieval", "lexical", unit_refs=[f"reg-{i}" for i in range(30)])
    refs = t.stages[0]["unit_refs"]
    assert len(refs) == MAX_LIST + 1
    assert refs[-1] == f"…+{30 - MAX_LIST}"


def test_None_인_사실은_안_남는다():
    """빈 값으로 행을 불리지 않는다."""
    t = TurnTrace()
    t.stage("strict", "off", cited=None, units=None)
    assert set(t.stages[0]) == {"stage", "decision", "ms"}


@pytest.mark.asyncio
async def test_file_search_턴은_지어냄을_안_쟀다고_남긴다(monkeypatch):
    """**「지어냄 0」과 「안 쟀음」은 다르다.**

    `fabricated_citations` 는 `if not units: return set(), set()` 로 시작하고
    `trace.units` 는 어휘 분기에서만 채워진다 → file_search·both·폴백 턴은 언제나
    0으로 찍힌다. 그걸 0으로 읽어 「이 경로는 안전하다」고 집계한 적이 있다.
    무보호가 아니라 **무측정**이라는 것이 데이터에 남아야 한다.
    """
    bot = _bot(evidence_policy_mode="strict", retrieval_mode="file_search")
    _, trace = await _run(bot, monkeypatch, answer="제99조에 따르면 그렇습니다.")
    strict = next(s for s in trace["stages"] if s["stage"] == "strict")

    assert strict["fabricated_checked"] is False
    # 안 쟀으므로 「지어냄 없음」으로도 적으면 안 된다 (None 은 기록에서 빠진다).
    assert "fabricated" not in strict
    assert "fabricated_loc" not in strict
