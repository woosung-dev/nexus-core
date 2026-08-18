"""게이트 변경의 실측 검증. API 호출 0회 (dense 꺼져 있어 순수 BM25).

두 가지를 잰다.

  ① 내 구현이 검증된 재판정 자와 **같은 집합**을 쓰는가
     `retrieved.units`  vs  `{src for page in pages for src in page.sources}`
     _rejudge_pages.py 는 후자로 57→1 을 냈다. 전자로 바꿔도 같아야 한다.
  ② 게이트 판정이 실제로 얼마나 바뀌는가 (replay 600건)

2026-08-18 실행 결과:

    ① 근거 집합 동일성   600 / 600 일치
    ② 차단 대상 337 → 280   (풀려남 57건 · **새로 막힘 0건**)
       지어냄     58 → 1    (남은 1건 = R0373, `_locator_keys` 오탐)

**새로 막힘이 0건이라는 것이 이 변경의 안전 근거다.** 근거 풀을 넓히기만 하므로
차단은 줄어들 수만 있다. 파일럿 동결 중에도 답변률을 떨어뜨릴 수 없다.

    NEXUS_DATA=/path/to/main python exports/replay_2026-08/_verify_gate.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv("NEXUS_DATA", REPO))   # 워크트리에는 exports 데이터가 없다
os.environ.setdefault("WIKI_ROOT", str(DATA / "exports" / "wiki_2026-08"))
sys.path.insert(0, str(REPO / "backend"))
os.chdir(REPO / "backend")   # `.env` 는 backend/ 기준으로 읽힌다

from app.services.strict_mode import evidence_ok, fabricated_citations  # noqa: E402
from app.services.wiki.service import _select_units  # noqa: E402
from app.services.wiki.store import get_index  # noqa: E402

BOT = 29
EX = DATA / "exports"


async def main() -> None:
    answers = {
        r["cid"]: r
        for r in json.loads((EX / "regression" / "_e2e_replay_0815.json").read_text("utf-8"))["results"]
    }
    rows = json.loads((EX / "replay_2026-08" / "_triage_replay_0815.json").read_text("utf-8"))["rows"]

    index = await get_index(BOT)
    all_units = index.units

    set_same = set_diff = 0
    cur_block = new_block = rescued = newly_blocked = 0
    cur_fab = new_fab = 0
    samples: list[tuple[str, str]] = []

    for row in rows:
        answer = answers[row["cid"]]["answer"]
        retrieved = await index.search(row["q"], top_k=3)
        units = _select_units(retrieved, "raw_budget")

        # ① 두 방식의 집합 비교
        mine = {u.src_id for u in retrieved.units}
        theirs = {
            src for page, _ in retrieved.pages for src in page.sources if src in all_units
        }
        if mine == theirs:
            set_same += 1
        else:
            set_diff += 1
            if len(samples) < 5:
                samples.append((row["cid"], f"내것-그것={sorted(mine - theirs)} 그것-내것={sorted(theirs - mine)}"))

        # ② 게이트 판정
        have = {u.src_id for u in units}
        merged = units + [u for u in retrieved.units if u.src_id not in have]

        cur_ok = evidence_ok(answer, units)
        new_ok = evidence_ok(answer, merged)
        cur_block += not cur_ok
        new_block += not new_ok
        rescued += (not cur_ok) and new_ok
        newly_blocked += cur_ok and (not new_ok)

        cur_fab += bool(fabricated_citations(answer, units)[1] or fabricated_citations(answer, units)[0])
        new_fab += bool(fabricated_citations(answer, merged)[1] or fabricated_citations(answer, merged)[0])

    n = len(rows)
    print(f"## ① 근거 집합 동일성   일치 {set_same} / 불일치 {set_diff}   ({n}건)")
    for cid, d in samples:
        print(f"   {cid}  {d}")
    print()
    print(f"## ② 게이트 판정 ({n}건)")
    print(f"   evidence_ok 실패(차단 대상)   현행 {cur_block}  →  변경 후 {new_block}")
    print(f"   풀려남 {rescued}건 · 새로 막힘 {newly_blocked}건")
    print(f"   지어냄 판정                   현행 {cur_fab}  →  변경 후 {new_fab}")


asyncio.run(main())
