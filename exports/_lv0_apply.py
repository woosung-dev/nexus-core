# A+B 후보(레벨 미분류)를 Lv0으로 실서버에 반영 + AI자동분류 태그·감사코멘트 기록 (dry-run 기본, --apply 로 실제 쓰기)
import argparse
import asyncio
import json
import re
from datetime import date, datetime
from pathlib import Path

import asyncpg

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
AI_TAG = "AI자동분류"
AI_AUTHOR = "AI 자동분류 (codex)"


# ── 실서버(Neon) DSN (preview 스크립트와 동일 규칙). 비밀값은 출력하지 않는다 ──
def _normalize(url):
    return url.replace("+asyncpg", "").replace("ssl=require", "sslmode=require")


def neon_dsn():
    import os
    v = os.environ.get("REDTEAM_DSN")
    if v:
        return _normalize(v)
    env = (ROOT / "backend" / ".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        s = line.lstrip("#").strip()
        if s.startswith("DATABASE_URL=") and "neon.tech" in s:
            return _normalize(s.split("=", 1)[1].strip())
    raise SystemExit("Neon DATABASE_URL 미발견 (REDTEAM_DSN 지정 또는 backend/.env Neon 줄 확인)")


def host_of(dsn):
    m = re.search(r"@([^/:?]+)", dsn)
    return m.group(1) if m else "?"


def latest_html():
    files = sorted(Path.home().glob("Downloads/Lv0_*.html"))
    if not files:
        raise SystemExit("~/Downloads 에 Lv0_예상목록_*.html 이 없습니다. 먼저 _lv0_preview.py 실행.")
    return files[-1]


def load_ab_targets():
    """검토한 HTML에서 A+B 후보만 추출 (사용자가 실제로 본 목록과 동일)."""
    html = latest_html()
    h = html.read_text(encoding="utf-8")
    m = re.search(r"const DATA = (\{.*?\});\nconst P", h, re.S)
    if not m:
        raise SystemExit(f"HTML에서 DATA 파싱 실패: {html}")
    data = json.loads(m.group(1))
    targets = [p for p in data["picked"] if p["tag"] == "A+B"]
    return html.name, targets


def comment_for(p):
    return (f"Lv0(보완 불필요) 자동 설정. 기준 A+B 충족 — 원본 레드팀 피드백 순수 긍정"
            f"(수정·문제 지적 없음), 평균 평점 {p.get('avg')}, 위험도 {p.get('risk')}. "
            f"대기·미분류 상태에서만 적용됨. 검증엔진 codex CLI · {date.today()}. "
            f"사람 검수로 확정하려면 레벨을 직접 변경하세요.")


async def run(apply):
    src, targets = load_ab_targets()
    gids = [p["gid"] for p in targets]
    dsn = neon_dsn()
    mode = "🟥 APPLY(실쓰기)" if apply else "🟦 DRY-RUN(미쓰기)"
    print(f"{mode} · 실서버 {host_of(dsn)} · 대상 HTML {src} · A+B {len(targets)}건")

    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            "SELECT id, status, level, tags FROM redteam_question_groups WHERE id = ANY($1::int[])",
            gids,
        )
        cur = {r["id"]: r for r in rows}

        eligible, skipped = [], []
        for p in targets:
            r = cur.get(p["gid"])
            if r is None:
                skipped.append((p, "그룹 없음"))
            elif r["status"] != "대기":
                skipped.append((p, f"상태={r['status']}"))
            elif r["level"] is not None:
                skipped.append((p, f"레벨={r['level']}(이미 분류)"))
            else:
                eligible.append(p)

        print(f"── 반영 가능 {len(eligible)}건 · 스킵 {len(skipped)}건 ──")
        for p, why in skipped[:30]:
            print(f"  스킵 #{p['gid']} ({why}) {p['q'][:30]}")

        if not apply:
            print("\n[DRY-RUN] 아무것도 쓰지 않았습니다. 실제 반영은 --apply.")
            print("적용 예시(상위 5):")
            for p in eligible[:5]:
                print(f"  #{p['gid']} level→0 · tags+[{AI_TAG}] · 코멘트: {comment_for(p)[:46]}…")
            return

        # ── 백업 (변경 대상 현재 상태) ──
        backup = [{"id": r["id"], "status": r["status"], "level": r["level"],
                   "tags": (json.loads(r["tags"]) if isinstance(r["tags"], str) else r["tags"])}
                  for r in rows]
        bpath = ROOT / "exports" / f"_lv0_apply_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
        bpath.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"백업 저장 → {bpath}")

        n_up = n_cmt = 0
        async with conn.transaction():
            for p in eligible:
                r = cur[p["gid"]]
                tags = r["tags"]
                if isinstance(tags, str):
                    tags = json.loads(tags) if tags else []
                tags = list(tags or [])
                if AI_TAG not in tags:
                    tags.append(AI_TAG)
                res = await conn.execute(
                    "UPDATE redteam_question_groups SET level=0, tags=$2::json, updated_at=now() "
                    "WHERE id=$1 AND status='대기' AND level IS NULL",
                    p["gid"], json.dumps(tags, ensure_ascii=False),
                )
                if int(res.split()[-1]) == 0:
                    continue  # 조회 이후 상태 변경됨 → 코멘트도 남기지 않음
                n_up += 1
                await conn.execute(
                    "INSERT INTO redteam_manage_feedback (group_id, author, content) VALUES ($1,$2,$3)",
                    p["gid"], AI_AUTHOR, comment_for(p),
                )
                n_cmt += 1
        print(f"✅ 반영 완료: 레벨 0 설정 {n_up}건 · 감사 코멘트 {n_cmt}건 · 상태는 '대기' 유지")
        print(f"되돌리려면 백업 파일({bpath.name})로 복구 스크립트 작성 가능.")
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 DB 쓰기 (미지정 시 dry-run)")
    args = ap.parse_args()
    asyncio.run(run(args.apply))
