"""답변 본문의 기계 id 표기 벗기기 — 무엇을 지우고 무엇을 남기는가, 그리고 순서.

계약은 셋이다.

1. **기계 id 는 지운다.** `[[src: reg-41]]`·`[reg-66]`·`(근거: reg-39, reg-40)` 은
   사용자에게 뜻이 없다. 모델이 주입 라벨을 흉내내 만든 것이다.
2. **조문 표기는 남긴다.** `(근거: 규정집v20 제71조)` 는 사람이 찾아볼 수 있는 정보다.
3. **벗기기는 strict 게이트 뒤다.** 게이트가 그 표기를 주입 목록과 대조하므로 먼저
   지우면 정답이 `STRICT_EVIDENCE_MESSAGE` 로 치환된다.

픽스처 문자열은 냉동 기준선(`exports/wiki_eval/answers.json`, 답변 225개)에서 실제로
관측된 모양을 그대로 가져왔다. `exports/` 는 gitignore 라 데이터가 이 기계에만 있어서
커버리지를 여기로 옮겨 둔다.
"""

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.bot import Bot
from app.models.chat import ChatSession
from app.schemas.chat import ChatCompletionRequest
from app.schemas.rag import RAGCitation, RAGResponse
from app.services import chat_service
from app.services.chat_service import ChatService
from app.services.strict_mode import (
    cited_ids,
    has_grounded_citation,
    strip_source_markers,
    strip_source_markers_from_citations,
)
from app.services.unanswered import RetrievalTrace
from app.services.wiki.store import SourceUnit

_ID_RE = re.compile(r"(?:reg|glo)-\d+")

UNITS = [
    SourceUnit(src_id="reg-43", doc="규정집v20", locator="제43조", text="12일 가정출발의식은 …"),
    SourceUnit(src_id="glo-2", doc="대사전v4", locator="행정 2", text="가정출발 …"),
]


# ---- 1. 관측된 형태를 전부 지운다 ------------------------------------------------

@pytest.mark.parametrize(
    "before, after",
    [
        # 대괄호 — 이중·단일·라벨 변형
        ("확정되어야 합니다. [[src: reg-41]]", "확정되어야 합니다."),
        ("확정되어야 합니다. [[src: reg-3, glo-132]]", "확정되어야 합니다."),
        ("확정되어야 합니다. [src: reg-69]", "확정되어야 합니다."),
        ("확정되어야 합니다. [근거: reg-56]", "확정되어야 합니다."),
        ("확정되어야 합니다. [근거 규정: reg-41, reg-43, glo-2]", "확정되어야 합니다."),
        # 맨 id 목록 — 기준선에서 가장 흔한 형태(125건)
        ("탈선의 기준으로 봅니다 [reg-66]", "탈선의 기준으로 봅니다"),
        ("기준으로 봅니다 [reg-65, reg-63]", "기준으로 봅니다"),
        ("기준으로 봅니다 [glo-29]", "기준으로 봅니다"),
        # 소괄호
        ("충족해야 합니다. (근거: reg-39, reg-40)", "충족해야 합니다."),
        ("충족해야 합니다. (근거: [glo-115], [reg-11])", "충족해야 합니다."),
        ("충족해야 합니다. ([reg-39])", "충족해야 합니다."),
        ("충족해야 합니다. ([[src: reg-66]])", "충족해야 합니다."),
        # 문장 가운데
        ("의식은 [reg-43] 성별 이후입니다.", "의식은 성별 이후입니다."),
    ],
)
def test_기계_id_표기는_형태와_무관하게_지워진다(before, after):
    assert strip_source_markers(before) == after


def test_인접_마커는_한_덩어리로_지워진다():
    """사이 쉼표를 남기면 「합니다. ,」 가 화면에 뜬다. 기준선에 실제로 있던 모양이다."""
    assert (
        strip_source_markers("축도 기준을 확인해야 합니다. [[src: reg-43]], [[src: glo-2]]")
        == "축도 기준을 확인해야 합니다."
    )
    assert strip_source_markers("봅니다 [reg-65] [reg-63] [glo-29]") == "봅니다"


def test_구두점_앞에_공백이_남지_않는다():
    """`합니다 [reg-x].` 를 그냥 지우면 `합니다 .` 가 된다."""
    assert strip_source_markers("규정되어 있습니다 [reg-66].") == "규정되어 있습니다."
    assert strip_source_markers("있습니다 [reg-66], 그리고") == "있습니다, 그리고"


