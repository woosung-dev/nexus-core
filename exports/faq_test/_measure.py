# probe들의 top-k FAQ 코사인 유사도를 실제 pgvector로 측정 (워크플로우 측정 단계용, 자체 env 로딩)
import os
import sys
import json
import glob
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")

# backend/.env 자체 로딩 + DB 호스트 localhost 오버라이드 (어느 셸에서 실행돼도 동작)
for _line in (ROOT / "backend/.env").read_text().splitlines():
    _line = _line.strip()
    if not _line or _line.startswith("#") or "=" not in _line:
        continue
    _k, _v = _line.split("=", 1)
    os.environ.setdefault(_k, _v.strip().strip('"').strip("'"))
if "DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")

sys.path.insert(0, str(ROOT / "backend"))

import logging  # noqa: E402
logging.disable(logging.INFO)

BOT_ID = 5


async def measure(run_dir: str):
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.utils.embeddings import get_embedding
    from sqlalchemy import text

    # gen_*.json 모두 병합 (각 파일 = probe 객체 리스트)
    probes = []
    for fp in sorted(glob.glob(str(Path(run_dir) / "gen_*.json"))):
        with open(fp, encoding="utf-8") as fh:
            items = json.load(fh)
        for it in items:
            it["_src"] = Path(fp).name
            probes.append(it)
    # 안정 id 부여
    for i, p in enumerate(probes):
        p["id"] = i

    out = []
    async with async_session() as s:
        for p in probes:
            q = p["text"]
            qv = await get_embedding(q)
            vec = f"[{','.join(str(v) for v in qv)}]"
            sql = f"""
                SELECT id, question, answer, 1 - (question_vector <=> '{vec}'::vector) AS sim
                FROM faqs
                WHERE bot_id = :bot_id AND is_active = true AND question_vector IS NOT NULL
                ORDER BY question_vector <=> '{vec}'::vector
                LIMIT 3
            """
            rows = (await s.execute(text(sql), {"bot_id": BOT_ID})).fetchall()
            t1, t2, t3 = (rows + [None, None, None])[:3]
            rec = {
                "id": p["id"],
                "text": q,
                "label": p.get("label"),            # gen 의도 라벨 (pos/neg) — 참고용
                "intended_faq_id": p.get("intended_faq_id"),
                "lens": p.get("lens"),
                "src": p.get("_src"),
                "top1_id": int(t1[0]), "top1_question": t1[1], "top1_answer": t1[2],
                "top1_sim": round(float(t1[3]), 4),
                "top2_id": (int(t2[0]) if t2 else None), "top2_sim": (round(float(t2[3]), 4) if t2 else None),
                "top3_id": (int(t3[0]) if t3 else None), "top3_sim": (round(float(t3[3]), 4) if t3 else None),
            }
            out.append(rec)
            await asyncio.sleep(0.15)

    outpath = Path(run_dir) / "measured.json"
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"measured {len(out)} probes -> {outpath}")


if __name__ == "__main__":
    asyncio.run(measure(sys.argv[1]))
