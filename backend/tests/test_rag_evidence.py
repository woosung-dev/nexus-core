# 근거 구절 스냅(원문 대조)과 grounding_supports 결합 로직을 검증하는 테스트
from types import SimpleNamespace

from app.schemas.rag import RAGCitation
from app.services.rag.evidence import _parse_spans, snap_to_source
from app.services.rag.gemini import _citations_from_grounding

CHUNK = (
    "⑪ 임신부, 산모, 중증질환자, 고령자, 미성년자, 장기복용 약물이 있는 자, 섭식장애 또는 건강상 위험이 예\n"
    "상되는 자에게는 무리한 금식을 요구하지 않는다. 이 경우 말씀훈독, 기도, 봉사로 대체한다."
)


class TestSnapToSource:
    def test_원문에_그대로_있으면_그대로_반환(self):
        span = "무리한 금식을 요구하지 않는다."
        assert snap_to_source(span, CHUNK) == span

    def test_줄바꿈이_단어를_가르면_원문_쪽_문자열로_되돌린다(self):
        # PDF 청크는 "예\n상되는" 처럼 단어 중간에 줄바꿈이 들어간다.
        got = snap_to_source("건강상 위험이 예상되는 자에게는", CHUNK)
        assert got is not None
        assert got in CHUNK
        assert "예\n상되는" in got

    def test_한_글자_오타는_원문_표기로_스냅된다(self):
        # 실측 사례 — 모델이 '산모'를 '산母'로 바꿔 냈다.
        got = snap_to_source("임신부, 산母, 중증질환자, 고령자, 미성년자", CHUNK)
        assert got is not None
        assert got in CHUNK
        assert "산모" in got and "산母" not in got

    def test_원문에_없는_문장은_버린다(self):
        assert snap_to_source("축복헌금은 전액 환불이 가능하다.", CHUNK) is None

    def test_너무_짧은_구절은_버린다(self):
        assert snap_to_source("금식", CHUNK) is None

    def test_반환값은_항상_원문의_부분문자열(self):
        for span in ["무리한 금식을 요구하지 않는다", "건강상 위험이 예상되는 자", "말씀훈독, 기도, 봉사로 대체"]:
            got = snap_to_source(span, CHUNK)
            assert got is None or got in CHUNK


class TestParseSpans:
    def test_표준_형식(self):
        assert _parse_spans('{"spans": ["가", "나"]}') == ["가", "나"]

    def test_배열만_와도_견딘다(self):
        # 실측에서 1/20 확률로 배열이 그대로 왔다.
        assert _parse_spans('["가", "나"]') == ["가", "나"]

    def test_문자열이_아닌_원소는_걸러낸다(self):
        assert _parse_spans('{"spans": ["가", 3, null]}') == ["가"]


def _grounding(chunk_texts, supports, same_source=False):
    """same_source=True 면 모든 청크가 같은 문서·페이지·본문 = 중복 제거 대상이 된다."""
    return SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(retrieved_context=SimpleNamespace(
                title="doc.pdf" if same_source else f"doc{i}.pdf",
                text=t,
                uri="u" if same_source else f"u{i}",
                page_number=1 if same_source else i))
            for i, t in enumerate(chunk_texts)
        ],
        grounding_supports=[
            SimpleNamespace(segment=SimpleNamespace(text=text), grounding_chunk_indices=idxs)
            for text, idxs in supports
        ],
    )


class TestCitationsFromGrounding:
    def test_supports_가_해당_청크에_붙는다(self):
        cits = _citations_from_grounding(
            _grounding(["원문A", "원문B"], [("답변구간1", [0]), ("답변구간2", [1])])
        )
        by_title = {c.title: c for c in cits}
        assert by_title["doc0.pdf"].segments == ["답변구간1"]
        assert by_title["doc1.pdf"].segments == ["답변구간2"]

    def test_한_구간이_여러_청크를_가리키면_모두에_붙는다(self):
        cits = _citations_from_grounding(_grounding(["원문A", "원문B"], [("공통구간", [0, 1])]))
        assert all(c.segments == ["공통구간"] for c in cits)

    def test_중복_제거시_구간이_합쳐진다(self):
        # 같은 청크가 두 번 실려도 카드는 하나로 합치되 구간은 둘 다 남아야 한다.
        cits = _citations_from_grounding(
            _grounding(["같은원문", "같은원문"], [("구간1", [0]), ("구간2", [1])], same_source=True)
        )
        assert len(cits) == 1
        assert cits[0].segments == ["구간1", "구간2"]
        assert cits[0].cite_count == 2

    def test_범위를_벗어난_인덱스는_무시한다(self):
        cits = _citations_from_grounding(_grounding(["원문A"], [("구간", [5]), ("정상", [0])]))
        assert cits[0].segments == ["정상"]

    def test_supports_가_없어도_인용은_나온다(self):
        g = _grounding(["원문A"], [])
        g.grounding_supports = None
        cits = _citations_from_grounding(g)
        assert len(cits) == 1 and cits[0].segments == []

    def test_evidence_기본값은_빈_배열(self):
        assert RAGCitation(title="t", content="c").evidence == []
