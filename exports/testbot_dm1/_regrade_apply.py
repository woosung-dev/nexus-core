# 재채점(같은 시점) 결과를 Neon redteam_testbot_evals 에 반영 — 채점 6필드만 UPDATE(답변·인용 보존), 없는 행은 full INSERT
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import asyncpg

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DIR = ROOT / "exports" / "testbot_dm1"
GRADE_COLS = ("risk_recur", "risk_recur_detail", "independent_risk",
              "independent_risk_detail", "ai_rating", "ai_rating_detail")


def neon_dsn():
    env = (ROOT / "backend" / ".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        s = line.strip()
        if s.startswith("DATABASE_URL=") and not s.startswith("#"):
            return s.split("=", 1)[1].strip().replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    raise SystemExit("DATABASE_URL 미발견")


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


async def run(apply, eval_tag, run_label, bot_model):
    evals = json.load(open(DIR / f"_evals_{eval_tag}.json"))["results"]
    answers = json.load(open(DIR / f"_answers_{eval_tag}.json"))
    bot = answers.get("bot", {})
    bot_label, bot_id = bot.get("name", "테스트 봇 D-1"), bot.get("id", 8)
    bot_model = bot_model or bot.get("model")

    conn = await asyncpg.connect(neon_dsn())
    try:
        # 기존 행 파악 (UPDATE vs INSERT 분기) + 백업
        existing = {r["group_id"]: dict(r) for r in await conn.fetch(
            "SELECT * FROM redteam_testbot_evals WHERE bot_label=$1 AND run_label=$2",
            bot_label, run_label)}
        norm = {r["id"]: r["question_norm"] for r in await conn.fetch(
            "SELECT id, question_norm FROM redteam_question_groups WHERE id = ANY($1::int[])",
            [r["gid"] for r in evals])}

        upd = [r for r in evals if r["gid"] in existing]
        ins = [r for r in evals if r["gid"] not in existing]
        mode = "🟥 APPLY" if apply else "🟦 DRY-RUN"
        print(f"{mode} · run_label='{run_label}' bot='{bot_label}'(model={bot_model}) · "
              f"UPDATE(채점만) {len(upd)} · INSERT(신규) {len(ins)}")
        for r in evals[:3]:
            old = existing.get(r["gid"], {})
            print(f"  #{r['gid']} AI {old.get('ai_rating','-')}→{r['ai_rating']} "
                  f"독립 {old.get('independent_risk','-')}→{r['independent_risk']} "
                  f"재발 {old.get('risk_recur','-')}→{r['risk_recur']}")
        if not apply:
            print("실제 반영은 --apply.")
            return

        # 백업 (해당 run_label 전체)
        if existing:
            bpath = DIR / f"_regrade_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
            bpath.write_text(json.dumps(list(existing.values()), ensure_ascii=False, default=str, indent=1),
                             encoding="utf-8")
            print(f"백업 {len(existing)}행 → {bpath.name}")

        n_u = n_i = 0
        async with conn.transaction():
            for r in upd:  # 채점 6필드만 갱신 (답변·citations·bf_citations 보존)
                await conn.execute(
                    "UPDATE redteam_testbot_evals SET "
                    "risk_recur=$3, risk_recur_detail=$4, independent_risk=$5, independent_risk_detail=$6, "
                    "ai_rating=$7, ai_rating_detail=$8, updated_at=now() "
                    "WHERE bot_label=$1 AND run_label=$2 AND group_id=$9",
                    bot_label, run_label, r.get("risk_recur"), r.get("risk_recur_detail") or "",
                    r.get("independent_risk"), r.get("independent_risk_detail") or "",
                    _num(r.get("ai_rating")), r.get("ai_rating_detail") or "", r["gid"])
                n_u += 1
            for r in ins:  # 신규 행은 전체 삽입
                await conn.execute(
                    """INSERT INTO redteam_testbot_evals
                       (group_id, question_norm, run_label, bot_label, bot_id, bot_model, answer,
                        citations, bf_citations, risk_recur, risk_recur_detail,
                        independent_risk, independent_risk_detail, ai_rating, ai_rating_detail, eval_engine)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8::json,$9::json,$10,$11,$12,$13,$14,$15,'codex')""",
                    r["gid"], norm[r["gid"]], run_label, bot_label, bot_id, bot_model, r.get("answer", ""),
                    json.dumps(r.get("citations", []), ensure_ascii=False),
                    json.dumps(r.get("bf_citations", []), ensure_ascii=False),
                    r.get("risk_recur"), r.get("risk_recur_detail") or "",
                    r.get("independent_risk"), r.get("independent_risk_detail") or "",
                    _num(r.get("ai_rating")), r.get("ai_rating_detail") or "")
                n_i += 1
        print(f"✅ 완료: UPDATE {n_u} · INSERT {n_i} → run_label='{run_label}'")
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--eval-tag", required=True, help="_evals_<tag>.json / _answers_<tag>.json")
    ap.add_argument("--run-label", required=True)
    ap.add_argument("--bot-model", default="")
    args = ap.parse_args()
    asyncio.run(run(args.apply, args.eval_tag, args.run_label, args.bot_model))
