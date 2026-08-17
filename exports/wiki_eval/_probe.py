# 1단 검색기 진단 — dense / BM25 / hybrid 를 나란히 놓는다. Gemini 호출 = 질의당 임베딩 1회.
#
# 이 스크립트가 답해야 하는 질문 하나: **하이브리드로 순위가 뒤집히는가.**
# dense-only 는 「가정회비」 질문에 `유아회비` 를 1위로 내놓았다. 의미가 비슷해서다.
# BM25 는 「가정회비」를 글자로 본다. 둘을 합쳐 정답 `가정공과금` 이 앞서면 진단이 맞은 것이다.
#
# 사용: cd backend && uv run python ../exports/wiki_eval/_probe.py
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

from app.services.wiki.store import get_index  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOT_ID = 11

QUERIES = [
    "가정회비 미납이 200만원이면 얼마를 내야 하나요?",  # 세션 지정 검증 케이스
    "축복을 받고 가정회비를 내지 않으면 얻게 되는 불이익이 있어?",  # 45문항 #41
]

# 이 두 쪽의 상대 순위가 판정이다.
WATCH = ("가정공과금", "유아회비")


def rank_of(rows: list[tuple[str, float]], slug: str) -> str:
    for i, (s, _) in enumerate(rows, 1):
        if s == slug:
            return f"{i}위"
    return "권외"


async def main() -> None:
    index = await get_index(BOT_ID)
    print(
        f"봇 {BOT_ID} · 스케일: "
        + " · ".join(f"{n} {len(s.ids)}건" for n, s in index.scales.items())
    )

    for q in QUERIES:
        print(f"\n{'=' * 78}\n질의: {q}\n{'=' * 78}")
        ret = await index.search(q, top_k=3)

        dense = ret.debug["page_dense"]
        lex = ret.debug["page_bm25"]
        hybrid = [(p.slug, round(s, 4)) for p, s in ret.pages]

        for label, rows in (("dense-only", dense), ("BM25-only", lex), ("hybrid", hybrid)):
            print(f"\n  [{label}]")
            for i, (slug, score) in enumerate(rows, 1):
                mark = " ←" if slug in WATCH else ""
                print(f"    {i}. {slug:<28} {score}{mark}")

        # 판정 한 줄
        verdict = []
        for label, rows in (("dense", dense), ("bm25", lex), ("hybrid", hybrid)):
            verdict.append(f"{label} {WATCH[0]}={rank_of(rows, WATCH[0])} {WATCH[1]}={rank_of(rows, WATCH[1])}")
        print("\n  판정: " + " | ".join(verdict))

        print(f"\n  [RRF 유닛 상위 8] (팔 B′ 가 주입할 후보)")
        for i, (u, s) in enumerate(ret.ranked_units[:8], 1):
            print(f"    {i}. {u.src_id:<10} {round(s, 4)}  {u.locator[:46]}")
        print(f"  [팔 B 주입량] 상위 3쪽 sources 합집합 = {len(ret.units)}건")


if __name__ == "__main__":
    asyncio.run(main())
