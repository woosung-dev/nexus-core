# 프로브 질문/봇응답/채점을 클릭 없이 읽는 평문 마크다운으로 덤프(~/Downloads)
import json
from collections import Counter
from datetime import date
from pathlib import Path

EXPORTS = Path("/Users/woosung/project/agy-project/nexus-core/exports")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_3주차_실제질문응답_{date.today()}.md"

ans = {}
for f in ("probe_answers.json", "probe_answers_boost.json"):
    for r in json.loads((EXPORTS / f).read_text(encoding="utf-8"))["results"]:
        ans[(r["candidate"], r["qid"])] = r
grades = {}
for f in ("probe_graded.json", "probe_graded_boost.json"):
    for r in json.loads((EXPORTS / f).read_text(encoding="utf-8"))["graded"]:
        grades[(r["candidate"], r["qid"])] = r["grade"]

# 후보 순서: 최종 채택안 먼저
CANDS = ["B_정밀정보+보강", "B_정밀정보", "A_원리", "D_통합v5"]
LABEL = {"B_정밀정보+보강": "B_정밀정보 + 보강레이어 (★ 최종 채택안)",
         "B_정밀정보": "B_정밀정보 (정밀형 베이스)", "A_원리": "A_원리 (원리형)", "D_통합v5": "D_통합v5 (통합형)"}

lines = [f"# 블레싱 3주차 — 실제 질문 & 봇 응답 (휴먼체크용)\n",
         f"생성 {date.today()} · 운영동일 모델 gemini-3.1-flash-lite · 스테이징 RAG(공문 4종 포함) · 채점 gpt-4o-mini\n",
         "> 각 문항: 질문 → 봇 실제 응답 전문 → 인용 문서 → 채점(정답기준 대비). 클릭 없이 위→아래로 읽으세요.\n"]

qids = sorted({qid for (_, qid) in ans})
for cand in CANDS:
    if not any((cand, q) in ans for q in qids):
        continue
    lines.append(f"\n\n---\n\n# 후보: {LABEL.get(cand, cand)}\n")
    for q in qids:
        item = ans.get((cand, q))
        if not item:
            continue
        g = grades.get((cand, q), {})
        cc = Counter(item.get("citations", []))
        cites = ", ".join(f"{n}×{c}" if c > 1 else n for n, c in cc.items()) or "(없음)"
        flags = " ".join(x for x in [
            "할루시" if g.get("hallucination") else "",
            "unsafe" if not g.get("safe", True) else "",
            "마크업노출" if g.get("markup_leak") else ""] if x)
        lines.append(f"\n## Q{q}. [{g.get('accuracy','?')}] {item['area']}\n")
        lines.append(f"**질문**: {item['q']}\n")
        lines.append(f"**골든 기준**: {item['golden']}\n")
        lines.append(f"**봇 응답**:\n\n{item['answer']}\n")
        lines.append(f"\n**인용 문서**: {cites}")
        lines.append(f"**채점(gpt-4o-mini)**: {g.get('accuracy','?')}{' / '+flags if flags else ''} — {g.get('reason','')}\n")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("평문 Q&A 저장:", OUT)
print("문항:", len(qids), "후보:", [c for c in CANDS if any((c,q) in ans for q in qids)])
