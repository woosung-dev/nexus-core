"""봇별 strict 모드의 작은 정책 모음.

strict 모드는 답변의 최신성·공식성을 판정하지 않는다. 대신 일반 답변에는 이번
RAG 호출에서 받은 직접 인용을 요구하고, FAQ에는 운영자가 작성한 거절문만 허용한다.
"""

import re

from app.schemas.rag import RAGCitation
from app.services.wiki.store import SourceUnit


# 게이트가 답변을 막았을 때 사용자가 받는 유일한 문장.
#
# 2026-08-14 파일럿 개시 전에 고쳤다. 전에는 「확인 가능한 직접 인용 근거가 없어 이
# 내용은 답변해 드릴 수 없습니다.」였는데 두 가지가 틀렸다.
#
#   ① **담당자로 넘기지 않는다.** 제품 방향 B 는 「근거 없으면 확실하게 유보하고
#      담당자로 넘긴다」인데, 이 문구는 유보만 하고 대화를 끊었다. 유보율 68.2% 라
#      10문항 중 7개가 막다른 길로 끝난다.
#   ② **「직접 인용 근거」는 내부 용어다.** 사용자는 그게 무슨 말인지 모른다.
#
# 연락처는 `unanswered.UNANSWERED_MESSAGE` · 봇 11 프롬프트와 같은 번호로 맞춘다.
STRICT_EVIDENCE_MESSAGE = (
    "규정집에서 근거를 찾지 못해 답변드리기 어렵습니다.\n"
    "담당 교회장님이나 가정행복국(02-3271-0502)으로 연락 부탁드립니다."
)

_REFUSAL_RE = re.compile(
    r"(?:답변|안내|도움).{0,16}(?:드리기|드릴|할).{0,16}(?:어렵|불가|않|못|없)|"
    r"답변할 수 없",
    re.IGNORECASE,
)


def has_direct_citation(citations: list[RAGCitation]) -> bool:
    """근사 백필이 아닌, 이번 RAG 응답의 식별 가능한 인용이 하나 이상인지 확인한다."""
    return any(
        not citation.approximate and bool(citation.title or citation.uri)
        for citation in citations
    )


def is_refusal_faq(answer: str) -> bool:
    """strict 봇에서 허용할 FAQ는 사용자를 안전하게 거절하는 안내문뿐이다."""
    return bool(_REFUSAL_RE.search(answer or ""))


# ── 어휘 경로 전용 게이트 ────────────────────────────────────────────────────
#
# `has_direct_citation()` 은 어휘 경로에서 **항상 참**이다. `wiki.service._citations()` 가
# 주입한 원문 유닛마다 `approximate=False` 인용을 만들기 때문이다 — 모델이 그 원문을
# 실제로 썼는지와 무관하다. 그래서 strict 를 켜도 보호가 하나도 늘지 않았다.
#
# 여기서는 대신 **모델이 답변에 남긴 근거 표기를 주입 목록과 대조한다.** 문자열 비교라
# LLM 추가 호출 0회 · 지연 0 · 결정론이다. 두 형식을 모두 받는다.
#
#     [[src: reg-3, glo-132]]        주입 블록의 [src_id] 라벨을 따라간 것
#     [근거: 규정집v20 제55조]        사람이 읽는 형식. `locator` 와 대조한다
#
# **조문 형식을 함께 받는 것이 핵심이다.** 봇 29(라이브 D-1 ver2 복제본) 20문항 × 2회
# 측정에서, src_id 만 보면 과잉 거절이 22.5%(9/40) 인데 조문을 함께 보면 5.0%(2/40) 로
# 떨어진다. 죽던 것은 「축복 헌금 얼마예요」(제55·56조) 같은 **정답**이었다.
# 같은 측정에서 주입 목록 밖 근거를 쓴 답변은 96셀 전부에서 0건이다.
_SRC_ID = r"(?:reg|glo)-\d+"
_SRC_ID_RE = re.compile(rf"\b{_SRC_ID}\b")
# 규정집 조문(`제55조`) 과 대사전 항목(`행정 134`). `locator` 가 그 형태로 저장돼 있다.
_ARTICLE_RE = re.compile(r"제\s*(\d+)\s*조")
_GLOSSARY_RE = re.compile(r"행정\s*(\d+)")


