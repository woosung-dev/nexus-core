# 청크 원문 + 답변 세그먼트를 LLM 에 주고 "실제 근거 구절"을 원문 그대로 뽑아내게 한 뒤 원문 존재를 검증하는 프로브
import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
logging.disable(logging.INFO)

from google.genai import types  # noqa: E402

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1")
PROBE = json.load(open(DIR / "_probe_supports.json"))
OUT = DIR / "_probe_extract.json"
MODEL = "gemini-3.5-flash-lite"

PROMPT = """다음은 챗봇 답변의 일부 구간과, 그 구간이 근거로 삼은 자료 원문이다.

[답변 구간]
{segments}

[자료 원문]
{chunk}

자료 원문에서 위 답변 구간의 근거가 된 부분을 찾아 **원문을 한 글자도 바꾸지 말고 그대로** 복사해 내라.

규칙:
- 원문에 없는 문장을 지어내지 말 것. 반드시 원문에서 복사할 것.
- 근거가 되는 최소 단위로 자를 것(문장 또는 조항 한 개).
- 최대 3개까지.
- 근거가 될 만한 부분이 없으면 빈 배열을 반환할 것.

출력은 아래 JSON 형식만:
{{"spans": ["원문 그대로1", "원문 그대로2"]}}"""


def squash(s):
    return re.sub(r"\s+", "", s or "")


async def main():
    rag = GeminiRAGService()
    client = rag._client

    # 청크(=UI 카드) 단위로 묶기
    cards = {}
    for rec in PROBE:
        for sup in rec["supports"]:
            for ci in sup["chunk_idx"] or []:
                if ci >= len(rec["chunks"]) or not rec["chunks"][ci]:
                    continue
                ch = rec["chunks"][ci]
                key = (rec["gid"], ch["title"], ch["page"], (ch["text"] or "")[:40])
                c = cards.setdefault(key, {"gid": rec["gid"], "title": ch["title"],
                                           "page": ch["page"], "text": ch["text"], "segs": []})
                if sup["text"] and sup["text"] not in c["segs"]:
                    c["segs"].append(sup["text"])

    print(f"대상 카드 {len(cards)}개\n")
    out, t0 = [], time.perf_counter()
    for i, c in enumerate(cards.values(), 1):
        prompt = PROMPT.format(segments="\n".join(f"- {s}" for s in c["segs"]), chunk=c["text"])
        t1 = time.perf_counter()
        try:
            resp = await asyncio.wait_for(client.aio.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0, max_output_tokens=1024,
                    response_mime_type="application/json")), timeout=90)
            spans = json.loads(resp.text).get("spans", [])
        except Exception as e:
            print(f"  [{i}] ERROR {type(e).__name__}: {str(e)[:90]}")
            out.append({**{k: c[k] for k in ('gid', 'title', 'page', 'segs')},
                        "error": str(e)[:200]})
            continue
        ms = (time.perf_counter() - t1) * 1000

        # 환각 차단 게이트 — 공백 무시하고 원문에 실제로 존재해야만 채택
        body = squash(c["text"])
        verified = [s for s in spans if squash(s) and squash(s) in body]
        rejected = [s for s in spans if s not in verified]
        print(f"  [{i}] gid={c['gid']} p.{c['page']} 제안 {len(spans)} → 검증통과 {len(verified)} "
              f"기각 {len(rejected)} ({ms:.0f}ms)")
        out.append({**{k: c[k] for k in ('gid', 'title', 'page', 'segs', 'text')},
                    "spans": spans, "verified": verified, "rejected": rejected, "ms": ms})
        await asyncio.sleep(4)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    ok = [o for o in out if o.get("verified")]
    prop = sum(len(o.get("spans") or []) for o in out)
    vf = sum(len(o.get("verified") or []) for o in out)
    print(f"\n=== 요약 ===")
    print(f"  카드 {len(out)}개 중 형광펜 1개 이상 = {len(ok)} ({len(ok)/len(out):.1%})")
    print(f"  제안 구절 {prop}개 중 원문 검증 통과 {vf}개 ({vf/max(prop,1):.1%})")
    print(f"  전체 {time.perf_counter()-t0:.0f}s, 저장: {OUT}")


asyncio.run(main())
