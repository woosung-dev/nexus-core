# 후보 감도 스킴을 학습데이터(r1+r2)에서 도출·고정 → schemes.json 저장 (홀드아웃 검증용)
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
ev = json.load(open(ROOT / "exports/faq_test/evaluated_all.json"))
GRID = [round(0.85 + 0.0025 * i, 4) for i in range(57)]
DEFAULT = 0.93
ATTR = {16, 19, 26, 30}

by = defaultdict(list)
for r in ev:
    by[r["top1_id"]].append(r)


def metrics(dec):
    TP = FP = FN = TN = 0
    for r, fire in dec:
        if r["ground_truth"]:
            TP += fire; FN += (not fire)
        else:
            FP += fire; TN += (not fire)
    p = TP / (TP + FP) if TP + FP else 1.0
    rec = TP / (TP + FN) if TP + FN else 1.0
    f1 = 2 * p * rec / (p + rec) if p + rec else 0
    return {"FP": FP, "FN": FN, "prec": round(p, 3), "rec": round(rec, 3), "f1": round(f1, 3)}


# ── 스킴 정의 ──
# S0 현행: 0.93 + 4종 0.96
S0 = {fid: (0.96 if fid in ATTR else DEFAULT) for fid in by}

# S1 robust auto-per-FAQ: 각 FAQ의 '되면안됨' 최고 sim 바로 위로 threshold 상향(과흡인 자동탐지),
#    단 [0.93, 0.965] 클램프. 고FP 유발 안 하는 FAQ는 0.93 유지. (해석가능·과적합 적음)
S1 = {}
for fid, rows in by.items():
    neg_sims = [r["top1_sim"] for r in rows if not r["ground_truth"]]
    pos_sims = [r["top1_sim"] for r in rows if r["ground_truth"]]
    t = DEFAULT
    if neg_sims:
        ceil = max(neg_sims)
        if ceil >= DEFAULT:                 # 0.93에서 FP 유발하는 FAQ만 상향
            t = min(0.965, round(ceil + 0.003, 4))
    # 양성을 과하게 자르면(데이터상 최저 양성보다 높으면) 약간 완화
    if pos_sims and t > min(pos_sims) and len([s for s in neg_sims if s >= DEFAULT]) < 2:
        t = DEFAULT                          # 음성근거 약하면 무리하게 올리지 않음
    S1[fid] = t

# S2 per-FAQ 오라클(게이트, 과적합 천장 — 참고용)
S2 = {}
for fid, rows in by.items():
    if any(r["ground_truth"] for r in rows) and any(not r["ground_truth"] for r in rows):
        S2[fid] = min(GRID, key=lambda T: sum((r["top1_sim"] >= T) != r["ground_truth"] for r in rows))
    else:
        S2[fid] = DEFAULT

# S3 단일 전역 best
S3T = max(GRID, key=lambda T: metrics([(r, r["top1_sim"] >= T) for r in ev])["f1"])

schemes = {
    "S0_current_0.93+4x0.96": S0,
    "S1_robust_autoperfaq": S1,
    "S2_oracle_perfaq(overfit)": S2,
    "S3_global_best": {"_global": S3T},
    "_default": DEFAULT,
    "_attractors": sorted(ATTR),
}
json.dump(schemes, open(ROOT / "exports/faq_test/schemes.json", "w"), ensure_ascii=False, indent=1)

print("=== 학습데이터(r1+r2, 143) 기준 train 성능 ===")
for name, m in [("S0 현행 0.93+4종0.96", S0), ("S1 robust auto-per-FAQ", S1), ("S2 오라클(과적합천장)", S2)]:
    r = metrics([(rr, rr["top1_sim"] >= m[rr["top1_id"]]) for rr in ev])
    print(f"  {name:26} FP={r['FP']:2d} FN={r['FN']:2d} 정밀={r['prec']:.3f} 재현={r['rec']:.3f} F1={r['f1']:.3f}")
r = metrics([(rr, rr["top1_sim"] >= S3T) for rr in ev])
print(f"  {'S3 단일전역 '+str(S3T):26} FP={r['FP']:2d} FN={r['FN']:2d} 정밀={r['prec']:.3f} 재현={r['rec']:.3f} F1={r['f1']:.3f}")

print(f"\nS1 robust가 0.93에서 올린 FAQ: " +
      ", ".join(f"id{fid}={t}" for fid, t in sorted(S1.items()) if abs(t - DEFAULT) > 1e-9))
print("schemes.json 저장 완료 — 홀드아웃 r3에서 동일 스킴으로 out-of-sample 비교 예정.")
