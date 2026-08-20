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
    cited_ids,
    has_direct_citation,
    has_grounded_citation,
    is_refusal_faq,
)
from app.services.unanswered import Reason, RetrievalTrace, is_self_refusal
from app.services.wiki.store import SourceUnit


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


# ── 어휘 경로 게이트 ────────────────────────────────────────────────────────
# 문자열은 전부 봇 29(라이브 D-1 ver2 복제본) 실측 답변에서 그대로 가져왔다.
# 지어낸 예시로 재면 실제로 나오지 않는 형식만 통과시키게 된다.

_UNITS = [
    SourceUnit(src_id="reg-55", doc="규정집v20", locator="제55조(축복 관련 공과금)", text="…"),
    SourceUnit(src_id="reg-56", doc="규정집v20", locator="제56조(가정회비)", text="…"),
    SourceUnit(src_id="glo-2", doc="대사전v4", locator="행정 2 가정출발", text="…"),
]


def test_cited_ids_reads_both_marker_shapes():
    assert cited_ids("금식은 3일입니다 [[src: reg-17]].") == {"reg-17"}
    assert cited_ids("[[src: reg-3, glo-132]]") == {"reg-3", "glo-132"}
    # 마커 밖에 맨몸으로 쓴 것도 인용으로 친다 — 게이트를 관대하게 잡아야 과잉 거절이 준다
    assert cited_ids("reg-25 ⑤ 에 따르면") == {"reg-25"}
    assert cited_ids("근거 없이 단언하는 문장.") == set()


def test_grounded_citation_accepts_src_id_and_article_number():
    # ① src_id 마커
    assert has_grounded_citation("가정회비는 월 15,000원입니다 [[src: reg-56]].", _UNITS)
    # ② 사람이 읽는 조문 형식 — 이것을 받는 것이 과잉 거절 22.5% → 5.0% 의 차이다
    assert has_grounded_citation(
        "가정기금 30,000원, 가정회비 월 15,000원입니다. [근거: 규정집v20 제55조, 제56조]",
        _UNITS,
    )
    # ③ 0 채움. 모델은 「행정 002」로 쓰는데 locator 는 「행정 2」다
    assert has_grounded_citation("[근거: 대사전 행정 002]", _UNITS)


def test_grounded_citation_rejects_unsupported_answers():
    assert not has_grounded_citation("절차는 세 단계입니다.", _UNITS)
    # 주입하지 않은 조문을 댔다 — 대조가 하는 일이 이것이다
    assert not has_grounded_citation("[근거: 규정집v20 제99조]", _UNITS)
    assert not has_grounded_citation("[[src: reg-99]]", _UNITS)
    # 주입 목록이 비면 대조할 것이 없다
    assert not has_grounded_citation("[[src: reg-55]]", [])


def test_fabricated_citations_catches_invented_sources():
    """`has_grounded_citation` 이 못 보는 실패. 110셀 실측에서 26건 중 18건이 새어 나갔다."""
    from app.services.strict_mode import fabricated_citations

    # 맞는 근거 하나에 가짜 하나를 얹었다 — 기존 자는 이것을 통과시킨다
    ids, loc = fabricated_citations("[[src: reg-56, reg-99]]", _UNITS)
    assert ids == {"reg-99"} and not loc
    # 조문 형식으로 지어냈다
    ids, loc = fabricated_citations("[근거: 규정집v20 제55조, 제99조]", _UNITS)
    assert not ids and loc == {("조", 99)}
    # 전부 진짜면 빈 값
    assert fabricated_citations("[근거: 규정집v20 제55조]", _UNITS) == (set(), set())
    # 주입 목록이 없으면 대조 불가 — 지어냈다고 단정하지 않는다
    assert fabricated_citations("[근거: 제99조]", []) == (set(), set())


def test_evidence_ok_requires_both_conditions():
    """① 주입 근거를 짚었고 ② 지어낸 것이 없어야 통과. 2026-08-14 실측 결정."""
    from app.services.strict_mode import evidence_ok

    assert evidence_ok("가정회비는 월 15,000원입니다 [[src: reg-56]].", _UNITS)
    # ② 위반 — 맞는 근거가 있어도 가짜가 섞이면 막는다
    assert not evidence_ok("[[src: reg-56]] 그리고 [[src: reg-99]] 에 따르면", _UNITS)
    # ① 위반
    assert not evidence_ok("절차는 세 단계입니다.", _UNITS)


