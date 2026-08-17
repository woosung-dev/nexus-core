# RAG 교체 검증 — 읽기 전용.
#
# 확인 셋:
#   ① 봇 11 문서가 새 판 2건뿐인가 · 스토어 전체에 구판이 남아 있지 않은가
#   ② custom_metadata 가 규약대로인가 — bot_id(numeric)=11 · content_sha256 이 원본과 일치
#      (이게 어긋나면 metadata_filter="bot_id = 11" 에 안 걸려 검색이 통째로 빈손이 된다)
#   ③ 색인 상태 — 비동기라 업로드 직후에는 아직 안 끝나 있을 수 있다
import asyncio
import hashlib
import logging
import sys
import unicodedata
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))
for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

DL = Path.home() / "Downloads"
BOT = 11
EXPECT = {
    "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf":
        DL / "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf",
    "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf":
        DL / "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf",
}
STALE = ["2026v19", "원본틀_v2"]


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


async def main():
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    client = rag._client

    rows = []
    async for d in await client.aio.file_search_stores.documents.list(
            parent=store, config={"page_size": 20}):
        cm = {m.key: (m.numeric_value if m.numeric_value is not None else m.string_value)
              for m in (d.custom_metadata or [])}
        rows.append({
            "name": (d.name or "").rsplit("/", 1)[-1],
            "display_name": nfc(d.display_name),
            "size": getattr(d, "size_bytes", None),
            "bot_id": cm.get("bot_id"),
            "sha": cm.get("content_sha256"),
            "state": str(getattr(d, "state", None)),
        })

    print(f"스토어 전체 문서 {len(rows)}건\n")

    mine = [r for r in rows if r["bot_id"] == BOT]
    print(f"① 봇 {BOT} 문서 {len(mine)}건")
    for r in mine:
        print(f"   {r['display_name']}")
        print(f"      file_id={r['name']} size={r['size']} state={r['state']}")
    ok1 = len(mine) == len(EXPECT) and {r["display_name"] for r in mine} == set(EXPECT)
    print(f"   → {'통과' if ok1 else '⚠ 실패'}\n")

    # 판정 범위는 봇 11 이다. 다른 봇의 구판은 각자 실험의 기준선이라 건드리지 않는다
    # (봇 8 '테스트 봇 D-1' = D복제+2026규정집 단독 구성. v19 가 그 실험의 기준선이다).
    stale_mine = [r for r in rows
                  if r["bot_id"] == BOT and any(s in r["display_name"] for s in STALE)]
    stale_other = [r for r in rows
                   if r["bot_id"] != BOT and any(s in r["display_name"] for s in STALE)]
    print(f"② 봇 {BOT} 구판 잔존 — {len(stale_mine)}건")
    for r in stale_mine:
        print(f"   ⚠ {r['display_name']}")
    print(f"   → {'통과' if not stale_mine else '⚠ 실패'}")
    if stale_other:
        print(f"   (참고) 다른 봇의 구판 {len(stale_other)}건 — 교체 대상 아님:")
        for r in stale_other:
            print(f"      봇 {int(r['bot_id'])}: {r['display_name']}")
    print()
    stale = stale_mine

    print("③ custom_metadata 규약")
    ok3 = True
    for r in mine:
        src = EXPECT.get(r["display_name"])
        local = hashlib.sha256(src.read_bytes()).hexdigest() if src and src.exists() else None
        match = (r["sha"] == local)
        ok3 &= bool(match) and r["bot_id"] == BOT
        print(f"   {r['display_name'][:46]}")
        print(f"      bot_id={r['bot_id']} (numeric) · sha256 원본일치={match}")
        if not match:
            print(f"         스토어 {r['sha']}\n         원본   {local}")
    print(f"   → {'통과' if ok3 else '⚠ 실패'}\n")

    states = {r["state"] for r in mine}
    print(f"④ 색인 상태: {states}")
    print("   ACTIVE 가 아니면 아직 색인 중이다 — 잠시 후 다시 실행한다.")

    print(f"\n종합: {'모두 통과' if (ok1 and not stale and ok3) else '⚠ 확인 필요'}")


if __name__ == "__main__":
    asyncio.run(main())
