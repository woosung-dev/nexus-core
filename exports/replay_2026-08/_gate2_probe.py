"""게이트 ②(지어냄) 차단이 옳았는지 **눈으로** 보는 프로브. 2026-08-21.

`_run_e2e --policy strict` 로는 못 본다 — 차단되면 답변이 고정 문구로 갈리고 인용이
비워져서, 저장된 산출물에는 **무엇을 지어냈다고 봤는지의 원본이 남지 않는다.**
그래서 게이트 앞단(`generate_with_rag`)에서 답변·청크를 그대로 받아 자를 대 본다.

⚠ 저장된 옛 데이터로는 못 한다. `citations.content` 는 표시용 800자 절단본이고 판정은
`full_content` 로 해야 한다 — 절단본으로 재판정하면 수치가 부푼다(인계문서 §2).

    cd backend && FILE_SEARCH_STORE_NAME=nexus-fs-measure-0818 \
      .venv/bin/python -u ../exports/replay_2026-08/_gate2_probe.py R0001,R0010
"""

import asyncio
import json
import os
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "regression"))
sys.path.insert(0, str(DIR.parent.parent / "backend"))

CIDS = sys.argv[1].split(",") if len(sys.argv) > 1 else []
BOT_ID = int(os.environ.get("PROBE_BOT_ID", "29"))


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.bot import Bot
    from app.services.rag.factory import get_rag_service
    from app.services.strict_mode import (
        fabricated_vs_grounding,
        grounding_locators,
        has_direct_citation,
    )

    dsn = os.environ.get("DATABASE_URL", "postgresql+asyncpg://nexus_user:nexus_pass@localhost:5432/nexus_core")
    if "neon.tech" in dsn:
        sys.exit("⛔ 라이브 DSN 이다. 중단한다.")
    engine = create_async_engine(dsn)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    items = {i["cid"]: i for i in json.loads((DIR / "_input_150.json").read_text())["items"]}
    async with Session() as s:
        bot = (await s.execute(select(Bot).where(Bot.id == BOT_ID))).scalar_one()
    rag = get_rag_service(provider=bot.llm_model)

    for cid in CIDS:
        q = items[cid]["q"]
        r = await rag.generate_with_rag(
            bot_id=bot.id, prompt=q, system_prompt=bot.system_prompt,
            model_name=bot.llm_model, history=None,
        )
        fake = fabricated_vs_grounding(r.answer, r.citations)
        keys = grounding_locators(r.citations)
        print("=" * 78)
        print(f"{cid} | {q}")
        print(f"① 직접인용 {has_direct_citation(r.citations)} · 청크 {len(r.citations)}")
        print(f"청크가 담은 조문 키: {sorted(keys)}")
        print(f"② 판정 = {'차단' if fake else '통과'} · 지어냄 후보 {sorted(fake)}")
        for c in r.citations:
            body = c.full_content or c.content or ""
            print(f"  - [{c.title}] approx={c.approximate} len={len(body)}")
        print("--- 답변 ---")
        print(r.answer)
        await asyncio.sleep(10)

    await engine.dispose()


asyncio.run(main())