def test_gate_regression_from_2026_08_14_measurement():
    """실측 두 사례를 회귀로 박는다. 이 판정이 바뀌면 결정 근거가 무너진다.

    출처: `exports/regression/_e2e_s1_lex_0813.json` · 봇 29 · 55문항 × 2회.
    """
    from app.services.strict_mode import evidence_ok

    # 사례 1 (문항#30 · 40일 성별) — 주입은 reg-72·73·41 인데 제32조를 인용문까지 붙여 지어냈다
    units_30 = [
        SourceUnit(src_id="reg-72", doc="규정집v20", locator="제72조(가정출발)", text=""),
        SourceUnit(src_id="reg-41", doc="규정집v20", locator="제41조(성별기간)", text=""),
    ]
    ans_30 = ("성별 실패나 위반이 발생한 경우에는 즉시 소속 교회장에게 보고하여 지도를 받아야 합니다. "
              "[근거: 규정집 v20 제32조]")
    assert not evidence_ok(ans_30, units_30), "지어낸 조문은 막아야 한다"

    # 사례 2 (문항#31 · 3일행사) — 근거를 아예 안 밝혔다. 내용은 주입 원문에서 나왔다.
    # 기존 자는 막았고(서식만 보고), 새 자도 막는다 — 과잉 차단을 감수한 결정이다.
    units_31 = [
        SourceUnit(src_id="reg-41", doc="규정집v20", locator="제41조(성별기간)", text=""),
        SourceUnit(src_id="reg-71", doc="규정집v20", locator="제71조(축복결혼식)", text=""),
    ]
    bare_31 = "즉시 소속 교회장에게 보고하고, 40일 성별을 다시 완료한 뒤 처음부터 진행합니다."
    assert not evidence_ok(bare_31, units_31)
    # 같은 답변에 정확한 조문을 붙이면 통과한다 — 자료 보강으로 회수되는 경로가 이것이다
    cited_31 = bare_31 + " (근거: 규정집v20 제41조, 제71조)"
    assert evidence_ok(cited_31, units_31)


def _lexical_trace(*reasons: str) -> RetrievalTrace:
    trace = RetrievalTrace(units=list(_UNITS))
    for reason in reasons:
        trace.mark(reason)
    return trace


def test_strict_blocks_only_ungrounded_assertions_on_lexical_path():
    grounded = RAGResponse(answer="가정회비는 월 15,000원입니다 [[src: reg-56]].", citations=[])
    assert not chat_service._strict_blocks("lexical", _lexical_trace(), grounded)

    # 근거 표기 없이 절차를 단언한다 — 실측 96셀 중 유일하게 문구가 바뀐 경우(#39)
    bare = RAGResponse(
        answer="가정출발 이전에는 축복정리 후 지상에서 재축복에 임할 수 있습니다.", citations=[]
    )
    assert chat_service._strict_blocks("lexical", _lexical_trace(), bare)


def test_strict_keeps_the_bots_own_refusal_text():
    """봇이 스스로 거절한 문구는 고정 문구로 덮지 않는다 — 연결처 안내가 사라진다."""
    refusal = RAGResponse(
        answer=(
            "규정집 이외의 내용에는 답할 수 없습니다. "
            "담당 교회장 또는 가정행복국(02-3271-0502)으로 문의해 주시기 바랍니다."
        ),
        citations=[],
    )
    assert is_self_refusal(refusal.answer)
    assert not chat_service._strict_blocks("lexical", _lexical_trace(), refusal)


def test_strict_uses_the_old_rule_off_the_lexical_path():
    """file_search·both 와 폴백은 Gemini grounding 을 본다 — 기존 동작 그대로."""
    bare = RAGResponse(answer="근거 표기가 없는 답", citations=[])
    cited = RAGResponse(answer="근거 표기가 없는 답", citations=[RAGCitation(title="공식 자료")])

    assert chat_service._strict_blocks("file_search", RetrievalTrace(), bare)
    assert not chat_service._strict_blocks("file_search", RetrievalTrace(), cited)
    # 어휘가 빈손이라 폴백했다면 답을 만든 것은 file_search 다
    assert not chat_service._strict_blocks(
        "lexical", _lexical_trace(Reason.LEXICAL_EMPTY), cited
    )


