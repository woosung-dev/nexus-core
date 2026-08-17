# L1 시스템 계측 — "파이프라인이 설계대로 돌았는가"를 숫자로 판정한다.
#
# 두 단계로 나뉜다.
#   집계(무API)  : _answers_<tag>.json 의 grounding_chunks/citations/elapsed 를 구간별로 쪼갠다.
#   중립 프로브   : chunks==0 인 문항만 중립 system_prompt 로 재질의해 원인을 가른다.
#
# 왜 중립 프로브가 필요한가 —
#   인용 0건은 "RAG가 안 돌았다"는 뜻이 아니다. 감사(exports/rag_citation_audit/)에서
#   페르소나가 grounding 보고를 억제한다는 게 규명됐다(페르소나 1.4% vs persona-free 97.2%).
#   따라서 같은 질문을 중립 프롬프트로 다시 던져야 아래 둘이 갈린다.
#     (a) 진짜 검색 빈손   — 중립으로도 0건. 문서에 답이 없거나 검색이 못 찾는다 → RAG 데이터 문제
#     (b) 검색됐으나 억제  — 중립으로는 잡힌다. 검색은 됐고 보고만 안 된 것 → 프롬프트/보고 문제
#   이 구분 없이 "인용 0"만 세면 RAG 데이터 문제와 보고 문제를 한 덩어리로 오독하게 된다.
import argparse
import asyncio
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent

# 중립 지시 — 페르소나를 빼고 검색 근거만 최대한 노출시킨다.
# 출처: exports/round3_redteam/04_평가·프로브/_probe_retrieval_capture.py 의 GROUNDING_SP
NEUTRAL_SP = ("너는 자료 검색기다. 제공된 축복행정 규정집·공문 문서에서 질문과 관련된 근거 조항을 "
              "찾아 인용하며 간단히 답하라. 자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라.")


def pct(n, d):
    return f"{100.0 * n / d:.1f}%" if d else "—"


def aggregate(results):
    """구간별 빈손율·인용율. l1 이 없는 행(계측 실패)은 분모에서 뺀다."""
    def bucketize(rows, keyfn):
        agg = defaultdict(lambda: {"n": 0, "empty": 0, "cited": 0, "measured": 0})
        for r in rows:
            k = keyfn(r)
            a = agg[k]
            a["n"] += 1
            l1 = r.get("l1")
            if l1 is None:
                continue
            a["measured"] += 1
            if l1.get("grounding_chunks", 0) == 0:
                a["empty"] += 1
            if r.get("n_citations", 0) > 0:
                a["cited"] += 1
        return dict(agg)

    ok = [r for r in results if not r["answer"].startswith("[ERROR]")]
    return {
        "overall": bucketize(ok, lambda r: "전체"),
        "by_bucket": bucketize(ok, lambda r: r.get("bucket") or "?"),
        "by_category": bucketize(ok, lambda r: r.get("cat") or "(없음)"),
        "by_risk": bucketize(ok, lambda r: r.get("risk") or "(불변제약)"),
    }


def show(title, agg):
    print(f"\n  [{title}]")
    print(f"    {'구간':<26}{'문항':>5}{'계측':>5}{'검색빈손':>10}{'인용有':>10}")
    for k, v in sorted(agg.items(), key=lambda x: -x[1]["n"]):
        print(f"    {k:<26}{v['n']:>5}{v['measured']:>5}"
              f"{pct(v['empty'], v['measured']):>10}{pct(v['cited'], v['measured']):>10}")


async def probe_empty(results, bot_id, model, throttle):
    """chunks==0 문항을 중립 프롬프트로 재질의해 (a)/(b) 를 가른다."""
    from _run import L1Capture, call  # 같은 디렉터리의 러너 재사용
    from app.services.rag.gemini import GeminiRAGService

    targets = [r for r in results
               if not r["answer"].startswith("[ERROR]")
               and (r.get("l1") or {}).get("grounding_chunks") == 0]
    if not targets:
        print("\n  중립 프로브 대상 없음 (검색 빈손 0건)")
        return {}

    cap = L1Capture()
    lg = logging.getLogger("app.services.rag.gemini")
    lg.addHandler(cap)
    lg.setLevel(logging.INFO)
    rag = GeminiRAGService()

    print(f"\n  중립 프로브 {len(targets)}건 (페르소나 제거 후 재검색)")
    out = {}
    for i, r in enumerate(targets, 1):
        key = r.get("cid") or r.get("gid")
        _, _, n_cit, l1 = await call(rag, bot_id, NEUTRAL_SP, model, r["q"], cap, max_tokens=900)
        chunks = (l1 or {}).get("grounding_chunks")
        cause = "판정불가" if chunks is None else ("검색됐으나_보고억제" if chunks > 0 else "진짜_검색빈손")
        out[str(key)] = {"neutral_chunks": chunks, "neutral_citations": n_cit, "cause": cause}
        print(f"    [{i:>2}/{len(targets)}] {key} chunks={chunks} → {cause}", flush=True)
        await asyncio.sleep(throttle)
    lg.removeHandler(cap)
    return out


