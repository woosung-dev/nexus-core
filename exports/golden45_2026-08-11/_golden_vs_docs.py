# 관리자 정답지(45) ↔ 규정집 v20 코퍼스 대조.
#
# `_evidence_audit.py` 는 「이 **질문**에 문서가 답할 수 있는가」를 물었다. 여기서는 다른 것을
# 묻는다 — **「관리자가 적은 답이 문서와 같은 말을 하는가」.**
#
# 왜 필요한가: 인계 문서(handoff-qa-golden-45set §2-1)의 전제다.
#   "불일치 자체가 가장 값진 산출물이다 — 문서 결손이거나 사람의 기억 오류이거나,
#    어느 쪽이든 조치가 필요하다."
# 이미 눈으로 확인된 것만 5건이다(#13·16 연령 · #40·37 가해자/피해자 · #26 · #39 · v20↔v21).
# 45문항 전수로 돌려 빠진 것을 찾는다.
#
# 회수(어휘)와 판정(조문 전문 읽기)을 분리하는 규약은 `_evidence_audit.py` 그대로다.
# 어휘 카운트로 판정하면 거짓양성이 쏟아진다('정자' 24회가 전부 확정자·행정자료·정자세).
import argparse
import importlib.util
import json
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
SRC = ROOT / "exports/prompt4_2026-08-05/_evidence_audit.py"
CORPUS = ROOT / "exports/golden_2026-08/_corpus"
QUESTIONS = ROOT / "exports/regression/questions.json"
OUT = DIR / "_golden_vs_docs.json"

TOP_ART, TOP_GLO, TOP_GONG = 8, 5, 2
BODY_CAP = 1800
BATCH = 3

_spec = importlib.util.spec_from_file_location("_ea", SRC)
_ea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ea)

INSTRUCTION = (
    "너는 종교(세계평화통일가정연합) 축복·가정행정 규정집과 **행정 담당자가 적어 준 정답**을\n"
    "대조하는 심사관이다. <stdin>으로 JSON 배열이 들어온다. 각 항목:\n"
    "  key: 문항 번호\n"
    "  question: 식구가 실제로 물은 질문\n"
    "  golden: 담당자가 적어 준 현행 기준(정답)\n"
    "  golden_source: 담당자가 밝힌 근거(비어 있을 수 있다)\n"
    "  passages: 어휘가 겹쳐 회수된 규정집 v20 조문·행정용어·공문 후보 (전문)\n\n"
    "**담당자의 답이 틀렸다고 보지 마라. 문서가 낡았을 수도 있다.**\n"
    "판정하는 것은 옳고 그름이 아니라 **둘이 같은 말을 하는가**다.\n\n"
    "각 항목을 다음으로 판정하라.\n"
    "① verdict — 정확히 넷 중 하나\n"
    "   '일치'     = passages 가 golden 과 같은 내용을 말한다\n"
    "   '부분일치' = 큰 줄기는 같으나 golden 이 더 구체적이거나 문서가 일부만 다룬다\n"
    "   '불일치'   = passages 가 golden 과 **다른 기준**을 말한다 (숫자·자격·가부가 어긋난다)\n"
    "   '문서에없음' = golden 이 말하는 쟁점을 다루는 조문이 passages 에 없다\n"
    "② conflict — '불일치'일 때만. 어긋나는 대목을 문서 쪽 문장 그대로 1~2줄 인용. 아니면 null.\n"
    "③ cited — 근거로 삼은 조문·행정용어·공문 식별자 배열 (예: ['제65조','행정124']). 없으면 빈 배열.\n"
    "④ doc_gap(true|false) — 이 답을 문서에 새로 실어야 하는가(문서에없음·불일치면 대개 true).\n"
    "⑤ reason — 한국어 1~2문장. 어느 조문의 어느 대목을 보고 그렇게 판정했는지 밝혀라.\n\n"
    "passages 에 없는 조문을 지어내지 마라. 확신이 어려우면 reason 에 명시하라.\n"
    "설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·key 로 출력하라. 각 원소 필드:\n"
    "{key, verdict, conflict, cited, doc_gap, reason}"
)
_ea.INSTRUCTION = INSTRUCTION   # codex_batch 가 모듈 전역을 읽는다


