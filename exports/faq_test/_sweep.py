# 임계값 스윕 — 정답라벨(should_override) + top1 유사도로 혼동행렬·최적 threshold 산출
import sys
import json
from pathlib import Path


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sweep(records, lo=0.80, hi=0.99, step=0.0025):
    # ideal=should_override(True/False), score=top1_sim
    pos = [r for r in records if r["ground_truth"] is True]   # 오버라이드돼야 함
    neg = [r for r in records if r["ground_truth"] is False]  # 오버라이드되면 안 됨
    rows = []
    t = lo
    while t <= hi + 1e-9:
        TP = sum(1 for r in pos if r["top1_sim"] >= t)
        FN = len(pos) - TP
        FP = sum(1 for r in neg if r["top1_sim"] >= t)
        TN = len(neg) - FP
        prec = TP / (TP + FP) if (TP + FP) else 1.0
        rec = TP / (TP + FN) if (TP + FN) else 1.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        rows.append({"t": round(t, 4), "TP": TP, "FP": FP, "TN": TN, "FN": FN,
                     "prec": round(prec, 4), "rec": round(rec, 4), "f1": round(f1, 4)})
        t += step
    return pos, neg, rows


def main(path):
    records = load(path)
    records = [r for r in records if r.get("ground_truth") is not None]
    pos, neg, rows = sweep(records)

    print(f"probes={len(records)}  (오버라이드돼야={len(pos)} / 되면안됨={len(neg)})\n")

    # 분리 통계
    pos_sims = sorted([r["top1_sim"] for r in pos])
    neg_sims = sorted([r["top1_sim"] for r in neg], reverse=True)
    if pos_sims and neg_sims:
        print(f"오버라이드돼야 유사도 최저(recall floor): {pos_sims[0]:.4f}")
        print(f"되면안됨 유사도 최고(FP ceiling):        {neg_sims[0]:.4f}")
        gap = pos_sims[0] - neg_sims[0]
        print(f"분리 간극: {gap:+.4f}  {'(겹침)' if gap < 0 else '(분리)'}\n")

    # 최적 후보
    best_f1 = max(rows, key=lambda r: (r["f1"], r["t"]))
    zero_fp = [r for r in rows if r["FP"] == 0]
    strict = min(zero_fp, key=lambda r: r["t"]) if zero_fp else None  # FP=0 만족 최저 T(=최대 recall)
    full_rec = [r for r in rows if r["FN"] == 0]
    loose = max(full_rec, key=lambda r: r["t"]) if full_rec else None  # FN=0 만족 최고 T(=최소 FP)

    print("=== 최적 후보 ===")
    print(f"F1 최대:        T={best_f1['t']:.4f}  F1={best_f1['f1']:.3f}  P={best_f1['prec']:.3f} R={best_f1['rec']:.3f}  (TP{best_f1['TP']} FP{best_f1['FP']} FN{best_f1['FN']} TN{best_f1['TN']})")
    if strict:
        print(f"정밀우선(FP=0): T={strict['t']:.4f}  recall={strict['rec']:.3f}  (TP{strict['TP']} FN{strict['FN']})  ← 틀린 고정답변 0")
    if loose:
        print(f"재현우선(FN=0): T={loose['t']:.4f}  FP={loose['FP']}  ← 진짜 매칭 다 잡되 오발동 최소")
    if strict and loose and loose["t"] >= strict["t"]:
        # 무오류 구간 [strict(FP=0 최저), loose(FN=0 최고)] 중앙
        mid = round((strict["t"] + loose["t"]) / 2, 4)
        print(f"권장(균형):     T={mid:.4f}  (무오류구간 [{strict['t']:.4f}, {loose['t']:.4f}] 중앙)")
    else:
        print(f"권장(균형):     T={best_f1['t']:.4f}  (무오류구간 없음 → F1최대)")

    # 스윕 표 (경계 구간만)
    print("\n=== 스윕 (0.88~0.97) ===")
    print(f"{'T':>7} {'TP':>3} {'FP':>3} {'FN':>3} {'TN':>3} {'prec':>6} {'rec':>6} {'F1':>6}")
    for r in rows:
        if 0.88 - 1e-9 <= r["t"] <= 0.97 + 1e-9:
            mark = "  <-F1max" if r["t"] == best_f1["t"] else ("  <-FP0" if strict and r["t"] == strict["t"] else "")
            print(f"{r['t']:>7.4f} {r['TP']:>3} {r['FP']:>3} {r['FN']:>3} {r['TN']:>3} {r['prec']:>6.3f} {r['rec']:>6.3f} {r['f1']:>6.3f}{mark}")

    # 하드케이스(경계) — 다음 라운드 생성 표적
    if strict:
        T = strict["t"]
        fp_cases = sorted([r for r in neg if r["top1_sim"] >= best_f1["t"]], key=lambda r: -r["top1_sim"])
        fn_cases = sorted([r for r in pos if r["top1_sim"] < best_f1["t"]], key=lambda r: r["top1_sim"])
        band = sorted([r for r in records if best_f1["t"] - 0.03 <= r["top1_sim"] <= best_f1["t"] + 0.03],
                      key=lambda r: -r["top1_sim"])
        print(f"\n=== 경계 밴드(±0.03 of F1max={best_f1['t']:.3f}) {len(band)}건 — 다음 라운드 표적 ===")
        for r in band[:18]:
            gt = "OVR돼야" if r["ground_truth"] else "되면안됨"
            print(f"  {r['top1_sim']:.4f} [{gt}] top1=id{r['top1_id']}  «{r['text'][:46]}»")

    # 패밀리(top1_id가 정리족 1~9) 분석
    fam = [r for r in neg if r["top1_id"] in {1,2,3,4,5,6,7,8,9} and r["top1_sim"] >= best_f1["t"]]
    if fam:
        print(f"\n※ '정리족(id1~9)' 오발동 원인 {len(fam)}건 — 해당 패밀리 개별 threshold 상향 검토 대상")


if __name__ == "__main__":
    main(sys.argv[1])
