# 백필 경로(search_citations)의 인용 보고율을 모델별로 비교하는 스윕 (읽기 전용 · DB 미변경)
#
# 목적: 2026-06-30 통제실험(6질문×2반복=12trial)의 "2.5-flash 단독 100%" 결론을
#       현재 라이브 프롬프트 + 실사용자 25문항으로 재현되는지 확인한다.
# 범위: 답변 생성 경로(generate_content)는 건드리지 않는다. 백필 호출만 비교하므로
#       3주차 레드팀 베이스(flash-lite + 동결 프롬프트)에 영향이 없다.
import asyncio
import json
import os
import pathlib
import sys
import time

BACKEND = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

import asyncpg  # noqa: E402

MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash"]
BOT_ID = 5  # 라이브 정밀형 (카카오 운영봇)
OUT = pathlib.Path(__file__).parent / "metrics.json"


def _neon_url() -> str:
    env = (BACKEND / ".env").read_text()
    line = next(l for l in env.splitlines() if "neon.tech" in l and "DATABASE_URL" in l)
    url = line.split("DATABASE_URL=", 1)[1].strip()
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("?ssl=require", "")


async def main():
    questions = [
        q["question"]
        for q in json.loads(
            (pathlib.Path(__file__).parents[1] / "rag_ad_probe_2026-07-02/questions.json").read_text()
        )
    ]

    # 라이브 봇5 의 실제 system_prompt 를 읽어온다 (읽기 전용).
    conn = await asyncpg.connect(_neon_url(), ssl="require")
    persona = await conn.fetchval("SELECT system_prompt FROM bots WHERE id = $1", BOT_ID)
    await conn.close()
    print(f"persona: {len(persona or '')}자 · 질문 {len(questions)}개 · 모델 {MODELS}")

    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    store = await svc.ensure_store()
    print(f"store: {store}\n")

    results: dict[str, list[dict]] = {m: [] for m in MODELS}
    for model in MODELS:
        for i, q in enumerate(questions):
            t0 = time.monotonic()
            try:
                cits = await svc.search_citations(
                    bot_id=BOT_ID, prompt=q, system_prompt=persona or "", model_name=model
                )
            except Exception as e:  # 쿼터/503 등은 기록만 하고 계속
                print(f"  [{model}] q{i} 실패: {type(e).__name__}: {e}")
                results[model].append({"q": q, "n": None, "error": str(e)[:120]})
                continue
            dt = time.monotonic() - t0
            results[model].append(
                {
                    "q": q,
                    "n": len(cits),
                    "files": sorted({c.title for c in cits if c.title}),
                    "pages": sorted({c.page_number for c in cits if c.page_number is not None}),
                    "sec": round(dt, 1),
                }
            )
            print(f"  [{model}] q{i:>2} n={len(cits):>2} {dt:>5.1f}s :: {q[:32]}")
            await asyncio.sleep(2)  # 무료 티어 분당 쿼터 완화

    summary = {}
    for m, rs in results.items():
        ok = [r for r in rs if r.get("n") is not None]
        cited = [r for r in ok if r["n"] > 0]
        summary[m] = {
            "n_questions": len(rs),
            "n_ok": len(ok),
            "n_errors": len(rs) - len(ok),
            "citation_rate": round(len(cited) / len(ok), 3) if ok else None,
            "avg_citations_when_cited": (
                round(sum(r["n"] for r in cited) / len(cited), 1) if cited else 0
            ),
            "n_with_pages": sum(1 for r in cited if r["pages"]),
        }

    OUT.write_text(
        json.dumps({"summary": summary, "per_question": results}, ensure_ascii=False, indent=1)
    )
    print("\n=== 요약 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"\n저장: {OUT}")


asyncio.run(main())