def test_괄호는_안전한_것만_붙인다():
    """`.`·`,` 앞 공백만 지운다. `)` 까지 넣으면 한국어 병기 표기를 건드린다."""
    assert strip_source_markers("축복결혼식 (축복식)은 의례입니다.") == "축복결혼식 (축복식)은 의례입니다."


def test_빈_답변은_그대로_돌려준다():
    """빈 답변은 실재한다 — 그래서 바로 뒤에 빈답변 게이트가 있다."""
    assert strip_source_markers("") == ""


# ---- 2. 조문 표기는 남긴다 ------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "원죄를 청산합니다 (근거: 규정집v20 제71조, 표 2)",
        "금액은 다음과 같습니다 (근거: 대사전v4 행정 95, 규정집v20 제55조)",
        "적용됩니다 (규정 근거: 규정집 제17조)",
        "구분됩니다 (근거: 규정집v20 제14조, 제32조, 표 2)",
        "관리합니다 (근거: 규정집v20 제63조제3항)",
    ],
)
def test_사람이_읽는_조문_표기는_건드리지_않는다(text):
    """`규정집v20 제71조` 는 찾아볼 수 있는 정보다. 지우면 손실이다.

    strict 게이트도 이 형식을 `locator` 와 대조한다(`_locator_keys`) — 지우면 게이트가
    읽을 것이 줄어든다.
    """
    assert strip_source_markers(text) == text


def test_한_문장에_섞여_있으면_기계_id_만_빠진다():
    assert (
        strip_source_markers(
            "12일 의식은 성별 이후입니다 [reg-43]. 헌금은 규정에 따릅니다 (근거: 규정집v20 제55조)."
        )
        == "12일 의식은 성별 이후입니다. 헌금은 규정에 따릅니다 (근거: 규정집v20 제55조)."
    )


# ---- 3. 순서 — 게이트 뒤여야 한다 -----------------------------------------------

def _trace() -> RetrievalTrace:
    trace = RetrievalTrace()
    trace.units = list(UNITS)
    return trace


def test_벗기기가_strict_게이트보다_앞이면_정답이_죽는다():
    """순서를 실행으로 남긴다.

    게이트는 「답변에 남은 근거 표기」를 주입 목록과 대조한다(PR #59). 먼저 벗기면
    대조할 표기가 0개라 `_strict_blocks` 가 참이 되어 **정답이**
    `STRICT_EVIDENCE_MESSAGE` 로 치환된다. 그래서 벗기기는 게이트 뒤에 있다.
    """
    grounded = "12일 가정출발의식은 성별 이후 진행합니다. [[src: reg-43]]"
    answered = RAGResponse(answer=grounded, citations=[], followups=[])

    # 게이트가 먼저 보면 통과한다
    assert has_grounded_citation(grounded, UNITS) is True
    assert chat_service._strict_blocks("lexical", _trace(), answered) is False

    # 벗긴 뒤에 보면 막힌다 — 이 순서로 배선하면 안 된다는 증거
    stripped = RAGResponse(answer=strip_source_markers(grounded), citations=[], followups=[])
    assert cited_ids(stripped.answer) == set()
    assert chat_service._strict_blocks("lexical", _trace(), stripped) is True


def test_벗기기는_조문_표기로_받은_근거를_없애지_않는다():
    """조문만으로 게이트를 통과한 답변은 벗겨도 통과 상태가 유지된다.

    과잉 거절 22.5% → 5.0% 를 만든 것이 이 형식이다. 벗기기가 그걸 깎으면 안 된다.
    """
    text = "축복감사헌금은 규정집v20 제43조에 따릅니다 [reg-43]"
    assert has_grounded_citation(strip_source_markers(text), UNITS) is True


# ---- 4. 인용 segments 도 같이 벗긴다 --------------------------------------------

def test_segments_도_같이_벗겨진다():
    """⚠ 이걸 빼면 각주가 조용히 사라진다.

    프론트가 `content.indexOf(segment)` 로 각주를 앵커한다(`citationMarkers.ts`).
    본문만 벗기면 segment 가 본문의 부분문자열이 아니게 된다.
    """
    body = "12일 의식은 성별 이후입니다. [[src: reg-43]]"
    citation = RAGCitation(
        title="규정집v20 제43조",
        content="제 43 조 원문 …",
        uri="reg-43",
        segments=["12일 의식은 성별 이후입니다. [[src: reg-43]]"],
    )
    strip_source_markers_from_citations([citation])
    stripped_body = strip_source_markers(body)

    assert citation.segments == ["12일 의식은 성별 이후입니다."]
    # 앵커가 성립한다 — 이게 각주가 붙는 조건이다
    assert stripped_body.find(citation.segments[0]) >= 0


