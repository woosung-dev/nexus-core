"""규칙 매칭 BM25 하한(`min_score`) 스윕 — 45문항 전수 · LLM 0회 · DB 0회.

앞선 스윕(n=6)은 **판정기가 양성으로 뽑은 문항만** 표본으로 썼다. 그 집합이 실행마다
흔들린다(v3 `[12,18,33,34,36,39,45]` → 최신 `[18,20,33,34,36,39,45]`). 표본이 난수에
매달려 있으면 하한도 난수다.

`min_score` 가 사는 곳은 `match_policy_rule` 이고 이건 BM25 어휘 비교라 모델이 없다.
판정기는 「되물을까」만, 하한은 「어느 규칙이냐」만 정한다 — 그래서 판정 결과와 무관하게
**45문항 전부에** 결정론적으로 돌릴 수 있다. 판정기가 흔들려 어떤 문항이든 양성이 될 수
있으므로 오히려 전수가 옳은 표본이다.

    cd backend && WIKI_DENSE_SCALES="" uv run python -u ../exports/clarify_eval/_sweep.py

산출: 표 출력 + `sweep.json`. 규칙·예시질문을 고칠 때마다 다시 돌려라 —
경계(거짓양성 최고 · 참양성 최저)가 움직이면 하한을 다시 골라야 한다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ★ import 전에 dense 를 끈다 — 임베딩 API 를 한 번도 부르지 않는다 (_run.py 와 같은 방식)
os.environ.setdefault("WIKI_DENSE_SCALES", "")

DIR = Path(__file__).resolve().parent
REPO = DIR.parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.schemas.clarification_policy import ClarificationPolicy  # noqa: E402
from app.services.chat_service import CLARIFICATION_MIN_SCORE  # noqa: E402
from app.services.clarification_trigger import (  # noqa: E402
    MIN_RULE_DOMINANCE,
    match_policy_rule,
)

QUESTIONS = REPO / "exports" / "wiki_eval" / "questions.json"
POLICY = REPO / "docs" / "architecture" / "clarification-policy-v2-2026-08-10.json"
OUT = DIR / "sweep.json"

# 정답지. 정책 JSON `_note` 의 표적 4건이 참양성이고 **나머지 41문항은 전부 None** 이다.
# None = 「걸리는 규칙이 없어야 한다」 = handoff 가 맞는 문항.
EXPECTED: dict[int, str] = {
    33: "family-start-12day",
    34: "family-start-pre-rite",
    18: "child-first-gen-eligibility",
    45: "b4u-tier",
}


def main() -> None:
    policy = ClarificationPolicy.model_validate(json.loads(POLICY.read_text(encoding="utf-8")))
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))

    # 1. 하한 없이 돌려 원점수를 본다. 지배도 게이트(1.5배)는 그대로 걸린다.
    rows = []
    for item in questions:
        number = int(item["n"])
        rule, score = match_policy_rule(item["question"], policy, min_score=0.0)
        expected = EXPECTED.get(number)
        matched = rule.id if rule else None
        rows.append(
            {
                "n": number,
                "question": item["question"],
                "top_rule": matched,
                "top_score": round(score, 2),
                "expected": expected,
                # 하한이 0 일 때의 판정. tp/tn 은 하한이 필요 없다는 뜻이다.
                "verdict": _verdict(matched, expected),
            }
        )

    true_positive = [r for r in rows if r["expected"] is not None]
    false_positive = [r for r in rows if r["expected"] is None and r["top_rule"] is not None]
    ceiling = max(false_positive, key=lambda r: r["top_score"]) if false_positive else None
    floor = min(true_positive, key=lambda r: r["top_score"]) if true_positive else None

    # 2. 관측된 점수에서만 결과가 바뀐다. 게이트가 `top_score < min_score` 라 관측값 자체는
    #    통과하므로, 관측값과 그 바로 위(+0.01)를 같이 넣어야 경계가 제대로 보인다.
    observed = {r["top_score"] for r in rows}
    grid = sorted(observed | {round(s + 0.01, 2) for s in observed} | {0.0})
    sweep = []
    for threshold in grid:
        wrong = []
        for item in questions:
            number = int(item["n"])
            rule, _ = match_policy_rule(item["question"], policy, min_score=threshold)
            matched = rule.id if rule else None
            if matched != EXPECTED.get(number):
                wrong.append(number)
        sweep.append({"min_score": threshold, "correct": len(questions) - len(wrong), "wrong": wrong})

    best = max(s["correct"] for s in sweep)
    perfect = [s["min_score"] for s in sweep if s["correct"] == best]

    # ── 출력 ──────────────────────────────────────────────
    print(f"45문항 · 규칙 {len(policy.rules)}개 · MIN_RULE_DOMINANCE={MIN_RULE_DOMINANCE}")
    print(f"프로덕션 하한 CLARIFICATION_MIN_SCORE={CLARIFICATION_MIN_SCORE}\n")
    print(f"{'n':>3} {'BM25':>7}  {'기대':28s} {'하한0 매칭':28s} 질문")
    for row in sorted(rows, key=lambda r: -r["top_score"]):
        print(
            f"{row['n']:>3} {row['top_score']:7.2f}  {str(row['expected']):28s} "
            f"{str(row['top_rule']):28s} {row['question'][:30]}"
        )

    print("\n― 스윕 ―")
    for entry in sweep:
        mark = "←" if entry["correct"] == best else " "
        print(f"  min_score={entry['min_score']:6.2f}  {entry['correct']:2d}/45 {mark} "
              f"오답 {entry['wrong'] or '없음'}")

    print("\n― 경계 ―")
    if ceiling:
        print(f"  거짓양성 최고  #{ceiling['n']:<3} {ceiling['top_score']:6.2f}  "
              f"→ {ceiling['top_rule']}")
    if floor:
        print(f"  참양성 최저    #{floor['n']:<3} {floor['top_score']:6.2f}  → {floor['expected']}")
    if ceiling and floor:
        low, high = ceiling["top_score"], floor["top_score"]
        if low < high:
            print(f"  안전 구간      ({low}, {high}]  · 기하 중점 {(low * high) ** 0.5:.2f}")
            inside = low < CLARIFICATION_MIN_SCORE <= high
            print(f"  현행 {CLARIFICATION_MIN_SCORE} 은 구간 {'안' if inside else '**밖**'}에 있다 "
                  f"(아래 여유 ×{CLARIFICATION_MIN_SCORE / low:.3f} · "
                  f"위 여유 ×{high / CLARIFICATION_MIN_SCORE:.3f})")
        else:
            print(f"  ⚠ 안전 구간이 **없다** — 거짓양성 {low} 이 참양성 {high} 이상이다. "
                  f"하한으로는 못 가른다. request_examples 를 고쳐라")
    print(f"  최고 정확도 {best}/45 를 내는 하한: {perfect[0]} ~ {perfect[-1]}")

    OUT.write_text(
        json.dumps(
            {
                "min_rule_dominance": MIN_RULE_DOMINANCE,
                "production_min_score": CLARIFICATION_MIN_SCORE,
                "false_positive_ceiling": ceiling,
                "true_positive_floor": floor,
                "sweep": sweep,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n→ {OUT}")


def _verdict(matched: str | None, expected: str | None) -> str:
    if expected is None:
        return "tn" if matched is None else "fp"
    if matched == expected:
        return "tp"
    return "fn" if matched is None else "wrong-rule"


if __name__ == "__main__":
    main()