def main(limit):
    arts = json.loads((CORPUS / "articles_v20.json").read_text(encoding="utf-8"))
    glo = json.loads((CORPUS / "glossary_v4.json").read_text(encoding="utf-8"))
    gong = json.loads((CORPUS / "gongmun.json").read_text(encoding="utf-8"))
    items = [i for i in json.loads(QUESTIONS.read_text(encoding="utf-8"))["items"]
             if i.get("no") and i.get("golden")]
    if len(items) != 45:
        sys.exit(f"45문항이 아니다: {len(items)} — _ingest.py 를 먼저 돌려라")

    graded = {}
    if OUT.exists():
        graded = {r["key"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))["rows"]}
        print(f"이전 판정 {len(graded)}건 재사용")

    todo = []
    for it in items:
        key = str(it["no"])
        if key in graded:
            continue
        # 회수 질의에 정답 본문을 함께 넣는다 — 질문 어휘만으로는 정답이 짚는 조문을 놓친다
        # (#26 은 질문에 '탈선'이 없고 정답에만 있다).
        probe = f"{it['q']} {it['golden']}"
        anchors = it.get("anchors") or []
        a = _ea.rank(probe, anchors, arts, lambda u: u["article"], lambda u: u["body"], TOP_ART)
        g = _ea.rank(probe, anchors, glo, lambda u: u["no"], lambda u: u["body"], TOP_GLO)
        m = _ea.rank(probe, anchors, gong, lambda u: u["name"], lambda u: u["body"], TOP_GONG)
        passages = (
            [{"id": f"제{x['article']}조({x['title']})", "text": _ea.tighten(x["body"])[:BODY_CAP]}
             for x in a]
            + [{"id": f"행정{x['no']} {x['term']}", "text": _ea.tighten(x["body"])[:BODY_CAP]}
               for x in g]
            + [{"id": f"공문 {x['name']}", "text": _ea.tighten(x["body"])[:BODY_CAP]} for x in m])
        todo.append({"key": key, "question": it["q"], "golden": it["golden"],
                     "golden_source": it.get("golden_source") or "",
                     "passages": passages,
                     "_cat": it["cat"], "_risk": it.get("risk"),
                     "_admin_status": it.get("evidence_status")})
    if limit:
        todo = todo[:limit]

    print(f"대조 대상 {len(todo)}문항 (v20 코퍼스 · 조문 {len(arts)} · 용어 {len(glo)} · 공문 {len(gong)})")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        print(f"  codex 배치 {i//BATCH+1}/{(len(todo)+BATCH-1)//BATCH}…", flush=True)
        got = _ea.codex_batch([{k: v for k, v in c.items() if not k.startswith("_")}
                               for c in chunk])
        for c in chunk:
            r = got.get(c["key"])
            if not r:
                print(f"    ⚠ 판정 누락: #{c['key']}")
                continue
            graded[c["key"]] = {
                "key": c["key"], "cat": c["_cat"], "risk": c["_risk"],
                "admin_evidence_status": c["_admin_status"],
                "q": c["question"], "golden": c["golden"],
                "golden_source": c["golden_source"],
                "verdict": r.get("verdict"), "conflict": r.get("conflict"),
                "cited": r.get("cited"), "doc_gap": r.get("doc_gap"),
                "reason": r.get("reason"),
                "candidates": [p["id"] for p in c["passages"]]}
        OUT.write_text(json.dumps(
            {"corpus": "v20", "rows": sorted(graded.values(), key=lambda r: int(r["key"]))},
            ensure_ascii=False, indent=1), encoding="utf-8")

    rows = sorted(graded.values(), key=lambda r: int(r["key"]))
    dist = {}
    for r in rows:
        dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
    print(f"\n판정 분포 ({len(rows)}문항): {dist}")
    print(f"문서 보완 필요(doc_gap): {sum(1 for r in rows if r.get('doc_gap'))}건")
    print("\n― 불일치 (문서와 다른 기준을 말한다) ―")
    for r in rows:
        if r["verdict"] == "불일치":
            print(f"  #{r['key']:>2} [{r['risk']}] {r['q'][:45]}")
            print(f"      관리자: {r['golden'][:90]}")
            print(f"      문서  : {str(r['conflict'])[:110]}")
    print("\n― 문서에없음 ―")
    for r in rows:
        if r["verdict"] == "문서에없음":
            print(f"  #{r['key']:>2} [{r['risk']}] {r['q'][:45]} — {str(r['reason'])[:80]}")
    print(f"\n저장 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    main(ap.parse_args().limit)