def _locator_keys(text: str) -> set[tuple[str, int]]:
    """조문·항목 번호를 대조용 키로 뽑는다. 0 채움을 지우려고 int 로 정규화한다 —
    모델이 「대사전 행정 002」라고 쓰는데 locator 는 「행정 2」다."""
    return {("조", int(m)) for m in _ARTICLE_RE.findall(text or "")} | {
        ("행", int(m)) for m in _GLOSSARY_RE.findall(text or "")
    }


def cited_ids(answer: str) -> set[str]:
    """답변이 표기한 원문 id. 마커 밖에 맨몸으로 쓴 것도 인용으로 친다."""
    return set(_SRC_ID_RE.findall(answer or ""))


def has_grounded_citation(answer: str, units: list[SourceUnit]) -> bool:
    """답변의 근거 표기가 **이번에 주입한 원문 안에 있는가.**

    하나라도 맞으면 참이다. 「모든 문장이 근거를 달았나」를 묻지 않는다 — 그렇게 걸면
    문장 하나가 마커를 빠뜨렸다는 이유로 답변 전체가 죽는다.
    """
    if not units:
        return False
    injected_ids = {u.src_id for u in units}
    if cited_ids(answer) & injected_ids:
        return True
    return bool(_locator_keys(answer) & _injected_locators(units))


def _injected_locators(units: list[SourceUnit]) -> set[tuple[str, int]]:
    return {k for u in units for k in _locator_keys(u.locator)}


def fabricated_citations(answer: str, units: list[SourceUnit]) -> tuple[set[str], set[tuple[str, int]]]:
    """답변이 **주입하지 않은** 근거를 댔는가. (가짜 id, 가짜 조문키)

    `has_grounded_citation` 이 못 보는 실패다. 그 함수는 「하나라도 맞으면 통과」라서
    맞는 것 하나에 가짜 셋을 얹어도 통과한다. 110셀 실측에서 **가짜 근거 26건 중 8건만**
    잡혔다(31%).

    이게 가장 위험한 형태다. 내용은 규정집에 실재하는데 **출처만 가짜**이면 사용자는
    그 조문을 찾아보고 못 찾는다. 실측 예: 주입은 `reg-72·73·41` 인데 답변이
    「[근거: 규정집 v20 제32조] > 실패 또는 중대한 위반이…」 라고 인용문까지 붙였다.
    """
    if not units:
        return set(), set()
    fake_ids = cited_ids(answer) - {u.src_id for u in units}
    fake_loc = _locator_keys(answer) - _injected_locators(units)
    return fake_ids, fake_loc


def evidence_ok(answer: str, units: list[SourceUnit]) -> bool:
    """어휘 경로의 근거 게이트. **두 조건을 모두** 통과해야 참이다.

        ① 주입한 근거를 하나라도 짚었다        `has_grounded_citation`
        ② 주입하지 않은 근거를 대지 않았다      `fabricated_citations` 가 빈 값

    합집합으로 거는 이유는 두 실패가 서로 다른 죄이기 때문이다 —
    ①만 보면 「가짜 근거를 얹은 답변」이 통과하고(실측 26건 중 18건 통과),
    ②만 보면 「근거를 아예 안 밝힌 답변」이 통과한다.

    110셀 실측(봇 29 · 55문항 × 2회 · 2026-08-14):

        정책          가짜근거 검출   불일치 문항 유보   전체 유보
        ① 단독            31%           62.5%        54.5%
        ② 단독            88%           50.0%        58.2%
        ①∪② ← 채택        88%           75.0%        68.2%

    **과잉 차단을 감수한 선택이다.** 10문항 중 7문항이 「확인되지 않습니다」로 나간다.
    근거: 오차단은 자료를 보강하면 자동으로 풀리지만(검색이 조문을 뽑으면 표기가 생긴다),
    잘못 나간 답은 회수가 안 된다. 그 비대칭이 이 결정의 전부다.

    ⚠ **file_search·both 경로에는 못 쓴다.** 주입 목록이 없어 대조가 성립하지 않는다.
      그 경로의 ②는 `fabricated_vs_grounding` 이 맡는다(2026-08-22 추가) — grounding
      청크를 대조 목록으로 쓴다. ①은 여전히 `has_direct_citation`(grounding 존재)이다.
    """
    if not has_grounded_citation(answer, units):
        return False
    fake_ids, fake_loc = fabricated_citations(answer, units)
    return not (fake_ids or fake_loc)


