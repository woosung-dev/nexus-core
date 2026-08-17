# RAG 교체 — 봇 11 의 규정집 v19 · 대사전 v2 를 v20 · v4 로 갈아끼운다.
#
# **쓰기 작업이다.** 기본은 사전점검(읽기 전용)이고, 실제 교체는 --confirm 을 줘야 한다.
#
# 운영 업로드 경로(GeminiRAGService.upload_document)를 그대로 쓴다 — custom_metadata 가
# `bot_id`(numeric) + `content_sha256`(string) 로 박혀야 검색 필터(`bot_id = 11`)에 걸린다.
# 직접 SDK 를 부르면 이 규약이 어긋날 수 있어 서비스 함수를 통한다.
#
# admin/bots.py 는 업로드 전에 원본을 R2 에도 넣는다. 여기서는 그 단계를 생략한다 —
# 원본이 ~/Downloads 에 있고, R2 는 키를 uuid4 로 랜덤화해 매핑을 남기지 않으므로
# (AGENTS.md §3-5) 복구 경로로서의 가치가 원본 보유보다 낮다.
#
# 순서: 삭제 → 업로드. 두 판이 동시에 색인돼 조문 번호가 충돌하는 구간을 만들지 않는다.
# 봇 11 은 테스트 봇이라 라이브 트래픽이 없다(라이브 봇은 2022 국제규정집 기반).
import argparse
import asyncio
import hashlib
import json
import logging
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))

for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

DIR = Path(__file__).parent
DL = Path.home() / "Downloads"
BOT = 11

# (지울 것, 넣을 것)
SWAP = [
    {
        "old_display": "신한국_축복가정행정_규정집_개정초안_2026v19_입회원서규정보완 - new.pdf",
        "new_path": DL / "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf",
    },
    {
        "old_display": "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_원본틀_v2 - new.pdf",
        "new_path": DL / "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf",
    },
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nfc(s: str) -> str:
    """스토어의 display_name 도 macOS 파일명도 NFD 로 온다. 비교 전에 반드시 정규화한다
    (AGENTS.md §5 — 정규화 없이 비교하면 거짓음성이 난다). 실제로 여기서 한 번 걸렸다."""
    return unicodedata.normalize("NFC", s or "")


async def snapshot(rag):
    docs = await rag.list_documents(BOT)
    return [{"file_id": d.file_id, "display_name": d.display_name,
             "size_bytes": d.size_bytes, "created_at": d.created_at} for d in docs]


async def main(confirm):
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    print(f"store: {store}\n")

    before = await snapshot(rag)
    print(f"[사전] 봇 {BOT} 문서 {len(before)}건")
    for d in before:
        print(f"   {d['file_id']:<40} {d['size_bytes']:>10} {d['display_name']}")
    print()

    # ── 사전 점검 ────────────────────────────────────────────────
    problems = []
    plan = []
    for s in SWAP:
        hit = [d for d in before if nfc(d["display_name"]) == nfc(s["old_display"])]
        if len(hit) != 1:
            problems.append(f"삭제 대상 '{s['old_display']}' 가 {len(hit)}건 (1건이어야 함)")
            continue
        p = s["new_path"]
        if not p.exists():
            problems.append(f"새 파일 없음: {p}")
            continue
        head = p.open("rb").read(5)
        if head != b"%PDF-":
            problems.append(f"PDF 가 아님: {p.name} (헤더 {head!r})")
            continue
        plan.append({"delete": hit[0], "upload": p, "sha256": sha(p),
                     "size": p.stat().st_size})

    if len(before) != len(SWAP):
        problems.append(f"봇 {BOT} 문서가 {len(before)}건 — 예상 {len(SWAP)}건. "
                        f"의도치 않은 문서가 있는지 확인할 것")

    print("[계획]")
    for x in plan:
        d = x["delete"]
        print(f"   삭제 {d['display_name']}")
        print(f"        └ file_id={d['file_id']} size={d['size_bytes']}")
        print(f"   등록 {x['upload'].name}")
        print(f"        └ size={x['size']} sha256={x['sha256'][:16]}…")
    print()

    if problems:
        print("⚠ 사전 점검 실패 — 진행하지 않는다:")
        for p in problems:
            print(f"   · {p}")
        raise SystemExit(1)
    print("사전 점검 통과.")

    if not confirm:
        print("\n(--confirm 없음 — 읽기 전용으로 끝낸다)")
        return

    # ── 실행 ────────────────────────────────────────────────────
    log = {"started": datetime.now(timezone.utc).isoformat(), "store": store,
           "bot": BOT, "before": before, "steps": []}

    print("\n[실행] 삭제 → 업로드")
    for x in plan:
        d = x["delete"]
        print(f"  삭제 중… {d['display_name'][:50]}", flush=True)
        await rag.delete_document(BOT, d["file_id"])
        log["steps"].append({"op": "delete", "file_id": d["file_id"],
                             "display_name": d["display_name"]})
        print("    삭제 완료", flush=True)

    for x in plan:
        p = x["upload"]
        print(f"  업로드 중… {p.name[:50]} ({x['size']/1e6:.1f}MB)", flush=True)
        # display_name 은 NFC 로 박는다 — 스토어에 NFD/NFC 가 섞이면 이후 대조가 또 어긋난다.
        await rag.upload_document(
            bot_id=BOT, file_data=p.read_bytes(), filename=nfc(p.name),
            display_name=nfc(p.name), mime_type="application/pdf")
        log["steps"].append({"op": "upload", "display_name": nfc(p.name),
                             "size_bytes": x["size"], "sha256": x["sha256"]})
        print("    업로드 요청 완료 (색인은 Gemini 서버에서 비동기)", flush=True)

    after = await snapshot(rag)
    log["after"] = after
    log["finished"] = datetime.now(timezone.utc).isoformat()
    (DIR / "_ragswap.json").write_text(json.dumps(log, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

    print(f"\n[사후] 봇 {BOT} 문서 {len(after)}건")
    for d in after:
        print(f"   {d['file_id']:<40} {d['size_bytes']:>10} {d['display_name']}")
    print(f"\n→ {DIR/'_ragswap.json'}")
    print("색인 완료 여부는 _ragverify.py 로 확인한다.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="실제로 삭제·업로드한다")
    asyncio.run(main(ap.parse_args().confirm))
