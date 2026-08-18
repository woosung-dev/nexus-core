# KEEP 20 FAQ를 FAQ 우회로 RAG에 직접 질의(Loop1=가/5, Loop2=나/3) → RAG가 답하는지 수집
import os
import sys
import json
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
for _l in (ROOT / "backend/.env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

KEEP_IDS = [1, 2, 3, 4, 6, 7, 8, 9, 10, 18, 19, 20, 21, 22, 23, 24, 31, 33, 34, 35]
LOOPS = [(1, 5, "가"), (2, 3, "나")]  # (loop_no, bot_id, tag)
OUT = ROOT / "exports/faq_test/rag_probe_results.json"


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot
    from app.services.rag.gemini import GeminiRAGService

    full = {o["id"]: o for o in json.load(open(ROOT / "exports/faq_test/faqs_fullcols.json"))}
    canon = {f["id"]: f for f in json.load(open(ROOT / "exports/faq_test/faqs_export.json"))}
    rag = GeminiRAGService()

    # 사전: 가/나 17종 확인
    async with async_session() as s:
        bots = {}
        for _, bid, tag in LOOPS:
            b = await crud_bot.get_active_bot(s, bid)
            nd = len(await rag.list_documents(bid))
            print(f"  {tag}/id{bid} '{b.name}' RAG문서={nd} model={b.llm_model}")
            assert nd >= 17, f"{tag} RAG 17종 아님({nd}) — 중단"
            bots[bid] = b

    results = json.load(open(OUT)) if OUT.exists() else []
    done = {(r["id"], r["loop"]) for r in results}

    async with async_session() as s:
        for fid in KEEP_IDS:
            q = canon[fid]["question"]
            for loop_no, bid, tag in LOOPS:
                if (fid, loop_no) in done:
                    continue
                b = bots[bid]
                try:
                    resp = await rag.generate_with_rag(
                        bot_id=bid, prompt=q, system_prompt=b.system_prompt,
                        model_name=b.llm_model, history=None,
                    )
                    cited = sorted({(c.title or "")[:60] for c in resp.citations if c.title})
                    rec = {"id": fid, "질문": q, "golden": canon[fid]["answer"],
                           "이슈요약": full[fid]["이슈요약"], "loop": loop_no, "bot": tag,
                           "answer": resp.answer, "cited_docs": cited}
                    print(f"  [id{fid} L{loop_no}/{tag}] ans {len(resp.answer)}자, 인용 {len(cited)}종: {cited[:3]}")
                except Exception as e:
                    rec = {"id": fid, "질문": q, "golden": canon[fid]["answer"],
                           "이슈요약": full[fid]["이슈요약"], "loop": loop_no, "bot": tag,
                           "answer": f"[ERROR] {type(e).__name__}: {e}", "cited_docs": []}
                    print(f"  [id{fid} L{loop_no}/{tag}] ERROR {type(e).__name__}: {str(e)[:50]}")
                results.append(rec)
                json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=1)
                await asyncio.sleep(12)

    ok = sum(1 for r in results if not r["answer"].startswith("[ERROR]"))
    print(f"\n생성 완료 {ok}/{len(results)} → {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
