# _evals(+bf_citations)를 redteam_testbot_evals 테이블에 upsert (dry-run 기본, --apply). Neon 실서버 대상, 백업 후 트랜잭션.
import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import asyncpg

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DIR = ROOT / "exports" / "testbot_dm1"
# bot_label/bot_id 는 _answers_<tag>.json 의 bot 객체에서 읽는다(하드코딩 아님).
DEFAULT_BOT_LABEL = "테스트 봇 D-1"
DEFAULT_BOT_ID = 8


def neon_dsn():
    import os
    v = os.environ.get("REDTEAM_DSN")
    if v:
        return v.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    env = (ROOT / "backend" / ".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        s = line.strip()
        if s.startswith("DATABASE_URL=") and not s.startswith("#"):
            return s.split("=", 1)[1].strip().replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    raise SystemExit("DATABASE_URL 미발견")


def host_of(dsn):
    m = re.search(r"@([^/:?]+)", dsn)
    return m.group(1) if m else "?"


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


async def run(apply, tag, run_label, bot_model_arg):
    evals_path = DIR / (f"_evals_{tag}.json" if tag else "_evals.json")
    answers_path = DIR / (f"_answers_{tag}.json" if tag else "_answers.json")
    results = json.load(open(evals_path))["results"]
    # 봇 정보(label/id/model)는 답변 파일의 bot 객체에서 (없으면 기본 D-1)
    bot = json.load(open(answers_path)).get("bot", {}) if answers_path.exists() else {}
    bot_label = bot.get("name") or DEFAULT_BOT_LABEL
    bot_id = bot.get("id") or DEFAULT_BOT_ID
    bot_model = bot_model_arg or bot.get("model")

    dsn = neon_dsn()
    mode = "🟥 APPLY(실쓰기)" if apply else "🟦 DRY-RUN(미쓰기)"
    print(f"{mode} · {host_of(dsn)} · 소스 {evals_path.name} {len(results)}건 · "
          f"bot='{bot_label}'(id{bot_id}, model={bot_model}) · run_label='{run_label}'")

    conn = await asyncpg.connect(dsn)
    try:
        # group_id → question_norm (재임포트 보존키)
        gids = [r["gid"] for r in results]
        norm = {r["id"]: r["question_norm"] for r in await conn.fetch(
            "SELECT id, question_norm FROM redteam_question_groups WHERE id = ANY($1::int[])", gids)}
        missing = [g for g in gids if g not in norm]
        if missing:
            print(f"⚠️ 그룹 없음 {len(missing)}건(스킵): {missing[:10]}")

        rows = [r for r in results if r["gid"] in norm]
        if not apply:
            print(f"\n[DRY-RUN] upsert 예정 {len(rows)}건 (상위 5 미리보기):")
            for r in rows[:5]:
                print(f"  #{r['gid']} 재발={r['risk_recur']} 독립={r['independent_risk']} "
                      f"AI={r['ai_rating']} 인용(직접 {len(r.get('citations',[]))}/근사 {r.get('bf_n',0)})")
            print("\n실제 반영은 --apply.")
            return

        # 백업 (같은 bot_label+run_label 기존 행)
        existing = await conn.fetch(
            "SELECT * FROM redteam_testbot_evals WHERE bot_label=$1 AND run_label=$2",
            bot_label, run_label)
        if existing:
            bpath = DIR / f"_apply_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
            bpath.write_text(json.dumps([dict(e) for e in existing], ensure_ascii=False, default=str, indent=1),
                             encoding="utf-8")
            print(f"백업 {len(existing)}행 → {bpath.name}")

        n = 0
        async with conn.transaction():
            for r in rows:
                await conn.execute(
                    """
                    INSERT INTO redteam_testbot_evals
                      (group_id, question_norm, run_label, bot_label, bot_id, bot_model, answer,
                       citations, bf_citations, risk_recur, risk_recur_detail,
                       independent_risk, independent_risk_detail, ai_rating, ai_rating_detail, eval_engine)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8::json,$9::json,$10,$11,$12,$13,$14,$15,'codex')
                    ON CONFLICT (group_id, bot_label, run_label) DO UPDATE SET
                      question_norm=EXCLUDED.question_norm, bot_id=EXCLUDED.bot_id, bot_model=EXCLUDED.bot_model,
                      answer=EXCLUDED.answer, citations=EXCLUDED.citations, bf_citations=EXCLUDED.bf_citations,
                      risk_recur=EXCLUDED.risk_recur, risk_recur_detail=EXCLUDED.risk_recur_detail,
                      independent_risk=EXCLUDED.independent_risk, independent_risk_detail=EXCLUDED.independent_risk_detail,
                      ai_rating=EXCLUDED.ai_rating, ai_rating_detail=EXCLUDED.ai_rating_detail, updated_at=now()
                    """,
                    r["gid"], norm[r["gid"]], run_label, bot_label, bot_id, bot_model, r.get("answer", ""),
                    json.dumps(r.get("citations", []), ensure_ascii=False),
                    json.dumps(r.get("bf_citations", []), ensure_ascii=False),
                    r.get("risk_recur"), r.get("risk_recur_detail") or "",
                    r.get("independent_risk"), r.get("independent_risk_detail") or "",
                    _num(r.get("ai_rating")), r.get("ai_rating_detail") or "",
                )
                n += 1
        print(f"✅ upsert 완료 {n}건 → redteam_testbot_evals (bot='{bot_label}', run_label='{run_label}')")
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 DB 쓰기 (미지정 시 dry-run)")
    ap.add_argument("--tag", default="", help="_evals_<tag>.json 반영")
    ap.add_argument("--run-label", default="테스트 1주차", help="회차 라벨 (모델 비교 시 분리)")
    ap.add_argument("--bot-model", default="", help="bot_model 명시(미지정 시 _answers 에서 추론)")
    args = ap.parse_args()
    asyncio.run(run(args.apply, args.tag, args.run_label, args.bot_model))