# ── file_search·both 경로 전용 게이트 ──────────────────────────────────────
#
# 이 경로는 주입 목록(units)이 없어 위의 자가 성립하지 않았고, `has_direct_citation`
# (grounding 존재)만 보는 반쪽이었다 — strict 를 켜도 유보 +0.9p(사실상 무보호).
# 대신 **grounding 청크 자체를 대조 목록으로** 쓴다. 청크는 모델이 실제로 받은
# 원문이므로, 어휘 경로의 「주입 목록」과 같은 지위다.


def grounding_locators(citations: list[RAGCitation]) -> set[tuple[str, int]]:
    """grounding 청크(제목+본문)에 등장하는 조문·항목 키. file_search·both 의 대조 목록.

    ⚠ `content` 는 표시용 800자 절단본이다(`rag/gemini.py:162`). 절단 뒤에서 조문 키가
    떨어져 나가면 정당한 인용이 지어냄으로 몰린다 — 그래서 **판정은 `full_content`
    (절단 전 원문 · 직렬화 제외 필드)로** 한다. 저장된 옛 데이터를 오프라인으로 재판정할
    때는 full_content 가 없으므로 content 로 폴백하고, 그 수치는 부풀 수 있음을 감안하라.
    """
    keys: set[tuple[str, int]] = set()
    for c in citations:
        if c.approximate:
            continue
        keys |= _locator_keys(c.title or "") | _locator_keys(c.full_content or c.content or "")
    return keys


def fabricated_vs_grounding(
    answer: str, citations: list[RAGCitation]
) -> set[tuple[str, int]]:
    """file_search·both 경로의 ② — 답변의 조문 표기가 grounding 청크 어디에도 없는가.

    어휘 경로 `fabricated_citations` 와 같은 죄(내용은 그럴듯한데 **출처만 가짜**)를
    이 경로에서 잡는다. ①(표기 요구)은 일부러 넣지 않는다 — 이 경로의 ①은 grounding
    존재(`has_direct_citation`)이고, 본문 표기를 새로 요구하면 지금까지 통과하던
    무표기 답변이 통째로 죽는다(어휘 경로에서 겪은 표기 누락 과차단의 재발).

    **청크 본문까지 대조에 넣는 것이 핵심이다.** 규정집v20 원문은 조문 끝에 원전 각주
    (`근거: [2022_ver.] 축복행정 국제 규정집 …`)를 내장하므로, 모델이 그 각주를 옮기는
    것은 재인용이지 지어냄이 아니다. 제목만 대조하면 그 재인용이 거짓 양성이 된다
    (실사례 판독: docs/architecture/research-wiki-plus-file-search-2026-08-19.md §10-2).

    청크에 조문·항목 형태가 하나도 없으면 **판정 불가**로 보고 빈 값을 돌려준다 —
    「안 쟀음」이지 「지어냄 0」이 아니다. 그 구분은 trace 의 `fabricated_checked` 가 남긴다.
    """
    keys = grounding_locators(citations)
    if not keys:
        return set()
    return _locator_keys(answer) - keys