# ── 위키 채널 (`# 참고 정리`) ────────────────────────────────────────────────
# 프롬프트는 `# 규정 원문`(units) 뒤에 `# 참고 정리`(위키 페이지)를 함께 넣는다. 페이지의
# `## 사실` 에는 `> 원문 인용` 이 붙어 있어 units 에 없는 조문 원문이 모델에게 간다.
# 아래 문자열은 replay R0085 실측이다 — 제17조를 축자 재현하고 정확히 인용했는데
# units 에 reg-17 이 없어 「지어냄」으로 차단됐다. 600건 중 56건이 같은 오경보였다.

_PAGE_UNITS = [
    SourceUnit(src_id="reg-17", doc="규정집v20", locator="제17조(3일행사)", text="…"),
]

_VIA_PAGE = "3일행사는 가정출발 이후에 진행합니다. (근거: 규정집v20 제17조)"


def test_gate_accepts_evidence_that_arrived_through_the_wiki_page():
    """위키 페이지가 실어 온 조문을 인용한 답변은 막지 않는다.

    **이 테스트가 없으면 회귀를 못 잡는다** — `evidence_units` 대신 `units` 를 다시
    쓰기 시작해도 다른 테스트는 전부 통과한다.
    """
    trace = RetrievalTrace(units=list(_UNITS), page_units=list(_PAGE_UNITS))
    assert not chat_service._strict_blocks("lexical", trace, RAGResponse(answer=_VIA_PAGE))

    # 같은 답변인데 페이지 채널을 빼면 막힌다. 그것이 고치기 전의 동작이다.
    blind = RetrievalTrace(units=list(_UNITS))
    assert chat_service._strict_blocks("lexical", blind, RAGResponse(answer=_VIA_PAGE))


def test_gate_still_blocks_what_no_channel_supplied():
    """넓힌 것은 「위키로 준 것」까지다. 어디로도 안 준 조문은 그대로 막는다."""
    trace = RetrievalTrace(units=list(_UNITS), page_units=list(_PAGE_UNITS))
    ghost = RAGResponse(answer="처음부터 다시 진행합니다. (근거: 규정집v20 제99조)")
    assert chat_service._strict_blocks("lexical", trace, ghost)


def test_evidence_units_merges_without_duplicating():
    """두 채널이 같은 조문을 실어 와도 한 번만 센다 — 대조 목록이지 집계가 아니다."""
    dup = RetrievalTrace(units=list(_UNITS), page_units=list(_UNITS) + list(_PAGE_UNITS))
    assert [u.src_id for u in dup.evidence_units] == ["reg-55", "reg-56", "glo-2", "reg-17"]
    # 위키를 안 탄 경로에서는 `units` 그대로다.
    assert RetrievalTrace(units=list(_UNITS)).evidence_units == _UNITS


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


def test_차단_문구는_사람에게로_넘긴다():
    """제품 방향 B 는 「근거 없으면 유보하고 **담당자로 넘긴다**」다.

    유보율이 68.2% 라 10문항 중 7개가 이 문구로 끝난다. 연락처가 없으면 그 7개가
    전부 막다른 길이 된다 — 유보 자체가 목적이 아니라 사람에게 넘기는 것이 목적이다.

    「직접 인용 근거」 같은 내부 용어도 쓰지 않는다. 사용자는 그 말을 모른다.
    """
    assert "02-3271-0502" in STRICT_EVIDENCE_MESSAGE
    for jargon in ("직접 인용", "grounding", "citation", "src_id"):
        assert jargon not in STRICT_EVIDENCE_MESSAGE, f"내부 용어 누출: {jargon}"


# ── file_search·both 경로 ② 지어냄 검사 (2026-08-22) ─────────────────────────
# grounding 청크를 대조 목록으로 쓴다. 문자열은 봇 29 실측 답변·규정집v20 원문 형태.


def _chunk(title: str, content: str = "", approximate: bool = False) -> RAGCitation:
    return RAGCitation(title=title, content=content, approximate=approximate)


def test_grounding_지어냄_가짜_조문을_잡는다():
    from app.services.strict_mode import fabricated_vs_grounding

    chunks = [_chunk("규정집v20 제55조", "축복감사헌금은 …")]
    fake = fabricated_vs_grounding("헌금은 (근거: 규정집v20 제99조) 에 따릅니다.", chunks)
    assert ("조", 99) in fake


