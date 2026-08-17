# persona-free 사이드패스(search_citations)가 실제로 인용을 복구하는지 라이브 검증(봇5·3)
import os
import sys
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
for _l in (ROOT / "backend/.env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

CASES = [(5, "축복자녀-1세 매칭확정자의 변경된 연령 기준은?"),
         (3, "축복을 받고 가정회비를 내는 이유가 무엇인가요?")]


async def main():
    rag = GeminiRAGService()
    ok = True
    for bid, q in CASES:
        async with async_session() as s:
            bot = await crud_bot.get_active_bot(s, bid)
        cits = await rag.search_citations(bot_id=bid, prompt=q, model_name=bot.llm_model)
        all_approx = all(c.approximate for c in cits)
        passed = len(cits) > 0 and all_approx
        ok = ok and passed
        print(f"bot{bid} '{q[:24]}' → citations={len(cits)} approximate={all_approx} "
              f"{'PASS' if passed else 'FAIL'}")
        for c in cits[:4]:
            print(f"    - {c.title} :: {(c.content or '')[:50]}")
        await asyncio.sleep(3)
    print("\n전체:", "PASS — 사이드패스가 인용 복구함" if ok else "FAIL")


asyncio.run(main())
