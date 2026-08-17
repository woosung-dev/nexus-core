# _raw_captures.json에서 Variant A(운영복제)·B(전체추출)·C(페르소나無)를 도출하고 결정 지표를 _derived.json으로 산출(오프라인·무API)
import os
import sys
import json
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x")  # import용 더미
os.environ.setdefault("GEMINI_API_KEY", "dummy")
from app.services.rag.gemini import _split_answer_and_followups  # noqa: E402

CAP = ROOT / "exports/rag_citation_audit/_raw_captures.json"
OUT = ROOT / "exports/rag_citation_audit/_derived.json"


def chunks_of(side):
    gm = (side or {}).get("grounding_metadata") or {}
    return gm.get("grounding_chunks") or []


def supports_of(side):
    gm = (side or {}).get("grounding_metadata") or {}
    return gm.get("grounding_supports") or []


def chunk_texts(side):
    out = []
    for c in chunks_of(side):
        rc = c.get("retrieved_context") or {}
        t = rc.get("text") or ""
        if t:
            out.append({"title": rc.get("title"), "text": t[:1200],
                        "uri": rc.get("uri"), "page_span": (rc.get("rag_chunk") or {}).get("page_span")})
    return out


def l1_mechanical(side):
    """검색이 일어났다는 SDK 기계 신호(grounding_chunks-only보다 넓음)."""
    gm = (side or {}).get("grounding_metadata") or {}
    cm = (side or {}).get("citation_metadata") or {}
    return bool((gm.get("grounding_chunks") or []) or (gm.get("grounding_supports") or [])
                or (cm.get("citations") or []) or gm.get("retrieval_queries"))


def main():
    caps = json.load(open(CAP, encoding="utf-8"))
    rows = []
    for c in caps:
        persona, pfree = c.get("persona") or {}, c.get("persona_free") or {}
        p_ok, f_ok = persona.get("ok"), pfree.get("ok")

        # Variant A — 운영 복제: persona 답변에 _split(마커·followup 제거) + grounding_chunks만
        a_answer = _split_answer_and_followups(persona.get("raw_text") or "")[0] if p_ok else ""
        a_chunks = chunks_of(persona)                 # 운영이 읽는 유일 필드
        a_markers = persona.get("markers") or []      # 운영이 버리는 인라인 마커

        # Variant B — 전체 추출: 같은 persona dump의 모든 신호
        b_supports = supports_of(persona)
        b_citmeta = ((persona.get("citation_metadata") or {}).get("citations") or [])
        b_signal_count = len(a_chunks) + len(b_supports) + len(b_citmeta) + len(a_markers)

        # Variant C — 페르소나無 별도 호출
        c_chunks = chunks_of(pfree)
        c_supports = supports_of(pfree)

        # L2 앵커: persona 답변(A)에 문서전용 앵커가 등장하면 검색 증명
        anchors = c.get("anchors") or []
        anchor_hit = bool(anchors) and any(a in a_answer for a in anchors)

        rows.append({
            "qid": c["qid"], "bot_id": c["bot_id"], "model": c.get("model"),
            "source": c.get("source"), "expected_retrieval": c.get("expected_retrieval"),
            "anchors": anchors, "question": c["question"], "golden": c.get("golden", ""),
            "persona_ok": bool(p_ok), "pfree_ok": bool(f_ok),
            "A_answer": a_answer,
            "A_cit": len(a_chunks),                       # 운영이 저장하는 인용 수
            "A_markers": len(a_markers),
            "B_supports": len(b_supports),
            "B_citmeta": len(b_citmeta),
            "B_signal": b_signal_count,                   # 같은 호출에서 코드가 더 읽었으면 캡처 가능했던 신호 총량
            "C_chunks": len(c_chunks),
            "C_supports": len(c_supports),
            "C_chunk_texts": chunk_texts(pfree),          # 심판 참조 코퍼스
            "B_chunk_texts": chunk_texts(persona),
            "L1_retr_mech_persona": l1_mechanical(persona),
            "L2_anchor_hit": anchor_hit,
        })

    # 집계
    def rate(pred, sub=None):
        pool = [r for r in rows if (sub is None or sub(r))]
        return (round(100 * sum(1 for r in pool if pred(r)) / len(pool), 1), len(pool)) if pool else (None, 0)

    pos = lambda r: r["expected_retrieval"]
    summary = {
        "n_rows": len(rows),
        "by_bot": sorted({r["bot_id"] for r in rows}),
        "models": sorted({r["model"] for r in rows if r["model"]}),
        # 운영(persona) 경로
        "A_citation_capture_rate": rate(lambda r: r["A_cit"] > 0),          # 운영이 인용 저장한 비율
        "A_marker_rate": rate(lambda r: r["A_markers"] > 0),
        "B_extra_signal_rate": rate(lambda r: r["B_signal"] > 0),           # 같은 호출에서 코드 확장 시 캡처 가능 비율
        "L1_retr_mech_persona_rate": rate(lambda r: r["L1_retr_mech_persona"]),
        # persona-free 복구
        "C_chunk_capture_rate": rate(lambda r: r["C_chunks"] > 0),
        "C_capture_rate_positives": rate(lambda r: r["C_chunks"] > 0, sub=pos),
        # 오라클(앵커 보유 질문)
        "L2_anchor_hit_rate": rate(lambda r: r["L2_anchor_hit"], sub=lambda r: bool(r["anchors"])),
        # 조용한 grounding(앵커로 검색 증명되나 운영 인용 0)
        "silent_grounding_by_anchor": rate(lambda r: r["L2_anchor_hit"] and r["A_cit"] == 0,
                                           sub=lambda r: bool(r["anchors"])),
    }
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