def test_grounding_청크_본문에_있는_조문은_정당하다():
    from app.services.strict_mode import fabricated_vs_grounding

    # 청크 본문이 다른 조문을 언급하면(원문 교차 참조) 그 조문 인용은 지어냄이 아니다
    chunks = [_chunk("규정집v20 제55조", "제 56 조의 납부 기준을 따른다.")]
    assert fabricated_vs_grounding("(근거: 제56조)", chunks) == set()


def test_grounding_재인용은_거짓양성이_아니다():
    """규정집v20 원문은 조문 끝에 원전 각주를 내장한다 — 그 재인용을 막으면 안 된다.

    실사례: 제65조 청크의 「근거: [2022_ver.] 축복행정 국제 규정집 03. …」 을 모델이
    옮겼고, 조문 키(제65조)는 청크 제목·본문에 실재했다(§10-2 사후 판독)."""
    from app.services.strict_mode import fabricated_vs_grounding

    chunks = [
        _chunk(
            "규정집v20 제65조",
            "탈선문제 판단 기준 … 근거: [2022_ver.] 축복행정 국제 규정집 03. 각종 성적문제 및 지도",
        )
    ]
    answer = "(근거: 규정집v20 제65조, [2022_ver.] 축복행정 국제 규정집 03. 각종 성적문제 및 지도)"
    assert fabricated_vs_grounding(answer, chunks) == set()


def test_grounding_조문_형태가_없으면_판정_불가로_빈값():
    from app.services.strict_mode import fabricated_vs_grounding, grounding_locators

    chunks = [_chunk("가이드북.pdf", "일반 안내 문단 — 조문 번호 없음")]
    assert grounding_locators(chunks) == set()
    # 「안 쟀음」이지 「지어냄 0」이 아니다 — 막지 않는다
    assert fabricated_vs_grounding("(근거: 제12조)", chunks) == set()


def test_grounding_근사_백필_청크는_대조_목록에서_뺀다():
    from app.services.strict_mode import grounding_locators

    assert grounding_locators([_chunk("규정집v20 제55조", approximate=True)]) == set()


def test_strict_blocks_FS경로_가짜_조문이면_막고_재인용이면_통과():
    from app.services.chat_service import _strict_blocks

    trace = RetrievalTrace()
    chunks = [_chunk("규정집v20 제55조", "축복감사헌금 …")]
    fake = RAGResponse(answer="(근거: 제99조) 에 따라 납부합니다.", citations=chunks)
    ok = RAGResponse(answer="(근거: 제55조) 에 따라 납부합니다.", citations=chunks)
    unmarked = RAGResponse(answer="납부 절차는 다음과 같습니다.", citations=chunks)
    assert _strict_blocks("file_search", trace, fake) is True
    assert _strict_blocks("file_search", trace, ok) is False
    # 본문 표기가 없어도 grounding 이 있으면 막지 않는다 — ①을 새로 요구하지 않는다
    assert _strict_blocks("file_search", trace, unmarked) is False


def test_strict_blocks_FS경로_자체_거절은_그대로_둔다():
    from app.services.chat_service import _strict_blocks

    trace = RetrievalTrace()
    chunks = [_chunk("규정집v20 제55조", "…")]
    refusal = RAGResponse(
        answer="제99조 관련 내용은 확인되지 않아 답변드리기 어렵습니다.", citations=chunks
    )
    assert _strict_blocks("file_search", trace, refusal) is False


def test_grounding_판정은_절단_전_원문으로_한다():
    """`content` 는 표시용 800자 절단본이다(`rag/gemini.py:162`) — 절단 뒤의 조문을
    인용했다고 지어냄으로 몰면 안 된다. 판정은 `full_content` 가 맡는다."""
    from app.services.strict_mode import fabricated_vs_grounding

    chunk = RAGCitation(
        title="규정집v20.txt",
        content="제 18 조 앞부분만 저장…",           # 절단본에는 제19조가 없다
        full_content="제 18 조 … (긴 원문) … 제 19 조 접수 시기는 …",
    )
    assert fabricated_vs_grounding("(근거: 규정집v20 제19조)", [chunk]) == set()
