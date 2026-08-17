# 읽기 전용 증명 — 실행 전후 대조용 스냅샷. SELECT 만 한다.
#
# AGENTS.md §4: "DB 는 SELECT 만. 실행 전후로 messages·chat_sessions 카운트와
# bots.system_prompt 해시를 대조해 증명한다."
#
# 사용: cd backend && .venv/bin/python ../exports/glossary_steering_2026-08-04/_dbproof.py --label before
import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))

for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session  # noqa: E402

for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent
OUT = DIR / "_dbproof.json"
BOTS = (7, 11)


async def snapshot():
    async with async_session() as s:
        counts = {}
        for t in ("messages", "chat_sessions"):
            counts[t] = (await s.execute(text(f"SELECT count(*) FROM {t}"))).scalar()

        bots = {}
        for b in BOTS:
            row = (await s.execute(
                text("SELECT id,name,llm_model,evidence_policy_mode,history_window,system_prompt "
                     "FROM bots WHERE id=:b"), {"b": b})).mappings().first()
            if row is None:
                bots[str(b)] = None
                continue
            sp = row["system_prompt"] or ""
            bots[str(b)] = {
                "name": row["name"], "llm_model": row["llm_model"],
                "evidence_policy_mode": row["evidence_policy_mode"],
                "history_window": row["history_window"],
                "system_prompt_len": len(sp),
                "system_prompt_sha256": hashlib.sha256(sp.encode()).hexdigest(),
            }
    return {"counts": counts, "bots": bots}


async def main(label):
    snap = await snapshot()
    log = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    log.append({"label": label, **snap})
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[{label}] messages={snap['counts']['messages']} "
          f"chat_sessions={snap['counts']['chat_sessions']}")
    for b, v in snap["bots"].items():
        if v:
            print(f"  bot {b:>2} '{v['name']}' sp={v['system_prompt_len']}자 "
                  f"sha={v['system_prompt_sha256'][:16]} model={v['llm_model']} "
                  f"mode={v['evidence_policy_mode']}")

    # 이전 스냅샷과 자동 대조 — 사람이 눈으로 비교하다 놓치는 것을 막는다.
    prevs = [r for r in log[:-1]]
    if prevs:
        base = prevs[0]
        diffs = []
        for k, v in snap["counts"].items():
            if base["counts"].get(k) != v:
                diffs.append(f"{k}: {base['counts'].get(k)} → {v}")
        for b, v in snap["bots"].items():
            bv = base["bots"].get(b)
            if bv and v and bv["system_prompt_sha256"] != v["system_prompt_sha256"]:
                diffs.append(f"bot {b} system_prompt 해시 변경")
        print(f"\n첫 스냅샷('{base['label']}') 대비: "
              + ("변화 없음 (읽기 전용 확인)" if not diffs else "⚠ " + " · ".join(diffs)))
    print(f"→ {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="before / after / 임의 라벨")
    asyncio.run(main(ap.parse_args().label))
