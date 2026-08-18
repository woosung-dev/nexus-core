"""file_search 경로에 어휘 경로와 같은 자를 대 본 기록 — **결론: 이 자로는 못 잰다.**

## 왜 만들었나

어휘 경로 재판정(`_rejudge_pages.py`)에서 「지어냄 57건 → 0건」이 나왔다. file_search
경로도 같은 자로 재려 했다.

## 코드로 이미 확정되는 것 (측정 이전)

    strict_mode.fabricated_citations(answer, units):
        if not units: return set(), set()      # ← file_search 턴은 여기서 즉시 빠진다

`trace.units` 는 `chat_service` 의 **lexical 분기에서만** 채워진다. 그래서 file_search
턴은 **항상 「지어냄 0」으로 기록된다.** 무보호가 아니라 **무측정**이다.
게이트(`has_direct_citation`)도 「인용이 하나라도 있나」만 본다 — 답변이 짚은 조문과
검색이 물어온 청크를 대조하지 않는다.

## 측정 구성 (2026-08-18)

공용 스토어는 안 건드렸다(다른 세션이 게이트 작업 중). `FILE_SEARCH_STORE_NAME` 을
`nexus-fs-measure-0818` 로 갈아끼워 격리 스토어를 만들고, **어휘 경로가 쓰는 바로 그
250 유닛**을 문서 2개(규정집v20·대사전v4)로 합쳐 올렸다. PDF 원본을 올리면 청킹이 달라져
경로가 아니라 청킹을 재게 된다. 봇 29·프롬프트 1,481자·같은 모델, replay 상위 45문항.

## 결과와 그 해석

    file_search 45건
      grounding 청크 0건        17건 (37.8%)
      본문에 조문 표기 없음      29건 (64.4%)
      「주입 밖 근거」           10건 (22.2%)
      has_direct_citation 통과  28건

    같은 45문항 · 어휘 경로
      본문에 조문 표기 없음      24건 (53.3%)
      현행 자 「지어냄」          3건 (6.7%)  →  위키 채널 반영 후 0건

**22.2% 를 지어냄률로 읽으면 안 된다.** 10건을 가르면 3건은 청크 0건이라 근거 풀이 비어
무엇을 대든 「밖」이 되고, 나머지 7건은 전부 **인접 조문**이다(풀=조33·답변=조32,
풀=조64·답변=조65 …). 청크 2건을 직접 열어 확인한 결과 **본문이 정확히 800자**
(`gemini._to_citation` 의 `ctx.text[:800]`)이고 **문장 중간에서 시작해 중간에서 끊긴다** —
`## [reg-N] …` 조문 표제가 창 밖으로 나간다. 즉 자가 보는 근거 풀이 열쇠구멍이다.

## 그래서 남는 결론

1. file_search 경로의 지어냄률은 **현재 계측 불가**다. 어휘 경로와 실패 원인만 다르다
   (어휘=위키 채널 미기록 · file_search=청크 800자 절단 + grounding 미보고 37.8%).
2. 재려면 둘이 필요하다 — 청크를 자르지 않고(또는 문서 내 위치를 함께) 기록할 것,
   grounding 0건 보고를 먼저 해소할 것.
3. 게이트는 이 대조를 아예 안 하므로, 계측을 고치기 전까지 이 경로의 위험은 **모르는 상태**다.

## 재현

    python exports/replay_2026-08/_fs_ruler.py setup    # 격리 스토어 + 문서 2건
    python exports/replay_2026-08/_fs_ruler.py run 45   # 측정 (문항당 1회, 4초 간격)
    python exports/replay_2026-08/_fs_ruler.py clean    # 격리 스토어 삭제

⚠ `NEXUS_DATA` 로 exports 데이터 뿌리를 준다(워크트리에는 exports 데이터가 없다).
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv("NEXUS_DATA", REPO))
STORE = "nexus-fs-measure-0818"
os.environ["FILE_SEARCH_STORE_NAME"] = STORE
os.environ.setdefault("WIKI_ROOT", str(DATA / "exports" / "wiki_2026-08"))
sys.path.insert(0, str(REPO / "backend"))
# `.env` 는 `backend/` 기준으로 읽힌다 — 레포 루트에서 실행하면 DATABASE_URL·GEMINI_API_KEY 가
# 없다고 죽는다. 어디서 부르든 되게 여기서 옮긴다.
os.chdir(REPO / "backend")

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.bot import Bot  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from app.services.strict_mode import _locator_keys, has_direct_citation  # noqa: E402
from app.services.wiki.store import get_index  # noqa: E402

BOT = 29
OUT = DATA / "exports" / "replay_2026-08" / "_fs_result.json"


def _doc(units: dict, prefix: str, title: str) -> bytes:
    ids = sorted((k for k in units if k.startswith(prefix)), key=lambda s: int(s.split("-")[1]))
    parts = [f"# {title}\n"]
    for sid in ids:
        u = units[sid]
        parts.append(f"\n## [{sid}] {u.doc} {u.locator}\n{u.text}\n")
    return "".join(parts).encode("utf-8")


async def setup() -> None:
    idx = await get_index(BOT)
    svc = GeminiRAGService()
    print("격리 스토어:", await svc.ensure_store())
    have = {d.display_name for d in await svc.list_documents(BOT)}
    for prefix, title, name in [
        ("reg-", "신한국 축복가정행정 규정집 개정초안 2026 (v20)", "규정집v20.txt"),
        ("glo-", "축복가정행정 용어 대사전 (v4)", "대사전v4.txt"),
    ]:
        if name in have:
            print("  건너뜀", name)
            continue
        blob = _doc(idx.units, prefix, title)
        print(f"  업로드 {name} {len(blob):,}바이트")
        await svc.upload_document(bot_id=BOT, file_data=blob, filename=name,
                                  display_name=name, mime_type="text/plain")
    for _ in range(40):
        docs = await svc.list_documents(BOT)
        if len(docs) >= 2:
            print("→ 준비 완료:", [d.display_name for d in docs])
            return
        await asyncio.sleep(15)
    print("⚠ 인덱싱 미완")


async def run(n: int) -> None:
    rows = json.loads((DATA / "exports/replay_2026-08/_triage_replay_0815.json").read_text())["rows"]
    rows.sort(key=lambda r: -r["k"])
    picked = rows[:n]
    async with async_session() as db:
        bot = (await db.execute(select(Bot).where(Bot.id == BOT))).scalar_one()
        sp, model = bot.system_prompt or "", bot.llm_model
    print(f"봇 {BOT} · {model} · 프롬프트 {len(sp)}자 · {len(picked)}문항", flush=True)

    svc = GeminiRAGService()
    out = []
    for i, r in enumerate(picked, 1):
        t0 = time.time()
        try:
            resp = await svc.generate_with_rag(bot_id=BOT, prompt=r["q"],
                                               system_prompt=sp, model_name=model)
        except Exception as e:
            print(f"  [{i}] {r['cid']} 실패 {type(e).__name__}: {str(e)[:80]}", flush=True)
            await asyncio.sleep(8)
            continue
        a = resp.answer or ""
        cited = {f"{k}{m}" for k, m in _locator_keys(a)}
        # 판정은 `full_content`(절단 없음)로 한다. `content` 는 800자 표시용이라
        # 조문 표제가 창 밖으로 나가 거짓 불일치를 낸다.
        pool = " ".join(
            (c.title or "") + " " + (c.full_content or c.content or "") for c in resp.citations
        )
        avail = {f"{k}{m}" for k, m in _locator_keys(pool)}
        out.append({
            "cid": r["cid"], "k": r["k"], "q": r["q"], "answer": a,
            "n_citations": len(resp.citations), "direct": has_direct_citation(resp.citations),
            # ⚠ 청크 길이를 반드시 남긴다 — 800 이면 절단이라 `avail` 이 열쇠구멍이다.
            "chunk_lens": [len(c.content or "") for c in resp.citations],
            "cited": sorted(cited), "avail": sorted(avail),
            "fake": sorted(cited - avail),
            "titles": sorted({c.title for c in resp.citations if c.title}),
        })
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [{i}/{len(picked)}] {r['cid']} 청크{len(resp.citations)} "
              f"짚음{len(cited)} 밖{len(out[-1]['fake'])} {time.time()-t0:.1f}s", flush=True)
        await asyncio.sleep(4)

    n_ = len(out)
    fake = [o for o in out if o["fake"]]
    zero = [o for o in fake if o["n_citations"] == 0]
    trunc = [o for o in fake if any(x >= 800 for x in o["chunk_lens"])]
    print(f"\n## file_search {n_}건")
    print(f"  grounding 청크 0건       {sum(1 for o in out if not o['n_citations'])}건")
    print(f"  본문에 조문 표기 없음     {sum(1 for o in out if not o['cited'])}건")
    print(f"  「주입 밖」              {len(fake)}건")
    print(f"    ↳ 청크 0 이라 판정불가  {len(zero)}건")
    print(f"    ↳ 800자 절단 청크 포함  {len(trunc)}건  ← 이것도 판정불가")
    print(f"  has_direct_citation 통과 {sum(1 for o in out if o['direct'])}건")


async def clean() -> None:
    svc = GeminiRAGService()
    name = await svc.ensure_store()
    from google import genai
    from app.core.config import get_settings
    client = genai.Client(api_key=get_settings().GEMINI_API_KEY.get_secret_value())
    await client.aio.file_search_stores.delete(name=name, config={"force": True})
    print("삭제:", name)


CMD = sys.argv[1] if len(sys.argv) > 1 else "run"
asyncio.run({"setup": setup, "clean": clean}.get(CMD, lambda: run(
    int(sys.argv[2]) if len(sys.argv) > 2 else 45))())
