# 홀드아웃 검증 — 학습(r1+r2)에서 고정한 스킴들을 신규 r3에 적용해 out-of-sample 비교
import json
import sys
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
schemes = json.load(open(ROOT / "exports/faq_test/schemes.json"))
DEFAULT = schemes["_default"]
test = json.load(open(sys.argv[1]))  # r3 evaluated.json


def tmap(name):
    m = schemes[name]
    return {int(k): v for k, v in m.items() if not k.startswith("_")}


def metrics(records, decide):
    TP = FP = FN = TN = 0
    for r in records:
        fire = decide(r)
        if r["ground_truth"]:
            TP += fire; FN += (not fire)
        else:
            FP += fire; TN += (not fire)
    p = TP / (TP + FP) if TP + FP else 1.0
    rec = TP / (TP + FN) if TP + FN else 1.0
    f1 = 2 * p * rec / (p + rec) if p + rec else 0
    return TP, FP, FN, TN, p, rec, f1


npos = sum(1 for r in test if r["ground_truth"])
print(f"홀드아웃 r3: {len(test)}건 (오버라이드돼야 {npos} / 되면안됨 {len(test)-npos})\n")

S0, S1, S2 = tmap("S0_current_0.93+4x0.96"), tmap("S1_robust_autoperfaq"), tmap("S2_oracle_perfaq(overfit)")
S3T = schemes["S3_global_best"]["_global"]

cands = [
    ("S0 현행 0.93+4종0.96", lambda r: r["top1_sim"] >= S0.get(r["top1_id"], DEFAULT)),
    ("S1 robust auto-per-FAQ", lambda r: r["top1_sim"] >= S1.get(r["top1_id"], DEFAULT)),
    ("S2 오라클(과적합)", lambda r: r["top1_sim"] >= S2.get(r["top1_id"], DEFAULT)),
    (f"S3 단일전역 {S3T}", lambda r: r["top1_sim"] >= S3T),
    ("(참고)플랫 0.93", lambda r: r["top1_sim"] >= 0.93),
]
print("=== out-of-sample (r3) 성능 ===")
print(f"  {'스킴':26} {'FP':>3} {'FN':>3} {'정밀':>6} {'재현':>6} {'F1':>6}")
for name, dec in cands:
    TP, FP, FN, TN, p, rec, f1 = metrics(test, dec)
    print(f"  {name:26} {FP:>3} {FN:>3} {p:>6.3f} {rec:>6.3f} {f1:>6.3f}")
