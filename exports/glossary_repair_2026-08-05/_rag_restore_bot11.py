# 봇 11(테스트 봇 D-1 ver2) RAG 복구 — 새 Gemini 키(다른 프로젝트) 기준.
#
# 배경: 키가 다른 프로젝트로 바뀌면서 File Search 스토어가 통째로 갈렸다.
#   옛 스토어 fileSearchStores/nexuscoreknowledgebase-9gjebfinkrvz  (189 문서)
#   새 스토어 fileSearchStores/nexuscoreknowledgebase-5gkmi10atfin  (86 문서)
# 앞선 v19·v2 → v20·v4 교체는 **옛 스토어**에 들어갔다. 새 키에서는 보이지 않는다.
#
# 봇 11 의 의도된 구성은 문서 2건이다(v19 규정집 + v2 대사전 → 이번에 v20 + v4 로 갱신).
# 그런데 새 스토어의 봇 11 에는 `[2022_ver.] 축복행정 국제 규정집.pdf` 1건이 붙어 있다 —
# 이 봇이 가진 적 없는 문서다. 그대로 두면 **조문 번호 체계가 다른 규정집 두 권**이
# 한 봇에 공존해 실험이 오염된다. 그래서 지운다.
#   되돌리려면: exports/blessing_vs_abc_2026-06-12/rag_reregister/docs/ 에 원본이 있다.
#
# 라이브 봇(4·6·7)은 건드리지 않는다 — 사용자 지시(2026-08-05).
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
BOT_NAME = "테스트 봇 D-1 ver2"

WANT = [
    DL / "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf",
    DL / "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf",
]
# 봇 11 이 가진 적 없는 문서 — 조문 번호 체계 충돌을 막기 위해 제거
DROP = ["[2022_ver.] 축복행정 국제 규정집.pdf"]


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


async def main(confirm):
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    print(f"store: {store}")
    if store.endswith("9gjebfinkrvz"):
        raise SystemExit("⚠ 옛 스토어가 잡혔다. .env 의 GEMINI_API_KEY 를 확인할 것.")
    print(f"대상: 봇 {BOT} '{BOT_NAME}'\n")

    cur = await rag.list_documents(BOT)
    print(f"[사전] 봇 {BOT} 문서 {len(cur)}건")
    for d in cur:
        print(f"   {d.file_id:<34} {d.size_bytes:>10}  {nfc(d.display_name)}")

    to_drop = [d for d in cur if nfc(d.display_name) in {nfc(x) for x in DROP}]
    keep = [d for d in cur if d not in to_drop]

    problems = []
    for p in WANT:
        if not p.exists():
            problems.append(f"원본 없음: {p}")
        elif p.open("rb").read(5) != b"%PDF-":
            problems.append(f"PDF 아님: {p.name}")
    already = {nfc(d.display_name) for d in cur}
    plan_up = [p for p in WANT if nfc(p.name) not in already]

    print(f"\n[계획]")
    for d in to_drop:
        print(f"   삭제 {nfc(d.display_name)}  (봇 {BOT} 이 가진 적 없는 문서)")
    for p in plan_up:
        print(f"   등록 {p.name}  ({p.stat().st_size/1e6:.1f}MB)")
    if keep:
        print(f"   유지 {[nfc(d.display_name) for d in keep]}")
    if not plan_up and not to_drop:
        print("   변경 없음")

    if problems:
        print("\n⚠ 사전 점검 실패:")
        for x in problems:
            print(f"   · {x}")
        raise SystemExit(1)
    print("\n사전 점검 통과.")

    if not confirm:
        print("(--confirm 없음 — 읽기 전용으로 끝낸다)")
        return

    log = {"started": datetime.now(timezone.utc).isoformat(), "store": store, "bot": BOT,
           "before": [{"file_id": d.file_id, "display_name": nfc(d.display_name),
                       "size_bytes": d.size_bytes} for d in cur], "steps": []}

    print("\n[실행]")
    for d in to_drop:
        print(f"  삭제 중… {nfc(d.display_name)[:46]}", flush=True)
        await rag.delete_document(BOT, d.file_id)
        log["steps"].append({"op": "delete", "file_id": d.file_id,
                             "display_name": nfc(d.display_name)})
        print("    완료", flush=True)

    for p in plan_up:
        data = p.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        print(f"  업로드 중… {p.name[:46]} ({len(data)/1e6:.1f}MB)", flush=True)
        await rag.upload_document(bot_id=BOT, file_data=data, filename=nfc(p.name),
                                  display_name=nfc(p.name), mime_type="application/pdf")
        log["steps"].append({"op": "upload", "display_name": nfc(p.name),
                             "size_bytes": len(data), "sha256": sha})
        print("    요청 완료 (색인은 비동기)", flush=True)

    after = await rag.list_documents(BOT)
    log["after"] = [{"file_id": d.file_id, "display_name": nfc(d.display_name),
                     "size_bytes": d.size_bytes} for d in after]
    log["finished"] = datetime.now(timezone.utc).isoformat()
    (DIR / "_rag_restore_bot11.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n[사후] 봇 {BOT} 문서 {len(after)}건")
    for d in after:
        print(f"   {d.file_id:<34} {d.size_bytes:>10}  {nfc(d.display_name)}")
    print(f"\n→ {DIR/'_rag_restore_bot11.json'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    asyncio.run(main(ap.parse_args().confirm))
