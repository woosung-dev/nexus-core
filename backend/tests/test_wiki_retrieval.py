"""BM25 토크나이저·RRF — 이 도메인에서 끊기면 안 되는 표기.

`app/services/wiki/retrieval.py:_selftest()` 를 pytest 로 옮긴 것이다. 원래는
`python retrieval.py` 로만 돌아 CI 가 보지 않았다. 원문 로딩을 파일시스템에서 DB 로
옮기는 동안 토크나이저가 조용히 깨지면 검색이 통째로 나빠지므로 여기서 지킨다.

토크나이저가 이 표기들을 안 끊는 것이 검색기의 전부다 —
「가정회비」={가정,정회,회비} vs 「유아회비」={유아,아회,회비} 에서 희소 바이그램 「정회」가 가른다.
"""

from app.services.wiki.retrieval import BM25, rrf, tokenize


class Test조문번호와_금액표기:
    def test_조문번호는_공백이_있어도_한_토큰이다(self):
        t = tokenize("제 19 조에 따라")
        assert "제19조" in t
        assert "19" not in t

    def test_가지번호도_끊기지_않는다(self):
        assert "제19조의2" in tokenize("제19조의2")

    def test_금액은_쉼표_있는_형태와_없는_형태를_모두_낸다(self):
        t = tokenize("15,000원을 납부")
        assert "15,000" in t and "15000" in t
        assert "000" not in t

    def test_영문숫자_고유명사는_쪼개지_않는다(self):
        t = tokenize("BLESSING4U 등업")
        assert "blessing4u" in t
        assert "blessing" not in t and "4u" not in t


class Test한글_바이그램:
    def test_낱말과_판별용_바이그램이_함께_나온다(self):
        t = tokenize("가정회비 미납")
        assert "가정회비" in t and "정회" in t

    def test_조사가_붙어도_바이그램이_이어준다(self):
        assert "정회" in tokenize("가정회비를 내지 않으면")


class TestBM25와_RRF:
    def test_가정회비와_유아회비를_실제로_가른다(self):
        bm = BM25([
            ("가정공과금", "가정회비 하늘공관금 납부"),
            ("유아회비", "유아회비 유아기금 출생신고"),
        ])
        top = bm.search("가정회비 미납")
        assert top and top[0][0] == "가정공과금"

    def test_문서가_없어도_죽지_않는다(self):
        assert BM25([]).search("아무거나") == []

    def test_rrf_는_순위가_대칭이면_같은_점수를_준다(self):
        scores = rrf([["a", "b"], ["b", "a"]])
        assert scores["a"] == scores["b"]
