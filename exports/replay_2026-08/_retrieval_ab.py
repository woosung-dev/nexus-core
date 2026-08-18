"""검색 A/B — BM25 단독 vs BM25+dense(의미). **생성 호출 0회.**

## 왜 검색만 재나

replay 600건에서 답 못 한 373건 중 **234건이 봇의 자체 거절**이고, 상위 26건을 주입 조문 제목과
함께 열어 보니 **검색이 엉뚱한 조문을 물어다 주고 있었다**.

    「상대자가 불륜을 한 것 같다」 → 제91조 자살 사안 · 미혼영인축복   (정답: 제63~66조 탈선)
    「축복 비용이 얼마인가」       → 납부확인서 · 성화신고             (정답: 제53조 축복감사헌금)
    「BLESSING 4U 링크」          → 행정지원센터 하나로 · 성물 관리    (정답: 제25조 B4U 운영 기준)

**생성을 태우지 않고 검색만 재면 호출이 임베딩뿐이고, 모델 변동성이 안 섞여 판정이 결정적이다.**

    유닛 임베딩 250회 (1회성·캐시) + 질문 임베딩 N회 = 265회 내외 < 하루 1,000회
    생성 0회

## 왜 dense 를 켜 보나

`store.py` 의 `WIKI_DENSE_SCALES` 기본값이 빈 문자열이라 지금은 **BM25 단독**이다.
뺀 이유는 `handoff-wiki-retrieval-2026-08-08.md` §5-1 —
**「의미 검색은 file_search 가 이미 하는 일이라 우리가 만들면 복제다」**.

**그 전제가 지금은 없다.** 라이브 봇 11 은 `lexical` 단독이라 file_search 를 안 탄다.
즉 의미 검색이 파이프라인 어디에도 없다.

## 정답지 — 원문을 직접 확인한 것만 넣었다

「어디 조문이 답인가」를 추측으로 채우면 자가 오염된다. 아래 `WANT` 는 **2026-08-17 에 원문 또는
조문 제목을 눈으로 확인한 것만** 담았다. 확신 없는 문항은 일부러 뺐다.

## 쓰는 법

    cd backend && .venv/bin/python ../exports/replay_2026-08/_retrieval_ab.py           # BM25 만 (호출 0)
    cd backend && .venv/bin/python ../exports/replay_2026-08/_retrieval_ab.py --dense   # dense 도 (임베딩 필요)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "backend" / ".env")

BOT = 11  # 파일시스템 코퍼스 기준(250유닛). 로컬 DB 의 bots.id=11 과는 다른 것이다.

# ⚠⚠ 이 스크립트는 `WikiIndex(11, load_pages/load_units)` 로 **파일시스템 인덱스를 직접** 만든다.
# 실제 파이프라인은 `get_index(29)` 로 **DB 인덱스**를 쓴다. 유닛은 DB↔FS 가 같지만
# **페이지가 다르다**(인계문서 `next-session-replay-first-2026-08-14.md`: 공통 8건뿐).
#
# 유닛 순위(`ranked_units`)만 보는 판정은 이 차이에 둔감하다 — 실측으로 units 600/600 일치.
# 그러나 **`fact` 스케일은 페이지에서 파생된다**(`fact_page`·`fact_src`). 따라서 아래 sweep 의
# 「fact 를 빼면 좋아진다」는 결론은 **봇 29 실물의 fact 가 아닐 수 있다.** 채택 전에
# `get_index(29)` 로 다시 재라 — 워크트리 `feat+idea` 의 `e7154e7` 이 같은 함정에 걸렸다
# (자를 봇 29 실물로 바꾸니 6건이 1건이 됐다).
#
# **실제 파이프라인을 탄 측정은 따로 있다** — `_run_e2e.py --tag dense150` + `_compare.py`.
# 그쪽 숫자(답변률 38.0% → 38.7%)가 판정의 근거이고, 이 파일은 진단용이다.

# 질문 → 이 조문 중 하나라도 주입되면 「찾았다」.
# ⚠ 전부 원문/제목을 직접 확인한 것이다. 추측으로 늘리지 마라 — 자가 오염된다.
CASES = [
    ("축복받을 때 대략적인 비용이 궁금해", ["reg-53"]),
    ("축복을 받았는데 상대자가 불륜을 한 것 같습니다. 어떻게 해야하나요?",
     ["reg-63", "reg-64", "reg-65", "reg-66"]),
    ("BLESSING 4U 웹사이트 링크 알려줘", ["reg-25", "glo-8"]),
    ("B4U 사이트 외에 매칭 방법은 어떤게 있나요?", ["reg-24", "reg-23"]),
    ("통일교에서는 야동을 어떻게 생각하나요?", ["reg-65", "reg-66"]),
    ("축복 후 성인 영상을 시청하는건 어떻게 생각해?", ["reg-65", "reg-66"]),
    ("사회에서는 음란물과 자위행위가 건강한 성생활이라는데 교회에서는 어떻게 봐?",
     ["reg-65", "reg-66"]),
    ("3일 금식에 대해서 알려줘", ["reg-33"]),
    ("가정출발은 축복식 이후 언제 해야 하나요?", ["reg-32", "reg-43"]),
    ("3일 행사 기도는 어떻게 해?", ["reg-69"]),
    ("축복을 받고 가정회비를 내지 않으면 얻게 되는 불이익이 있어?", ["reg-61"]),
    ("약혼식이후 반지를 함께 착용해도 돼? 약혼반지라는 게 따로 있나?", ["reg-71", "reg-72"]),
    ("당감봉 행사는 뭘 해요?", ["glo-137"]),
    ("교류를 결정하기 전에 꼭 3번 만나는 것이 원칙인가요?", ["reg-24"]),
]


async def build(dense: bool):
    if dense:
        os.environ["WIKI_DENSE_SCALES"] = "unit"
    else:
        os.environ["WIKI_DENSE_SCALES"] = ""
    from app.services.wiki.store import WikiIndex, clear_index_cache, load_pages, load_units
    clear_index_cache()
    idx = WikiIndex(BOT, pages=load_pages(BOT), units=load_units(BOT))
    await idx.build()
    return idx


async def run(idx, label: str) -> list[tuple]:
    from app.services.wiki.service import _select_units
    out = []
    for q, want in CASES:
        got = await idx.search(q)
        picked = [u.src_id for u in _select_units(got, "raw_budget")]
        hit = next((w for w in want if w in picked), None)
        rank = picked.index(hit) + 1 if hit else None
        out.append((q, want, picked, hit, rank))
    n = sum(1 for r in out if r[3])
    print(f"\n═══ {label} · {n}/{len(out)} 적중 ═══")
    for q, want, picked, hit, rank in out:
        mark = f"✅ {hit} ({rank}위)" if hit else "❌"
        print(f"  {mark:<18} {q[:40]}")
        if not hit:
            print(f"       want={'/'.join(want)}  got={', '.join(picked[:5])}")
    return out


def golden_cases():
    """독립 표본 — `exports/wiki_eval/corpus_evidence.json` 의 손라벨에서 뽑는다.

    **이 자는 내가 만든 것이 아니다.** 2026-08-08 에 「정답의 근거가 코퍼스 안에 있는가」를
    문항별로 손으로 매기며 `why` 에 실제 조문을 남긴 것이다. `CASES` 로 고른 융합 조합이
    **과적합인지**를 여기서 가른다 — 같은 손이 만든 자로 두 번 재면 아무것도 검증되지 않는다.
    """
    import json as _j
    import re as _re
    ev = _j.loads((ROOT / "exports/wiki_eval/corpus_evidence.json").read_text(encoding="utf-8"))
    qs = {str(q.get("no")): q["q"]
          for q in _j.loads((ROOT / "exports/regression/questions.json").read_text(encoding="utf-8"))["items"]
          if q.get("no") is not None}
    out = []
    for k, v in ev.items():
        if not isinstance(v, dict) or v.get("label") != "in":
            continue
        ids = sorted(set(_re.findall(r"\b(?:reg|glo)-\d+", v.get("why", ""))))
        q = qs.get(k)
        if q and ids:
            out.append((q, ids))
    return out


async def sweep(idx, cases=None, label="CASES(자체 정답지)") -> None:
    """융합 방식을 바꿔 가며 적중률을 훑는다. **벡터가 캐시된 뒤에는 호출 0회다.**

    `unit` 공간에 들어가는 순위표는 셋이다 — `unit.bm25` · `fact.bm25`(971 사실문장을 유닛으로
    매핑) · `unit.dense`. 현행은 셋을 `RRF_K=60` 으로 합친다. k 가 크면 각 순위표의 1위가
    약해져, 서로 다른 답을 1위로 미는 두 검색기가 **서로를 밀어낸다**(실측 5/14 → 4/14).
    """
    from collections import defaultdict
    from app.services.wiki.retrieval import rrf

    def fuse(lists, k, weights=None):
        fused = defaultdict(float)
        for i, ranked in enumerate(lists):
            w = 1.0 if weights is None else weights[i]
            seen = set()
            for rank, d in enumerate(ranked, 1):
                if d in seen:
                    continue
                seen.add(d)
                fused[d] += w / (k + rank)
        return fused

    cases = cases or CASES
    us = idx.scales["unit"]
    fs = idx.scales["fact"]
    rows = []
    for q, want in cases:
        qv = await idx.query_vector(q)
        ub = [i for i, _ in us.lexical(q)]
        ud = [i for i, _ in us.dense(qv)]
        fb = [idx.fact_src[i] for i, _ in fs.lexical(q) if i in idx.fact_src]
        rows.append((q, want, ub, ud, fb))

    COMBOS = [
        ("현행 BM25 (unit+fact, k=60)", lambda ub, ud, fb: fuse([ub, fb], 60)),
        ("현행 +dense (k=60)", lambda ub, ud, fb: fuse([ub, fb, ud], 60)),
        ("fact 제외 · bm25+dense (k=60)", lambda ub, ud, fb: fuse([ub, ud], 60)),
        ("fact 제외 · bm25+dense (k=10)", lambda ub, ud, fb: fuse([ub, ud], 10)),
        ("fact 제외 · bm25+dense (k=5)", lambda ub, ud, fb: fuse([ub, ud], 5)),
        ("unit+fact+dense (k=10)", lambda ub, ud, fb: fuse([ub, fb, ud], 10)),
        ("bm25 2배 가중 +dense (k=10)", lambda ub, ud, fb: fuse([ub, ud], 10, [2.0, 1.0])),
        ("dense 2배 가중 +bm25 (k=10)", lambda ub, ud, fb: fuse([ub, ud], 10, [1.0, 2.0])),
        ("BM25 단독 (k=10)", lambda ub, ud, fb: fuse([ub, fb], 10)),
        ("dense 단독 (k=10)", lambda ub, ud, fb: fuse([ud], 10)),
    ]

    # 주입 상한은 실제 파이프라인과 같게 8건으로 본다(`service.BUDGET_UNITS`).
    TOPN = 8
    print(f"\n■ {label} · {len(rows)}문항")
    print(f"{'융합 방식':<34}적중  놓친 문항")
    print("─" * 96)
    best = None
    for name, fn in COMBOS:
        hits, miss = 0, []
        for q, want, ub, ud, fb in rows:
            scored = sorted(fn(ub, ud, fb).items(), key=lambda kv: kv[1], reverse=True)
            picked = [d for d, _ in scored[:TOPN]]
            if any(w in picked for w in want):
                hits += 1
            else:
                miss.append(q[:12])
        print(f"{name:<34}{hits:>2}/{len(rows)}  {' · '.join(miss)}")
        if best is None or hits > best[1]:
            best = (name, hits)
    print("─" * 96)
    print(f"최고: {best[0]} — {best[1]}/{len(rows)}")


async def main(dense: bool, do_sweep: bool = False) -> None:
    if do_sweep:
        idx = await build(True)
        await sweep(idx)
        await sweep(idx, golden_cases(), "corpus_evidence(독립 표본)")
        return
    base = await run(await build(False), "BM25 단독 (현행)")
    if not dense:
        print("\n--dense 를 주면 의미 검색을 켜고 다시 잰다(유닛 임베딩 250회 + 질문 임베딩).")
        return
    new = await run(await build(True), "BM25 + dense (의미)")

    print("\n═══ 문항별 변화 ═══")
    for (q, _, _, h0, r0), (_, _, _, h1, r1) in zip(base, new):
        if bool(h0) == bool(h1):
            state = "그대로" if h0 else "둘 다 못 찾음"
        else:
            state = "**dense 가 찾음**" if h1 else "**dense 가 놓침**"
        print(f"  {state:<18} {q[:44]}")
    b = sum(1 for r in base if r[3])
    d = sum(1 for r in new if r[3])
    print(f"\n적중 {b}/{len(CASES)} → {d}/{len(CASES)}  ({'+' if d >= b else ''}{d - b})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense", action="store_true", help="의미 검색도 켜서 비교(임베딩 호출 발생)")
    ap.add_argument("--sweep", action="store_true",
                    help="융합 방식(RRF k·스케일·가중)을 훑는다. 벡터 캐시 뒤에는 호출 0회")
    a = ap.parse_args()
    asyncio.run(main(a.dense, a.sweep))
