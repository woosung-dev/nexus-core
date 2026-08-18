# captures.json·attribution.json 에서 A/D/F 아키텍처 비교 지표를 산출해 metrics.json 으로 저장
import json
import re
from pathlib import Path

DIR = Path(__file__).parent
CAPS = json.loads((DIR / "captures.json").read_text())
ATTR_PATH = DIR / "attribution.json"
ATTR = json.loads(ATTR_PATH.read_text()) if ATTR_PATH.exists() else {}
OUT = DIR / "metrics.json"

# 문서전용 앵커: 공문번호·연령·금액·기간·비율
_ANCHOR_RES = [
    re.compile(r"제?\s?\d{4}-\d+호"),
    re.compile(r"만\s?\d+\s?세"),
    re.compile(r"\d+\s?(?:일|년|개월)(?!반)"),
    re.compile(r"\d[\d,.]*\s?(?:만\s?원|원|달러|불)"),
    re.compile(r"\d+\s?%"),
]


def anchors(text: str) -> set[str]:
    out = set()
    for rx in _ANCHOR_RES:
        for m in rx.findall(text or ""):
            out.add(re.sub(r"\s+", "", m))
    return out


def file_cits(ann_list) -> list[dict]:
    return [a for a in (ann_list or []) if a.get("type") == "file_citation"]


def span_texts(raw_answer: str, anns: list[dict]) -> list[dict]:
    """annotation의 start/end(UTF-8 byte offset)가 답변 내부를 가리키는지 검증하고 span 텍스트 추출."""
    b = (raw_answer or "").encode("utf-8")
    rows = []
    for a in anns:
        s, e = a.get("start_index"), a.get("end_index")
        ok = isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(b)
        span = b[s:e].decode("utf-8", errors="replace") if ok else None
        rows.append({"file": a.get("file_name"), "start": s, "end": e, "valid": ok,
                     "span": (span[:120] if span else None)})
    return rows


def main():
    per_q = []
    for key in sorted(CAPS, key=int):
        rec = CAPS[key]
        p, a, pf = rec.get("P") or {}, rec.get("A") or {}, rec.get("PF") or {}
        a2 = rec.get("A2")
        if any(x.get("error") for x in (p, a, pf) if isinstance(x, dict)):
            per_q.append({"qid": key, "skipped": True})
            continue

        p_ans, a_ans = p.get("answer") or "", a.get("answer") or ""
        cits_a = file_cits(a.get("annotations"))
        spans = span_texts(a.get("raw_answer") or "", cits_a)

        pa, aa = anchors(p_ans), anchors(a_ans)
        row = {
            "qid": key,
            "question": rec["question"],
            # A 아키텍처
            "A_n_citations": len(cits_a),
            "A_cited_files": sorted({c.get("file_name") or "" for c in cits_a}),
            "A_spans_valid": sum(1 for s in spans if s["valid"]),
            "A_spans": spans,
            "A_answer_len": len(a_ans),
            # 운영 표시답변(P) — 현행 grounding 보고
            "P_n_citations": len(p.get("citations") or []),
            "P_answer_len": len(p_ans),
            # F fidelity gap: 표시답변 P ↔ 백필 소스 답변 B(=A 콜) 앵커 비교
            "anchors_P": sorted(pa),
            "anchors_B": sorted(aa),
            "anchors_only_in_B": sorted(aa - pa),  # 인용 기준 답변에만 있는 사실 → 표시답변과 불일치
            "anchors_only_in_P": sorted(pa - aa),
            # PF (D 후보)
            "PF_n_chunks": len(pf.get("chunks") or []),
        }
        if isinstance(a2, dict) and not a2.get("error"):
            f1 = {c.get("file_name") for c in file_cits(a.get("annotations"))}
            f2 = {c.get("file_name") for c in file_cits(a2.get("annotations"))}
            union = f1 | f2
            row["A_repeat_n_citations"] = len(file_cits(a2.get("annotations")))
            row["A_repeat_file_jaccard"] = round(len(f1 & f2) / len(union), 3) if union else 1.0
        per_q.append(row)

    ok_rows = [r for r in per_q if not r.get("skipped")]
    n = len(ok_rows)

    summary = {
        "n_questions": n,
        # A
        "A_citation_rate": round(sum(1 for r in ok_rows if r["A_n_citations"] > 0) / n, 3) if n else 0,
        "A_avg_citations": round(sum(r["A_n_citations"] for r in ok_rows) / n, 2) if n else 0,
        "A_span_validity": None,
        "A_determinism": None,
        # 운영 P (현행 grounding 보고율 재확인)
        "P_citation_rate": round(sum(1 for r in ok_rows if r["P_n_citations"] > 0) / n, 3) if n else 0,
        # F fidelity gap
        "F_qs_with_anchor_mismatch": sum(
            1 for r in ok_rows if r["anchors_only_in_B"] or r["anchors_only_in_P"]),
        "F_qs_with_B_only_anchors": sum(1 for r in ok_rows if r["anchors_only_in_B"]),
        # PF/D
        "PF_chunk_rate": round(sum(1 for r in ok_rows if r["PF_n_chunks"] > 0) / n, 3) if n else 0,
        "D_by_threshold": {},
    }
    total_spans = sum(r["A_n_citations"] for r in ok_rows)
    if total_spans:
        summary["A_span_validity"] = round(sum(r["A_spans_valid"] for r in ok_rows) / total_spans, 3)
    reps = [r for r in ok_rows if "A_repeat_file_jaccard" in r]
    if reps:
        summary["A_determinism"] = {
            "n_repeated": len(reps),
            "avg_file_jaccard": round(sum(r["A_repeat_file_jaccard"] for r in reps) / len(reps), 3),
            "both_emitted": sum(1 for r in reps if r["A_n_citations"] > 0 and r["A_repeat_n_citations"] > 0),
        }
    if ATTR:
        ths = sorted({th for r in ATTR.values() for th in r["by_threshold"]}, key=float)
        for th in ths:
            with_cit = sum(1 for r in ATTR.values() if r["by_threshold"][th]["cited_chunks"])
            cov = sum(r["by_threshold"][th]["covered_sentences"] for r in ATTR.values())
            tot = sum(r["n_sentences"] for r in ATTR.values())
            summary["D_by_threshold"][th] = {
                "citation_rate": round(with_cit / len(ATTR), 3),
                "sentence_coverage": round(cov / tot, 3) if tot else 0,
            }

    OUT.write_text(json.dumps({"summary": summary, "per_question": per_q},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"→ {OUT.name}")


main()
