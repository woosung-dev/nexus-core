# _derived.json을 codex CLI(구독·무과금)로 봇별 배치 심판 → 함의·조용한grounding·인용지지 판정을 _judge.json으로 저장
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
REPO = str(ROOT)
DERIVED = ROOT / "exports/rag_citation_audit/_derived.json"
OUT = ROOT / "exports/rag_citation_audit/_judge.json"
REASONING = "medium"

INSTRUCTION = (
    "너는 가정연합 축복 상담 챗봇의 RAG 인용(grounding)을 검증하는 엄격한 평가자다.\n"
    "<stdin>으로 JSON 배열이 들어온다. 각 항목은 한 질문에 대한 (1) 운영 답변(answer), "
    "(2) 문서에서 검색된 참조 청크(reference_chunks: 페르소나 없는 별도 검색 결과), "
    "(3) 문서전용 앵커(anchors), (4) 운영이 저장한 인용 수(persona_citation_count)다.\n"
    "설명·서론·코드실행 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·qid로 출력하라.\n"
    "각 원소 필드:\n"
    "  qid,\n"
    "  entailment(entailed|partial|contradicted|unsupported: answer 내용이 reference_chunks로 뒷받침되는 정도. "
    "reference_chunks가 비었으면 unsupported),\n"
    "  used_doc_specific_fact(true/false: answer가 공문번호·금액·연령·고유명사 등 일반상식이 아닌 문서전용 사실을 포함),\n"
    "  silent_grounding(true/false: used_doc_specific_fact가 true 또는 entailment가 entailed/partial 인데 "
    "persona_citation_count==0 인 경우 = 문서를 썼는데 인용이 보고되지 않음),\n"
    "  hallucinated_fact(true/false: reference_chunks·일반상식 어디에도 없는 사실을 단정),\n"
    "  citation_support(full|partial|none|n/a: reference_chunks가 answer의 핵심 주장을 실제로 지지하는 정도. "
    "reference_chunks 없으면 n/a),\n"
    "  answer_correctness(정확|부분오류|오류: 문서 근거와 비교한 사실 정확성. 상담형 질문은 단정 대신 "
    "공감·확인·담당자 연결이면 정확),\n"
    "  reason(한 줄 한국어).\n"
    "코퍼스外 질문(reference_chunks 비고 answer가 '문서에 없음/담당자 확인'이면): used_doc_specific_fact=false, "
    "silent_grounding=false, citation_support=n/a, answer_correctness=정확."
)


def extract_json_array(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError("JSON 배열 못 찾음")
    return json.loads(t[i:j + 1])


def codex_judge(items):
    payload = json.dumps(items, ensure_ascii=False)
    p = subprocess.run(
        ["codex", "exec", INSTRUCTION, "-s", "read-only",
         "-c", f'model_reasoning_effort="{REASONING}"'],
        input=payload, capture_output=True, text=True, cwd=REPO, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-200:]}")
    return extract_json_array(p.stdout)


def main():
    data = json.load(open(DERIVED, encoding="utf-8"))
    rows = data["rows"]
    by_bot = defaultdict(list)
    for r in rows:
        by_bot[r["bot_id"]].append(r)

    judged = []
    for bid, brows in by_bot.items():
        items = []
        for r in brows:
            ref = (r.get("C_chunk_texts") or []) + (r.get("B_chunk_texts") or [])
            ref_txt = [{"title": x.get("title"), "text": (x.get("text") or "")[:900]} for x in ref[:8]]
            items.append({
                "qid": r["qid"], "question": r["question"],
                "answer": (r.get("A_answer") or "")[:2500],
                "reference_chunks": ref_txt,
                "anchors": r.get("anchors") or [],
                "persona_citation_count": r.get("A_cit", 0),
            })
        print(f"  codex 심판: 봇 {bid} ({len(items)}문항)...", flush=True)
        res = codex_judge(items)
        gmap = {str(g.get("qid")): g for g in res}
        for r in brows:
            g = gmap.get(str(r["qid"])) or {
                "entailment": "unsupported", "used_doc_specific_fact": False,
                "silent_grounding": False, "hallucinated_fact": False,
                "citation_support": "n/a", "answer_correctness": "오류", "reason": "[codex 누락]"}
            judged.append({"qid": r["qid"], "bot_id": bid, "judge": g})
            print(f"    {r['qid']:<10} ent={g.get('entailment')} silent={g.get('silent_grounding')} "
                  f"corr={g.get('answer_correctness')}", flush=True)

    OUT.write_text(json.dumps({"meta": {"grader": "codex CLI (구독)", "reasoning": REASONING},
                               "judged": judged}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n심판 저장 {len(judged)}건 → {OUT}")


if __name__ == "__main__":
    sys.exit(main())
