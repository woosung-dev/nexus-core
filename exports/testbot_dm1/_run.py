# 테스트 봇 D-1(bots.id=8)에 3주차 위험도 상·중 80그룹 대표질문을 운영동일 파라미터로 질의 → _answers.json (resume-safe)
import argparse
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
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1")
THROTTLE = 12  # 분당 쿼터(RPM) 보호


async def call(rag, sp, model, q, tries=5, max_tokens=2048):
    """운영과 동일하게 generate_with_rag 호출. 429/503 백오프. (answer, [unique titles], n_cites) 반환."""
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(
                rag.generate_with_rag(bot_id=BOT_ID, prompt=q, system_prompt=sp,
                                      model_name=model, max_tokens=max_tokens),
                timeout=180)
            titles, seen = [], set()
            for c in resp.citations:
                t = (c.title or "").strip()
                if t and t not in seen:
                    seen.add(t)
                    titles.append(t)
            return resp.answer, titles, len(resp.citations)
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:100]}", [], 0
            wait = delay if ("503" in msg or "429" in msg) else 5
            await asyncio.sleep(wait)
            delay = min(int(delay * 1.5), 90)


async def main(limit, model_override, risks, tag, max_tokens):
    out = DIR / (f"_answers_{tag}.json" if tag else "_answers.json")
    # 봇 메타
    async with async_session() as s:
        row = (await s.execute(text(
            "SELECT id,name,system_prompt,llm_model FROM bots WHERE id=:b"),
            {"b": BOT_ID})).mappings().first()
        if not row:
            raise SystemExit(f"bots.id={BOT_ID} 없음")
        sp, model, name = row["system_prompt"], row["llm_model"], row["name"]

        # 대상: 지정 위험도 그룹 (상 먼저, 그다음 중, id 순). 대표 question 사용.
        grows = (await s.execute(text(
            "SELECT id, question, question_norm, risk FROM redteam_question_groups "
            "WHERE risk = ANY(:risks) "
            "ORDER BY CASE risk WHEN '상' THEN 0 WHEN '중' THEN 1 ELSE 2 END, id"),
            {"risks": risks})).mappings().all()

    if model_override:
        model = model_override  # 봇 저장 설정은 그대로, 이번 실행만 모델 교체
    groups = [{"gid": r["id"], "q": r["question"], "norm": r["question_norm"], "risk": r["risk"]}
              for r in grows]
    if limit:
        groups = groups[:limit]
    print(f"bot id={BOT_ID} '{name}' model={model} sp_len={len(sp)} max_tokens={max_tokens} → {out.name}", flush=True)
    print(f"대상 그룹 {len(groups)}건 (상 {sum(g['risk']=='상' for g in groups)} · "
          f"중 {sum(g['risk']=='중' for g in groups)})", flush=True)

    # resume: 오류 아닌 결과만 재사용
    done = {}
    if out.exists():
        prev = json.load(open(out))
        done = {r["gid"]: r for r in prev.get("results", []) if not r["answer"].startswith("[ERROR]")}
        print(f"이전 결과 {len(done)}건 재사용", flush=True)

    rag = GeminiRAGService()
    results = []
    for idx, g in enumerate(groups, 1):
        if g["gid"] in done:
            results.append(done[g["gid"]])
            continue
        t = time.time()
        ans, titles, n_cit = await call(rag, sp, model, g["q"], max_tokens=max_tokens)
        results.append({"gid": g["gid"], "norm": g["norm"], "risk": g["risk"], "q": g["q"],
                        "answer": ans, "citations": titles, "n_citations": n_cit})
        flag = "ERR" if ans.startswith("[ERROR]") else ("no-cite" if n_cit == 0 else "ok")
        print(f"[{idx:>2}/{len(groups)}] #{g['gid']} {g['risk']} {flag} "
              f"{time.time()-t:.1f}s len={len(ans)} cites={n_cit}", flush=True)
        # 증분 저장
        out.write_text(json.dumps(
            {"bot": {"id": BOT_ID, "name": name, "model": model},
             "count": len(results), "results": results},
            ensure_ascii=False, indent=1), encoding="utf-8")
        await asyncio.sleep(THROTTLE)

    # 루프 안 증분 저장은 '신규 호출 직후'에만 일어나므로, 마지막 신규 호출 이후 순번의
    # resume 항목들이 디스크에 안 써진 채 남는다. 종료 시 한 번 더 써서 전량을 보존한다.
    out.write_text(json.dumps(
        {"bot": {"id": BOT_ID, "name": name, "model": model},
         "count": len(results), "results": results},
        ensure_ascii=False, indent=1), encoding="utf-8")

    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    nocit = sum(1 for r in results if r["n_citations"] == 0 and not r["answer"].startswith("[ERROR]"))
    print(f"\n완료: {len(results)}건 저장 (오류 {errs} · 인용0 {nocit}) → {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="앞 N건만 (스모크용, 0=전량)")
    ap.add_argument("--model", default="", help="llm_model 오버라이드 (봇 저장값 대신 이번 실행만)")
    ap.add_argument("--risk", default="상,중", help="대상 위험도 (쉼표구분, 예: 상)")
    ap.add_argument("--tag", default="", help="출력 파일 접미사 (_answers_<tag>.json)")
    ap.add_argument("--bot-id", type=int, default=BOT_ID, help="테스트 봇 bots.id (기본 8=D-1, 10=D-2)")
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="출력 토큰 한도. Gemini 3.x는 thinking 이 이 예산을 함께 소모하므로 "
                         "3.5-flash 는 8192 권장(2048 이면 사고에 다 쓰여 답변이 잘림)")
    args = ap.parse_args()
    BOT_ID = args.bot_id  # 모듈 전역 재설정 (call/main 이 참조)
    risks = [x.strip() for x in args.risk.split(",") if x.strip()]
    asyncio.run(main(args.limit, args.model, risks, args.tag, args.max_tokens))
