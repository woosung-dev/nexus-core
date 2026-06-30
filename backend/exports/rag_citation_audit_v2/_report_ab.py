# A/B 집계 + 게이트 판정: 답변품질(승/무/패)·정확도·안전·markup leak·인용보고율·인용지지·지연
import json
import sys
from collections import Counter

SC = "/private/tmp/claude-501/-Users-woosung-project-agy-project-nexus-core/cf88eb6c-aabb-40e6-84d0-e477d46c9272/scratchpad"
_SUF = sys.argv[1] if len(sys.argv) > 1 else ""
caps = json.load(open(f"{SC}/_ab{_SUF}_captures.json", encoding="utf-8"))
judge = json.load(open(f"{SC}/_ab{_SUF}_judge.json", encoding="utf-8"))
cap_by = {(c["qid"], c["bot_id"]): c for c in caps}
cite_by = {(g["qid"], g["bot_id"]): g["judge"] for g in judge["cite"]}


def side(g, a_is, which):
    """which='NEW'|'OLD' → 해당 시스템의 A/B 측 판정 dict."""
    key = "A" if a_is == which else "B"
    return g.get(key) or {}


win = Counter()
new_acc = Counter()
old_acc = Counter()
new_unsafe = old_unsafe = new_leak = 0
n = 0
for r in judge["ab"]:
    g = r["judge"]
    if not g:
        continue
    n += 1
    win[r["winner_system"]] += 1
    nv, ov = side(g, r["A_is"], "NEW"), side(g, r["A_is"], "OLD")
    new_acc[nv.get("accuracy", "오류")] += 1
    old_acc[ov.get("accuracy", "오류")] += 1
    new_unsafe += 0 if nv.get("safe", True) else 1
    old_unsafe += 0 if ov.get("safe", True) else 1
    new_leak += 1 if nv.get("markup_leak") else 0

n = n or 1
# 캡처 기반: 인용 보고율(positive), fu_leak, 지연
pos = [c for c in caps if c.get("expected_retrieval")]
new_cit_rate = sum(1 for c in pos if c["NEW"]["citations"]) / (len(pos) or 1)
old_cit_rate = sum(1 for c in pos if c["OLD"]["citations"]) / (len(pos) or 1)
cap_leak = sum(1 for c in caps if c["NEW"].get("fu_leak"))
new_lat = sorted(c["NEW"]["latency_ms"] for c in caps if not c["NEW"]["blocked"])
old_lat = sorted(c["OLD"]["latency_ms"] for c in caps if not c["OLD"]["blocked"])


def p90(xs):
    return xs[int(len(xs) * 0.9)] if xs else 0


# 인용 무결성
cs = Counter(g.get("citation_support", "none") for g in cite_by.values())
cs_total = sum(cs.values()) or 1
cite_support_ok = (cs["full"] + cs["partial"]) / cs_total
hallu = sum(1 for g in cite_by.values() if g.get("hallucinated"))

new_acc_pct = round(100 * new_acc["정확"] / n, 1)
old_acc_pct = round(100 * old_acc["정확"] / n, 1)
loss_rate = round(100 * win["OLD"] / n, 1)        # NEW 패배 = OLD 승
wintie = round(100 * (win["NEW"] + win["tie"]) / n, 1)

# === 게이트 ===
g1 = loss_rate <= 15 and wintie >= 85
g2 = new_acc_pct >= old_acc_pct - 2
g3 = new_unsafe <= old_unsafe
g4 = (new_leak == 0) and (cap_leak == 0)
g5 = cite_support_ok >= 0.80
g6 = (p90(new_lat) <= 1.5 * p90(old_lat)) if old_lat else True
gates = {"1 답변품질(패≤15·승무≥85)": g1, "2 정확도(NEW≥OLD-2pp)": g2,
         "3 안전(NEW unsafe≤OLD)": g3, "4 markup leak=0": g4,
         "5 인용지지(full|partial≥80%)": g5, "6 지연 p90≤1.5×(참고)": g6}
go = g1 and g2 and g3 and g4 and g5  # 6은 참고

print("=" * 70)
print(f"A/B 검증 결과 (n={n}, 봇별 합산)")
print("=" * 70)
print(f"답변품질  NEW승 {win['NEW']} · 무 {win['tie']} · NEW패(OLD승) {win['OLD']}  "
      f"→ 패배율 {loss_rate}% · 승무 {wintie}%")
print(f"정확도    NEW {new_acc_pct}% vs OLD {old_acc_pct}%  (NEW {dict(new_acc)})")
print(f"안전      unsafe NEW {new_unsafe} vs OLD {old_unsafe}")
print(f"markup    NEW judge_leak {new_leak} · capture fu_leak {cap_leak}")
print(f"인용보고율 NEW {new_cit_rate:.0%} vs OLD {old_cit_rate:.0%} (positive {len(pos)})")
print(f"인용무결성 support {dict(cs)} → full|partial {cite_support_ok:.0%}, hallucinated {hallu}")
print(f"지연 p90  NEW {p90(new_lat):.0f}ms vs OLD {p90(old_lat):.0f}ms")
print("-" * 70)
for k, v in gates.items():
    print(f"  [{'PASS' if v else 'FAIL'}] {k}")
print("-" * 70)
print(f"  ▶ GATE 종합: {'GO (이전 진행)' if go else 'STOP (이전 보류)'}")