def test_evidence_와_content_는_건드리지_않는다():
    """`evidence` 는 원문 청크(`content`)의 부분문자열이다. 답변 본문의 것이 아니라
    벗기면 형광펜이 원문과 어긋난다."""
    citation = RAGCitation(
        title="규정집v20 제43조",
        content="제 43 조 [reg-43] 원문 …",
        uri="reg-43",
        evidence=["제 43 조 [reg-43] 원문"],
    )
    strip_source_markers_from_citations([citation])
    assert citation.content == "제 43 조 [reg-43] 원문 …"
    assert citation.evidence == ["제 43 조 [reg-43] 원문"]


def test_인용이_없어도_터지지_않는다():
    strip_source_markers_from_citations([])


# ---- 5. 종단 — 저장되는 본문에 기계 id 가 없다 -----------------------------------

RAW_ANSWER = (
    "12일 가정출발의식은 성별 이후 진행합니다. [[src: reg-43]]\n"
    "1~3일 정성, 4일째 의식으로 나뉩니다 [reg-43], [glo-2]\n"
    "축복감사헌금은 규정에 따릅니다 (근거: 규정집v20 제55조)."
)


def _bot(**kw) -> Bot:
    kw.setdefault("llm_model", "gemini-3.5-flash-lite")
    bot = Bot(name="테스트 봇 D-1 ver2", description="test", **kw)
    bot.id = 29
    return bot


def _chat_session() -> ChatSession:
    s = ChatSession(user_id=1, bot_id=29)
    s.id = 9
    return s


@pytest.mark.asyncio
async def test_어휘_경로가_저장하는_본문에는_기계_id_가_없다(monkeypatch):
    """DB 에 남으면 새로고침 때 다시 보인다 — 그래서 `create_message` 보다 앞에서 벗긴다."""
    create = AsyncMock(return_value=SimpleNamespace(id=5))
    monkeypatch.setattr(chat_service.crud_chat, "create_message", create)
    monkeypatch.setattr(chat_service, "search_faq_override", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_service, "get_rag_service",
                        lambda provider=None: SimpleNamespace(generate_with_rag=AsyncMock()))
    monkeypatch.setattr(chat_service, "load_runtime_facts", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_service, "build_prompt_overlay", lambda facts: "")
    monkeypatch.setattr(chat_service, "term_rules", lambda facts: [])
    monkeypatch.setattr(chat_service, "_schedule_evidence_fill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_schedule_citation_backfill", lambda **kw: None)
    monkeypatch.setattr(chat_service, "_record_unanswered", AsyncMock(return_value=None))

    async def fake_wiki(**kw):
        return (
            RAGResponse(
                answer=RAW_ANSWER,
                citations=[
                    RAGCitation(
                        title="규정집v20 제43조",
                        content="제 43 조 …",
                        uri="reg-43",
                        segments=["12일 가정출발의식은 성별 이후 진행합니다. [[src: reg-43]]"],
                    )
                ],
                followups=["다음 질문"],
            ),
            None,
        )

    monkeypatch.setattr("app.services.wiki.service.answer_with_wiki", fake_wiki, raising=True)

    session = MagicMock()
    session.commit = AsyncMock()
    resp = await ChatService(session).process_chat_request(
        ChatCompletionRequest(
            bot_id=29, message="2세 가정 12일 가정출발의식 절차가 뭐야?", use_rag=True, stream=False
        ),
        _bot(retrieval_mode="lexical"),
        _chat_session(),
    )

    saved = create.await_args.kwargs["content"]
    assert "[[src:" not in saved
    assert _ID_RE.search(saved) is None
    # 조문 표기는 남는다
    assert "(근거: 규정집v20 제55조)" in saved
    # 화면과 DB 가 같아야 새로고침 결과가 같다
    assert resp.content == saved
    # 각주 앵커가 성립한다
    assert saved.find(resp.citations[0].segments[0]) >= 0
    assert _ID_RE.search(resp.citations[0].segments[0]) is None
