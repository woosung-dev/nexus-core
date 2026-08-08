"""
어휘 검색(BM25)과 순위 융합(RRF). 외부 의존성 없음 — 순수 파이썬이다.

**왜 BM25 를 직접 쓰는가.** dense-only 검색이 이 도메인에서 실패하는 지점이 로그에 남아 있다.
「가정회비 미납」 질문에서 1위가 `유아회비`(0.808), 정답 `가정공과금`은 2위(0.790)였다.
임베딩은 "회비"라는 의미만 보고 두 낱말을 붙여 놓는다. 어휘 검색은 「가정회비」를 글자로 본다.

규모가 작아서(위키 138쪽 · 원문 250건 · 사실문장 971개) 라이브러리가 필요 없다.
역색인 전체가 메모리 몇 MB 고, 검색은 밀리초다.
"""

import math
import re
import unicodedata
from collections import defaultdict

# 「제 19 조」·「제19조의2」처럼 띄어 쓴 조문 번호를 한 덩어리로 붙인다.
# 이걸 먼저 하지 않으면 `19` 만 숫자로 떨어져 나가 조문 번호가 검색어로 안 남는다.
_CITE = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")

# 분기 순서가 규칙이다. 조문 번호 → 영숫자 → 숫자 → 한글.
#   제19조     한 토큰      (첫 분기가 없으면 「제」/「조」/「19」 셋으로 찢어진다)
#   blessing4u 한 토큰      (`[A-Za-z][A-Za-z0-9]*` — 숫자로 끊기지 않는다)
#   15,000     한 토큰      (콤마 세 자리 묶음을 숫자의 일부로 본다)
_TOKEN = re.compile(
    r"제\d+조(?:의\d+)?"
    r"|[A-Za-z][A-Za-z0-9]*"
    r"|\d+(?:,\d{3})*(?:\.\d+)?"
    r"|[가-힣]+"
)

_HANGUL = re.compile(r"^[가-힣]+$")


def tokenize(text: str) -> list[str]:
    """검색어를 뽑는다. 한글은 낱말과 문자 바이그램을 함께 낸다.

    형태소 분석기가 없으므로 「가정회비를」은 낱말로는 「가정회비」와 다른 토큰이 된다.
    바이그램이 그 간극을 메운다 — 그리고 이 도메인에서는 바이그램이 오히려 판별력을 준다.

        가정회비 → 가정 · 정회 · 회비
        유아회비 → 유아 · 아회 · 회비

    겹치는 건 흔한 「회비」뿐이고, 희소한 「정회」가 둘을 가른다. BM25 의 IDF 가
    그 희소성에 가중치를 준다 — dense 가 놓친 구분이 정확히 여기서 살아난다.
    """
    norm = unicodedata.normalize("NFKC", text or "").casefold()
    norm = _CITE.sub(lambda m: "제" + m.group(1) + "조" + ("의" + m.group(2) if m.group(2) else ""), norm)

    out: list[str] = []
    for tok in _TOKEN.findall(norm):
        out.append(tok)
        if "," in tok:
            # 「15,000」과 「15000」이 서로 안 맞으면 금액 질문이 통째로 빗나간다.
            out.append(tok.replace(",", ""))
        elif _HANGUL.match(tok) and len(tok) >= 2:
            out.extend(tok[i : i + 2] for i in range(len(tok) - 1))
    return out


class BM25:
    """Okapi BM25. 질의어 포스팅에 걸린 문서만 채점한다."""

    K1 = 1.2
    B = 0.75

    def __init__(self, docs: list[tuple[str, str]]) -> None:
        """docs: (doc_id, text) 목록. 순서가 곧 내부 인덱스다."""
        self.ids = [d for d, _ in docs]
        self.postings: dict[str, dict[int, int]] = defaultdict(dict)
        self.doclen: list[int] = []

        for i, (_, text) in enumerate(docs):
            tf: dict[str, int] = defaultdict(int)
            for t in tokenize(text):
                tf[t] += 1
            for t, c in tf.items():
                self.postings[t][i] = c
            self.doclen.append(sum(tf.values()))

        n = len(docs)
        self.avgdl = sum(self.doclen) / n if n else 0.0
        # 표준 Okapi IDF. 문서 절반 이상에 나오는 말은 음수가 되므로 0 으로 눌러 둔다 —
        # 안 누르면 「축복」처럼 어디에나 있는 낱말이 점수를 깎는 쪽으로 작동한다.
        self.idf = {
            t: max(0.0, math.log((n - len(p) + 0.5) / (len(p) + 0.5) + 1.0))
            for t, p in self.postings.items()
        }

    def search(self, query: str, depth: int = 50) -> list[tuple[str, float]]:
        scores: dict[int, float] = defaultdict(float)
        for t in tokenize(query):
            idf = self.idf.get(t)
            if not idf:
                continue
            for i, tf in self.postings[t].items():
                denom = tf + self.K1 * (1 - self.B + self.B * self.doclen[i] / (self.avgdl or 1))
                scores[i] += idf * tf * (self.K1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:depth]
        return [(self.ids[i], s) for i, s in ranked]


RRF_K = 60  # 표준값. 상위 몇 등 안에서의 미세한 점수차를 의도적으로 뭉갠다.


def rrf(lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion — 점수 스케일이 다른 순위표들을 등수로만 합친다.

    BM25 점수와 코사인 유사도는 단위가 달라 더할 수 없다. RRF 는 점수를 버리고
    등수만 쓰기 때문에 정규화 없이 섞인다. 그래서 하이브리드의 기본형으로 쓰인다.

    같은 id 가 한 리스트에 두 번 나오면 **가장 앞선 등수만** 센다 — 청크 여러 개가
    같은 원문으로 매핑될 때 한 문서가 중복 가산되는 걸 막는다.
    """
    fused: dict[str, float] = defaultdict(float)
    for ranked in lists:
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranked, 1):
            if doc_id in seen:
                continue
            seen.add(doc_id)
            fused[doc_id] += 1.0 / (k + rank)
    return fused


def _selftest() -> None:
    """이 도메인에서 끊기면 안 되는 표기 — 조문 번호·금액·플랫폼 이름."""
    t = tokenize("제 19 조에 따라")
    assert "제19조" in t, t
    assert "19" not in t, t

    t = tokenize("제19조의2")
    assert "제19조의2" in t, t

    t = tokenize("15,000원을 납부")
    assert "15,000" in t and "15000" in t, t
    assert "000" not in t, t

    t = tokenize("BLESSING4U 등업")
    assert "blessing4u" in t, t
    assert "blessing" not in t and "4u" not in t, t

    # 낱말 자체 + 판별용 바이그램이 함께 나와야 한다
    t = tokenize("가정회비 미납")
    assert "가정회비" in t and "정회" in t, t
    # 조사가 붙으면 낱말은 달라지지만 바이그램이 이어 준다
    assert "정회" in tokenize("가정회비를 내지 않으면")

    # 「가정회비」와 「유아회비」를 실제로 가르는지
    bm = BM25([("가정공과금", "가정회비 하늘공관금 납부"), ("유아회비", "유아회비 유아기금 출생신고")])
    top = bm.search("가정회비 미납")
    assert top and top[0][0] == "가정공과금", top

    assert rrf([["a", "b"], ["b", "a"]])["a"] == rrf([["a", "b"], ["b", "a"]])["b"]
    print("retrieval selftest OK")


if __name__ == "__main__":
    _selftest()