async def main(tag, do_probe, throttle):
    src = DIR / (f"_answers_{tag}.json" if tag else "_answers.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    results = data["results"]
    bot = data["bot"]

    errs = [r for r in results if r["answer"].startswith("[ERROR]")]
    unmeasured = [r for r in results if r.get("l1") is None and r not in errs]
    agg = aggregate(results)

    print(f"L1 계측 — {src.name} · 봇 {bot['id']} '{bot['name']}' · {bot['model']}")
    print(f"  문항 {len(results)} · 오류 {len(errs)} · 계측 실패 {len(unmeasured)}")
    for t, k in (("전체", "overall"), ("구간별", "by_bucket"),
                 ("카테고리별", "by_category"), ("위험도별", "by_risk")):
        show(t, agg[k])

    ov = agg["overall"].get("전체", {"measured": 0, "empty": 0, "cited": 0})
    print(f"\n  ▶ 검색 빈손율 {pct(ov['empty'], ov['measured'])} "
          f"({ov['empty']}/{ov['measured']})   인용 보고율 {pct(ov['cited'], ov['measured'])}")

    # --probe 없이 다시 돌려도 이전 프로브 결과를 날리지 않는다 (재실행 footgun 방지).
    out_path = DIR / (f"_l1_{tag}.json" if tag else "_l1.json")
    probe = {}
    if out_path.exists():
        probe = json.loads(out_path.read_text(encoding="utf-8")).get("neutral_probe") or {}
        if probe and not do_probe:
            print(f"  (이전 중립 프로브 {len(probe)}건 보존)")
    if do_probe:
        probe = await probe_empty(results, bot["id"], bot["model"], throttle)
        if probe:
            causes = defaultdict(int)
            for v in probe.values():
                causes[v["cause"]] += 1
            print("\n  ▶ 빈손 원인 분해")
            for c, n in sorted(causes.items(), key=lambda x: -x[1]):
                print(f"      {c:<22}{n:>4}건  {pct(n, len(probe))}")

    # ── 근거 공백 목록 — L1 의 1급 산출물 ──────────────────────────
    # 통과율이 아니라 이 목록이 이 계층의 결과물이다. 우리 정답 데이터(규정집·공문·용어집)는
    # 결손이 실증돼 있어서(2세×2세 가정출발 근거 없음, p.21 표제 없는 조문) "빈손율 N%"로
    # 뭉치면 관리자가 문서를 고칠 이유를 잃는다. 어떤 질문에 근거가 없는지가 문서 트랙의 입력이다.
    #
    # 중립 프로브로도 빈손인 것만 넣는다 — 페르소나의 보고 억제(chunks=0 이지만 검색은 됨)와
    # 진짜 자료 공백은 소재가 다르다(A 프롬프트 vs B 문서).
    qmap = {}
    for r in results:
        qmap.setdefault(str(r.get("cid") or r.get("gid")), r)
    gaps = [{"key": k, "q": qmap.get(k, {}).get("q", ""),
             "risk": qmap.get(k, {}).get("risk"), "cat": qmap.get(k, {}).get("cat")}
            for k, v in probe.items() if v["cause"] == "진짜_검색빈손"]
    gaps.sort(key=lambda g: ({"상": 0, "중": 1, "하": 2}.get(g["risk"], 9), g["key"]))

    out_path.write_text(json.dumps({"source": src.name, "bot": bot, "aggregate": agg,
                                    "n_errors": len(errs), "n_unmeasured": len(unmeasured),
                                    "evidence_gaps": gaps,
                                    "neutral_probe": probe}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    if probe:
        print(f"\n  ▶ 근거 공백 {len(gaps)}건 — 문서 트랙으로 넘길 목록 "
              f"(중립 프롬프트로도 빈손 = 자료에 답이 없다)")
        for g in gaps:
            print(f"      [{g['risk'] or '—'}] {g['key']} {g['q'][:50]}")
    print(f"\n저장 → {out_path.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--probe", action="store_true", help="빈손 문항을 중립 프롬프트로 재질의 (API 호출)")
    ap.add_argument("--throttle", type=int, default=8)
    a = ap.parse_args()
    asyncio.run(main(a.tag, a.probe, a.throttle))
