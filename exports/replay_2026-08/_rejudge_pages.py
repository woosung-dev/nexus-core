"""④(지어냄) 재판정 — 위키 채널을 근거 목록에 넣고 다시 센다.

**왜 필요한가.** `answer_with_wiki` 는 `raw`·`raw_budget` 에서 프롬프트에
`# 규정 원문`(units) 뿐 아니라 `# 참고 정리`(`_wiki_block`)도 넣는다. 위키 페이지의
`## 사실` 에는 `> 원문 인용` 이 붙어 있어(생성 규약) **units 에 없는 조문의 원문이
모델에게 간다.** 그런데 `fabricated_citations` 는 units 하고만 대조한다 →
정확한 인용이 「지어냄」으로 집계된다.

**답변을 다시 만들지 않는다.** 저장된 replay 답변을 그대로 두고 검색만 다시 돌려 그때
어떤 페이지가 갔는지 복원한다. `WIKI_DENSE_SCALES` 가 비어 있으면 dense 가 꺼져 순수
BM25 라 **API 호출 0회**다.

    python exports/replay_2026-08/_rejudge_pages.py

워크트리처럼 `exports/` 데이터가 없는 체크아웃에서 돌릴 때는 데이터 뿌리를 준다:

    NEXUS_DATA=/path/to/main-checkout python exports/replay_2026-08/_rejudge_pages.py

⚠ **「현행 재현」이 600/600 이 아니면 재판정도 그만큼 못 믿는다.** 오프라인 검색이 그때와
같다는 것을 먼저 증명하고 읽어야 한다. 2026-08-17 실행에서는 600/600 일치했다.
단 이 검증은 **units 만** 보증한다 — 페이지 순위는 따로 틀릴 수 있다(아래 BOT 주석).

2026-08-17 결과: **지어냄 57건 → 1건.**

남은 1건(R0373 「가정회비는 왜 해야 해요?」)도 지어냄이 아니라 **자의 오탐**이다.
주입된 reg-56 본문 안에 `근거: 20250613 축복가정 가정공과금 규정집: 제 5 조 납부 기준표`
가 있고 모델이 그것을 그대로 옮겼는데, `_locator_keys` 가 문서를 구분하지 않고 조문
번호만 봐서 규정집v20 제5조(최신 공문 우선 원칙)로 오인했다. 금액(15,000·3,000)·CMS 는
전부 프롬프트에 실재한다.

→ **replay 600건에서 내용이 틀린 답변은 0건이다.**
"""

import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv("NEXUS_DATA", REPO))
os.environ.setdefault("WIKI_ROOT", str(DATA / "exports" / "wiki_2026-08"))
sys.path.insert(0, str(REPO / "backend"))

from app.services.strict_mode import fabricated_citations  # noqa: E402
from app.services.wiki.service import _select_units  # noqa: E402
from app.services.wiki.store import get_index  # noqa: E402

# ⚠ **반드시 `get_index(29)` 를 써라.** 봇 11 의 파일시스템 페이지로 `WikiIndex` 를 직접
# 만들면 코퍼스는 같은데(138쪽·250건, 차이 0) **페이지 순위 동점 처리가 달라져 3위가
# 바뀐다.** 실제로 R0085 에서 3위가 `3일행사-가정출발`(재현) ↔ `축복자녀-축복후보자`
# (실제, reg-17 을 실어옴) 로 갈렸고, 그 한 쪽 차이가 정상 인용을 「지어냄」으로 만들었다.
# 점수는 0.0415 vs 0.0414 로 거의 동점이라 정렬 순서에 흔들린다. 유닛은 `ranked_units`
# (유닛 공간)에서 뽑혀 이 차이에 둔감하다 — 그래서 units 는 600/600 맞는데 페이지만 틀렸다.
BOT = 29  # replay 를 돌린 봇 그대로. `get_index` 가 DB 를 먼저 본다.
EXPORTS = DATA / "exports"


def _recorded_loc(result: dict) -> set[str]:
    """그때 런타임이 남긴 `fabricated_loc`. 재현 검증의 정답지다."""
    for stage in result["trace"].get("stages", []):
        if (stage.get("stage") or stage.get("name")) == "strict":
            return set(stage.get("fabricated_loc") or [])
    return set()


async def main() -> None:
    answers = {
        r["cid"]: r
        for r in json.loads(
            (EXPORTS / "regression" / "_e2e_replay_0815.json").read_text(encoding="utf-8")
        )["results"]
    }
    rows = json.loads(
        (EXPORTS / "replay_2026-08" / "_triage_replay_0815.json").read_text(encoding="utf-8")
    )["rows"]

    index = await get_index(BOT)
    all_units = index.units

    same = diff = 0
    mismatch: list[tuple] = []
    rescued: list[tuple] = []
    still: list[tuple] = []

    for row in rows:
        result = answers[row["cid"]]
        answer = result["answer"]
        retrieved = await index.search(row["q"], top_k=3)
        units = _select_units(retrieved, "raw_budget")
        have = {u.src_id for u in units}
        # 페이지가 실어 온 원문. 이것이 지금 자에서 빠져 있는 채널이다.
        extra = [
            all_units[src]
            for page, _ in retrieved.pages
            for src in page.sources
            if src in all_units and src not in have
        ]

        _, cur_loc = fabricated_citations(answer, units)
        _, new_loc = fabricated_citations(answer, units + extra)
        cur = {f"{k}{n}" for k, n in cur_loc}
        new = {f"{k}{n}" for k, n in new_loc}

        rec = _recorded_loc(result)
        if cur == rec:
            same += 1
        else:
            diff += 1
            if len(mismatch) < 8:
                mismatch.append((row["cid"], sorted(rec), sorted(cur)))

        if cur:
            (still if new else rescued).append(
                (row["k"], row["cid"], sorted(new or cur), row["q"][:52])
            )

    print(f"## 현행 재현 검증   일치 {same} / 불일치 {diff}   ({len(rows)}건)")
    for cid, rec, cur in mismatch:
        print(f"   {cid}  기록={rec}  재현={cur}")
    if diff:
        print("   ⚠ 불일치가 있으면 아래 재판정은 그만큼 못 믿는다.")
    print()
    print(f"## 지어냄 판정   현행 {len(rescued) + len(still)}건  →  위키 채널 반영 {len(still)}건")
    print(f"   무죄 {len(rescued)}건 · 그대로 남은 것 {len(still)}건")
    print()
    print("### 그대로 남은 것 = 진짜 조사 대상 (빈도순)")
    for k, cid, keys, q in sorted(still, reverse=True):
        print(f"  k={k:>2}  {cid}  {','.join(keys):<18} {q}")


asyncio.run(main())