# ── 화면 표시 — 기계 id 벗기기 ──────────────────────────────────────────────
#
# 모델은 주입 라벨(`[reg-41] 규정집v20 제41조`, `wiki/service.py:69`)을 흉내내 기계 id 를
# 본문에 남긴다. 봇 프롬프트에는 인용 형식 지시가 없다 — 모델이 스스로 만든 것이고
# 사용자에게는 뜻이 없는 문자열이다.
#
# **생성을 막으면 안 된다.** 위 게이트가 그 표기를 읽는다. 게이트를 통과한 뒤,
# 화면에 나가기 전에 벗긴다. 그래서 이 함수가 게이트와 같은 모듈에 있다 —
# 읽는 문법과 벗기는 문법이 갈라지면 조용히 어긋난다.
#
# 지우는 것은 **페이로드가 기계 id 뿐인 표기**다. 사람이 찾아볼 수 있는 조문·항목 표기
# (`(근거: 규정집v20 제71조, 표 2)`)는 정보라서 남긴다.
#
# 냉동 기준선(`exports/wiki_eval/answers.json`) 답변 225개 실측:
# 기계 id 243 → 6 (98% 제거) · 조문 표기 20 → 20 (100% 보존) · 구두점 잔여 0.
# 남는 것은 산문에 박힌 형태(`- 근거: 규정 reg-17, reg-33, glo-34`)뿐이라 그냥 둔다 —
# 거기서 id 만 빼면 문장이 토막난다.
_ID_LIST = rf"\[?\s*{_SRC_ID}\s*\]?(?:\s*[,·]\s*\[?\s*{_SRC_ID}\s*\]?)*"
_MARKER_LABEL = r"(?:src|출처|(?:규정\s*)?근거(?:\s*[^\]:：\n]{0,6})?)"
_MARKER = (
    rf"\[\[?\s*{_MARKER_LABEL}\s*[::]\s*{_ID_LIST}\s*\]\]?"
    rf"|\(\s*{_MARKER_LABEL}\s*[::]\s*{_ID_LIST}\s*\)"
    rf"|\[\s*{_SRC_ID}(?:\s*[,·]\s*{_SRC_ID})*\s*\]"
)
# 인접 마커는 한 덩어리로 먹는다. `합니다. [[src: reg-43]], [[src: glo-2]]` 에서 사이
# 쉼표를 남기면 「합니다. ,」 가 화면에 뜬다.
_MARKER_RUN_RE = re.compile(rf"[ \t]*(?:{_MARKER})(?:[ \t]*[,·]?[ \t]*(?:{_MARKER}))*")
_EMPTY_PARENS_RE = re.compile(r"\(\s*\)")


def strip_source_markers(answer: str) -> str:
    """답변 본문에서 기계 id 표기를 벗긴다. 조문 표기는 남긴다."""
    if not answer:
        return answer
    text = _MARKER_RUN_RE.sub("", answer)
    text = _EMPTY_PARENS_RE.sub("", text)  # 마커만 들어 있던 괄호
    text = re.sub(r"[ \t]{2,}", " ", text)
    # `.`·`,` 로만 좁힌다. `)` 까지 넣으면 「축복결혼식 (축복식)」을 건드린다.
    text = re.sub(r"[ \t]+([.,])", r"\1", text)
    return re.sub(r"(?m)[ \t]+$", "", text)


def strip_source_markers_from_citations(citations: list[RAGCitation]) -> None:
    """인용의 `segments` 에도 같은 것을 적용한다 (제자리 수정).

    ⚠ 이걸 빼면 각주가 조용히 사라진다.
    프론트가 `content.indexOf(segment)` 로 각주를 앵커하므로
    (`frontend-client/src/components/chat/citationMarkers.ts`), 본문만 벗기면 segment 가
    더 이상 본문의 부분문자열이 아니게 된다. `apply_term_rules_to_citations` 와 같은
    이유·같은 계약이다.

    `evidence` 는 원문 청크(`content`)의 부분문자열이므로 **건드리지 않는다.**
    """
    for citation in citations:
        if citation.segments:
            citation.segments = [strip_source_markers(s) for s in citation.segments]
