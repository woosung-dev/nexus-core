# D-1(bot 8)+3.5-flash-lite 로 답변→인용(supports)→근거구절(evidence) 전체 경로를 실제 코드로 돌려보는 프로브
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
logging.disable(logging.INFO)

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

BOT_ID = 8
MODEL = "gemini-3.5-flash-lite"
OUT = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1/_probe_e2e.json")
N = 5


async def main():
    async with async_session() as s:
        bot = (await s.execute(text("SELECT system_prompt FROM bots WHERE id=:b"),
                               {"b": BOT_ID})).mappings().first()
        rows = (await s.execute(text(
            "SELECT id, question FROM redteam_question_groups WHERE risk='상' ORDER BY id LIMIT :n"),
            {"n": N})).mappings().all()

    rag = GeminiRAGService()
    out = []
    for r in rows:
        t0 = time.perf_counter()
        resp = await rag.generate_with_rag(
            bot_id=BOT_ID, prompt=r["question"], system_prompt=bot["system_prompt"],
            model_name=MODEL)
        answer_ms = (time.perf_counter() - t0) * 1000

        seg_total = sum(len(c.segments) for c in resp.citations)
        # 여기부터가 답변 전송 이후 비동기로 도는 구간이다.
        t1 = time.perf_counter()
        filled = await rag.fill_evidence(resp.citations, resp.answer, MODEL)
        ev_ms = (time.perf_counter() - t1) * 1000

        # 불변식 — 화면에 칠할 구절은 반드시 청크 원문의 부분문자열이어야 한다.
        violations = [
            (c.title, e) for c in resp.citations for e in c.evidence
            if e not in (c.content or "")
        ]
        anchored = sum(1 for c in resp.citations for s in c.segments if s in resp.answer)

        print(f"[{r['id']}] 답변 {answer_ms/1000:.1f}s / 인용 {len(resp.citations)} "
              f"구간 {seg_total}(본문앵커 {anchored}) / 근거추출 {ev_ms/1000:.1f}s "
              f"카드 {filled}/{len(resp.citations)} / 불변식위반 {len(violations)}")

        out.append({
            "gid": r["id"], "q": r["question"], "answer": resp.answer,
            "answer_ms": answer_ms, "evidence_ms": ev_ms,
            "citations": [c.model_dump() for c in resp.citations],
            "violations": violations,
        })
        await asyncio.sleep(5)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    cards = [c for o in out for c in o["citations"]]
    with_ev = [c for c in cards if c["evidence"]]
    print(f"\n=== 요약 ===")
    print(f"  카드 {len(cards)}개 중 형광펜 {len(with_ev)} ({len(with_ev)/len(cards):.1%})")
    print(f"  불변식 위반(원문에 없는 구절) 총 {sum(len(o['violations']) for o in out)}건")
    print(f"  근거추출 평균 {sum(o['evidence_ms'] for o in out)/len(out)/1000:.1f}s (비동기)")
    print(f"  저장: {OUT}")


asyncio.run(main())
