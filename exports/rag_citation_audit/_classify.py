# _derived.json + _judge.json을 조인해 인용누락 원인(코드/아키텍처/라이브러리)을 분류·집계 → _rootcause.json + 요약표
import json
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DERIVED = ROOT / "exports/rag_citation_audit/_derived.json"
JUDGE = ROOT / "exports/rag_citation_audit/_judge.json"
OUT = ROOT / "exports/rag_citation_audit/_rootcause.json"


def classify(r, j):
    """한 (질문,봇) 행의 인용 상태를 분류."""
    pos = r["expected_retrieval"]
    a_cit = r["A_cit"]
    silent = bool(j.get("silent_grounding")) or r["L2_anchor_hit"]

    if not pos:  # 코퍼스外 부정
        if a_cit > 0 or r["C_chunks"] > 0 or j.get("hallucinated_fact"):
            return "NEG_false_retrieval"
        return "NEG_correct"

    if a_cit > 0:
        return "OK_cited"                       # 운영이 인용 저장 성공
    # 여기부터 운영 인용 0 (결함 표면)
    if r["B_signal"] > 0:
        return "CODE_loss"                      # 같은 호출에 신호 있었으나 운영이 미독
    if r["C_chunks"] > 0:
        return "ARCH_persona_suppress"          # persona엔 신호 전무, persona-free가 복구
    if silent:
        return "LIB_no_machine_signal"          # 문서 썼다는 증거(앵커/함의)는 있으나 기계신호 어디에도 없음
    return "UNCLEAR_no_retrieval"               # 검색 자체가 안 일어났을 수 있음(상담형 등)


CAUSE_LABEL = {
    "OK_cited": "정상(인용 저장됨)",
    "CODE_loss": "코드(같은 호출 신호 미독)",
    "ARCH_persona_suppress": "아키텍처(페르소나가 보고 억제·persona-free 복구)",
    "LIB_no_machine_signal": "라이브러리/모델(기계 grounding 전무)",
    "UNCLEAR_no_retrieval": "불명(검색 미발생 가능)",
    "NEG_correct": "부정질문 정상(검색無)",
    "NEG_false_retrieval": "부정질문 오검색/환각",
}


def main():
    drows = {(r["qid"], r["bot_id"]): r for r in json.load(open(DERIVED, encoding="utf-8"))["rows"]}
    jmap = {(g["qid"], g["bot_id"]): g["judge"] for g in json.load(open(JUDGE, encoding="utf-8"))["judged"]}

    out = []
    for key, r in drows.items():
        j = jmap.get(key, {})
        cls = classify(r, j)
        out.append({**{k: r[k] for k in ("qid", "bot_id", "model", "source", "expected_retrieval",
                                          "A_cit", "A_markers", "B_signal", "C_chunks", "L2_anchor_hit")},
                    "judge_silent": j.get("silent_grounding"), "judge_ent": j.get("entailment"),
                    "judge_corr": j.get("answer_correctness"), "class": cls})

    cnt = Counter(o["class"] for o in out)
    positives = [o for o in out if o["expected_retrieval"]]
    missing = [o for o in positives if o["A_cit"] == 0]
    miss_cause = Counter(o["class"] for o in missing)

    n_pos = len(positives) or 1
    summary = {
        "n": len(out),
        "operating_citation_capture_rate_pct": round(100 * sum(1 for o in positives if o["A_cit"] > 0) / n_pos, 1),
        "persona_free_recovery_rate_pct": round(100 * sum(1 for o in positives if o["C_chunks"] > 0) / n_pos, 1),
        "silent_grounding_rate_pct": round(100 * sum(1 for o in positives if o["judge_silent"] or o["L2_anchor_hit"]) / n_pos, 1),
        "class_distribution": dict(cnt),
        "missing_citation_cause_distribution": dict(miss_cause),
    }

    OUT.write_text(json.dumps({"summary": summary, "rows": out}, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=" * 78)
    print("RAG 인용 근본원인 분류 결과")
    print("=" * 78)
    print(f"운영(persona) 인용 캡처율   : {summary['operating_citation_capture_rate_pct']}%  "
          f"(positive {n_pos}건 중)")
    print(f"persona-free 복구율          : {summary['persona_free_recovery_rate_pct']}%")
    print(f"조용한 grounding 비율        : {summary['silent_grounding_rate_pct']}%")
    print("-" * 78)
    print("전체 분류 분포:")
    for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}  {k:<24} {CAUSE_LABEL.get(k, k)}")
    print("-" * 78)
    print(f"인용 누락({len(missing)}건) 원인 분포:")
    for k, v in sorted(miss_cause.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}  {k:<24} {CAUSE_LABEL.get(k, k)}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
