# 문항별 RAG 검색 근거(청크 제목+내용) 캡처 — "근거 인용하며 답하라"로 grounding 최대화
# 사용: set -a; source backend/.env; set +a; backend/.venv/bin/python exports/_probe_retrieval_capture.py
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

BASE = Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_redteam/04_평가·프로브")
ANS = BASE / "probe_answers_qt.json"
OUT = BASE / "retrieval_qt.json"
MODEL = "gemini-3.1-flash-lite"
STAGING_BOT = 3
# grounding 강제 — 검색 청크를 최대한 노출시키기 위한 중립 지시
GROUNDING_SP = "너는 자료 검색기다. 제공된 [2022 ver.] 축복행정 국제 규정집·공문 문서에서 질문과 관련된 근거 조항을 찾아 인용하며 간단히 답하라. 자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라."

QUESTIONS = json.load(open(ANS, encoding="utf-8"))["questions"]


async def call(rag, q, tries=5):
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(
                rag.generate_with_rag(bot_id=STAGING_BOT, prompt=q, system_prompt=GROUNDING_SP,
                                      model_name=MODEL, temperature=0.2, max_tokens=900),
                timeout=70)
            cites = [{"title": c.title, "content": (c.content or "")[:500]} for c in resp.citations]
            return resp.answer, cites
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:80]}", []
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()
    out = []
    for q in QUESTIONS:
        ans, cites = await call(rag, q["q"])
        out.append({"qid": q["id"], "area": q["area"], "q": q["q"], "golden": q["golden"],
                    "retrieval_answer": ans, "retrieved": cites})
        print(f"  Q{q['id']:>2} {q['area'][:20]:<20} 청크 {len(cites)}개", flush=True)
        await asyncio.sleep(6)
    OUT.write_text(json.dumps({"meta": {"model": MODEL, "staging_bot": STAGING_BOT, "note": "grounding 강제 캡처 — 응답엔 근거로 쓴 청크만 노출(top-k 전체 아님)"},
                               "items": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    got = sum(1 for x in out if x["retrieved"])
    print(f"\n저장: {OUT}  (근거 포착 {got}/{len(out)}문항)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
