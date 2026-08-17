# 0.93보다 나은 감도 탐색 — 전역/per-FAQ/마진 스킴 비교 (기존 143 라벨데이터 기준, 오라클=천장)
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
ev = json.load(open(ROOT / "exports/faq_test/evaluated_all.json"))
ATTR = {16, 19, 26, 30}
GRID = [round(0.85 + 0.0025 * i, 4) for i in range(int((0.99 - 0.85) / 0.0025) + 1)]


def metrics(decisions):
    TP = FP = FN = TN = 0
    for r, fire in decisions:
        if r["ground_truth"]:
            TP += fire; FN += (not fire)
        else:
            FP += fire; TN += (not fire)
    p = TP / (TP + FP) if TP + FP else 1.0
    rec = TP / (TP + FN) if TP + FN else 1.0
    f1 = 2 * p * rec / (p + rec) if p + rec else 0
    return FP, FN, round(p, 3), round(rec, 3), round(f1, 3)


def show(name, decisions):
    FP, FN, p, r, f1 = metrics(decisions)
    print(f"  {name:34} FP={FP:2d} FN={FN:2d}  정밀={p:.3f} 재현={r:.3f} F1={f1:.3f}")


# 데이터 밀도
dens = Counter(r["top1_id"] for r in ev)
both = {fid for fid in dens if any(r["top1_id"] == fid and r["ground_truth"] for r in ev)
        and any(r["top1_id"] == fid and not r["ground_truth"] for r in ev)}
print(f"probe {len(ev)}건이 top1로 매칭된 FAQ {len(dens)}종. 양·음 둘다 가진 FAQ {len(both)}종 (per-FAQ 튜닝 가능 대상)\n")

print("=== A. 기준선 ===")
show("현행 전역0.93 + 4종0.96", [(r, r["top1_sim"] >= (0.96 if r["top1_id"] in ATTR else 0.93)) for r in ev])

print("\n=== B. 최적 단일 전역 (F1·균형 기준) ===")
best = max(GRID, key=lambda T: metrics([(r, r["top1_sim"] >= T) for r in ev])[4])
show(f"단일 전역 best T={best}", [(r, r["top1_sim"] >= best) for r in ev])

print("\n=== C. per-FAQ 오라클 (각 FAQ 최적 T, 데이터 게이트) — 천장 ===")
# 각 FAQ별로 자기 probe에서 오차 최소 T 탐색. 데이터 부족(양·음 둘다 없음)이면 기본 0.93.
by = defaultdict(list)
for r in ev:
    by[r["top1_id"]].append(r)
perfaq_T = {}
for fid, rows in by.items():
    if fid in both:
        bestT = min(GRID, key=lambda T: sum((r["top1_sim"] >= T) != r["ground_truth"] for r in rows))
        perfaq_T[fid] = bestT
    else:
        perfaq_T[fid] = 0.93
show("per-FAQ 오라클(게이트)", [(r, r["top1_sim"] >= perfaq_T[r["top1_id"]]) for r in ev])
# 기본0.93과 다른 FAQ만 출력
diff = {fid: t for fid, t in perfaq_T.items() if abs(t - 0.93) > 1e-9}
print(f"     기본0.93과 다른 FAQ {len(diff)}종: " + ", ".join(f"id{fid}={t}" for fid, t in sorted(diff.items())))

print("\n=== D. 마진 규칙 (top1>=T AND top1-top2>=M) ===")
cand = []
for T in [0.90, 0.91, 0.92, 0.93]:
    for M in [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]:
        dec = [(r, (r["top1_sim"] >= T and (r["top1_sim"] - (r["top2_sim"] or 0)) >= M)) for r in ev]
        FP, FN, p, rr, f1 = metrics(dec)
        cand.append((f1, T, M, FP, FN, p, rr))
cand.sort(reverse=True)
for f1, T, M, FP, FN, p, rr in cand[:6]:
    print(f"  T={T} M={M:.2f}  FP={FP:2d} FN={FN:2d}  정밀={p:.3f} 재현={rr:.3f} F1={f1:.3f}")

print("\n=== E. per-FAQ 오라클 + 마진 결합 ===")
bestcomb = None
for M in [0.0, 0.01, 0.02, 0.03]:
    dec = [(r, (r["top1_sim"] >= perfaq_T[r["top1_id"]] and (r["top1_sim"] - (r["top2_sim"] or 0)) >= M)) for r in ev]
    m = metrics(dec)
    if bestcomb is None or m[4] > bestcomb[0][4]:
        bestcomb = (m, M)
show(f"per-FAQ + 마진 M={bestcomb[1]}", [(r, (r["top1_sim"] >= perfaq_T[r["top1_id"]] and (r["top1_sim"] - (r["top2_sim"] or 0)) >= bestcomb[1])) for r in ev])

print("\n※ C·E의 per-FAQ 오라클은 '같은 데이터로 최적화'라 과적합(낙관). 실제 우월성은 신규 홀드아웃으로 검증 필요.")
