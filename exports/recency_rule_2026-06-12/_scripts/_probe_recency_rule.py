# 파일명 연도 우선(신문서 우선) 프롬프트 규칙의 A/B 미니 프로브 — 가(id5)·나(id3) × 충돌10+일반5 × 규칙 전/후 = 60콜
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

import psycopg2  # noqa: E402
from google.genai import types  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import _get_genai_client  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "프로브_결과_raw.json"

RULE = """

[자료 우선순위 규칙]
- 참고 자료의 문서 제목(파일명)에 연도가 포함된 경우가 있다(예: 2022, 2025, 2025-259호).
- 같은 주제에서 문서 간 내용이 충돌하면, 제목의 연도가 가장 최신인 문서를 정본으로 우선한다.
- 제목에 연도가 없는 문서는 상시 유효한 현행 자료로 간주한다. 단, 연도가 있는 더 최신 문서와 충돌하면 최신 문서를 따른다.
- 기준 변경을 발견하면 "최근 기준으로 변경되었습니다"를 밝히고, 근거 문서명과 연도를 함께 표기한다.
- 과거 시점 기준을 묻는 질문에는 현행 기준과 과거 기준을 구분해 답한다."""

# 충돌 10(연도 다른 문서 간 기준 차이가 실재하거나 가능성 높은 주제) + 일반 5(회귀 확인)
QUESTIONS = [
    ("C01", "충돌", "미혼 1세가 축복 후보자가 되기 위한 연령 기준이 어떻게 되나요?"),
    ("C02", "충돌", "미혼 1세 후보자의 예배 출석 기준은 몇 개월인가요?"),
    ("C03", "충돌", "축복자녀(2세)의 예배 출석 기준을 알려주세요."),
    ("C04", "충돌", "축복 후보자가 되기 위해 이수해야 하는 교육 기준이 궁금해요."),
    ("C05", "충돌", "매칭 확정자의 자격 기준을 알려주세요."),
    ("C06", "충돌", "장애가 있는 축복자녀의 축복헌금은 얼마인가요?"),
    ("C07", "충돌", "12일 가정출발의식은 어떤 경우에 하는 건가요?"),
    ("C08", "충돌", "다음 축복식 일정은 언제인가요?"),
    ("C09", "충돌", "미혼 1세가 제출해야 하는 서류는 뭐가 있나요?"),
    ("C10", "충돌", "축복 후보자의 금식 조건을 알려주세요."),
    ("G01", "일반", "남편과 자꾸 다투게 돼요. 어떻게 하면 좋을까요?"),
    ("G02", "일반", "축복의 의미가 뭐예요?"),
    ("G03", "일반", "축복반지는 어디서 사요?"),
    ("G04", "일반", "부모매칭은 어떻게 진행돼요?"),
    ("G05", "일반", "천보 40일 수련 대신 받을 수 있는 교육이 있나요?"),
]


def load_prompts() -> dict[int, str]:
    url = None
    for line in open("/Users/woosung/project/agy-project/nexus-core/backend/.env"):
        m = re.match(r"^DATABASE_URL\s*=\s*(.+)$", line.strip())
        if m and "neon" not in m.group(1).lower():
            url = m.group(1).strip().strip('"').strip("'")
    m = re.match(r"postgres(?:ql)?(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(\w+)", url)
    user, pw, _host, port, db = m.groups()
    conn = psycopg2.connect(host="localhost", port=int(port or 5432), dbname=db, user=user, password=pw)
    cur = conn.cursor()
    cur.execute("SELECT id, system_prompt FROM bots WHERE id IN (3,5)")
    return {r[0]: r[1] for r in cur.fetchall()}


async def call(client, store, bot_id, system_prompt, question):
    cfg = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1500,
        system_instruction=system_prompt,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id={bot_id}",
            top_k=get_settings().RAG_TOP_K,
        ))],
    )
    for attempt in range(6):
        try:
            r = await client.aio.models.generate_content(
                model="gemini-3.1-flash-lite", contents=question, config=cfg)
            titles = []
            try:
                for c in (r.candidates[0].grounding_metadata.grounding_chunks or []):
                    if c.retrieved_context and c.retrieved_context.title not in titles:
                        titles.append(c.retrieved_context.title)
            except Exception:
                pass
            return {"answer": r.text or "", "titles": titles}
        except Exception as e:
            msg = str(e)
            if any(k in msg for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500")):
                wait = 15 * (attempt + 1)
                print(f"    쿼터/일시 오류 — {wait}s 대기 후 재시도 ({attempt+1}/6)")
                await asyncio.sleep(wait)
                continue
            return {"answer": f"[ERROR] {msg[:300]}", "titles": []}
    return {"answer": "[ERROR] 재시도 소진", "titles": []}


async def main():
    settings = get_settings()
    client = _get_genai_client()
    store = None
    async for s in await client.aio.file_search_stores.list():
        if s.display_name == settings.FILE_SEARCH_STORE_NAME:
            store = s.name
            break
    prompts = load_prompts()
    print(f"store={store} / 프롬프트 로드: id3 {len(prompts[3])}자, id5 {len(prompts[5])}자")

    results = []
    t0 = time.time()
    total = len(QUESTIONS) * 2 * 2
    n = 0
    for bot_id in (5, 3):
        for variant in ("base", "rule"):
            sp = prompts[bot_id] + (RULE if variant == "rule" else "")
            for qid, qtype, q in QUESTIONS:
                n += 1
                print(f"[{n}/{total}] bot{bot_id} {variant} {qid}", flush=True)
                r = await call(client, store, bot_id, sp, q)
                results.append({"bot_id": bot_id, "variant": variant, "qid": qid,
                                "qtype": qtype, "q": q, **r})
                await asyncio.sleep(2.5)  # 프리티어 분당 쿼터 완화

    OUT.write_text(json.dumps({
        "meta": {"date": "2026-06-12", "model": "gemini-3.1-flash-lite", "temperature": 0.2,
                 "top_k": get_settings().RAG_TOP_K, "bots": [5, 3],
                 "rule_chars": len(RULE), "elapsed_sec": round(time.time() - t0)},
        "rule": RULE.strip(),
        "results": results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    print(f"\n완료 — {len(results)}건 저장({OUT.name}), ERROR {errs}건, {round(time.time()-t0)}초")


if __name__ == "__main__":
    asyncio.run(main())
