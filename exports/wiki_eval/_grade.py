# 관리자 정답 10건 × 여러 팔 → codex LLM-judge 채점. Gemini 과금 0(구독 CLI 사용).
#
# 키워드 자는 **어휘를 센다**. 절차 표현("최신 공문 확인" 등)이 많아 넓게 말하는 팔이 유리하다.
# 여기서는 내용으로 잰다 — 관리자 정답과 대조한다.
#
# 편향 방지 2가지
#   ① 눈가림  팔 이름을 숨기고 갑/을/병/… 로 준다
#   ② 순서    문항마다 순서를 바꾼다(문항 번호로 결정적 셔플 — 재현된다)
#
# 판정 기준 셋 중 ②·③을 여기서 낸다(①은 `_run.py` 의 키워드 충족률).
#
# 사용: uv run python ../exports/wiki_eval/_grade.py
import argparse
import json
import re
import subprocess
from pathlib import Path

DIR = Path(__file__).parent
ANSWERS = DIR / "answers.json"
EVIDENCE = DIR / "corpus_evidence.json"
OUT = DIR / "grades.json"

ARMS = ["rag", "wiki", "wiki_budget", "wiki_first", "hybrid",
        "union_ac", "union_ab2", "arb_ac", "full"]
TITLE = {
    "rag": "A RAG",
    "wiki": "B 위키→원문",
    "wiki_budget": "B′ 예산",
    "wiki_first": "C 위키본문",
    "hybrid": "F A+BM25",
    "union_ac": "A+C 사후결합",
    "union_ab2": "A+B′ 사후결합",
    "arb_ac": "G′ A+C 중재",
    "full": "D 통째",
}
LABELS = ["갑", "을", "병", "정", "무", "기", "경", "신"]

RUBRIC = """너는 종교단체 행정 규정 챗봇의 답변을 채점한다.
관리자(실무 책임자)가 직접 쓴 정답을 기준으로, 아래 답변들을 각각 채점하라.

채점 항목 (답변마다)
  fact   0~2  정답의 핵심 사실을 맞혔는가. 2=맞음 1=일부 2=0 틀리거나 없음
  cover  0~2  정답이 담은 요소를 얼마나 담았는가. 2=대부분 1=절반 0=거의 없음
  harm   0 또는 -2  정답과 배치되는 잘못된 안내를 했으면 -2 (숫자·자격·절차 오류)
  total  fact + cover + harm  (-2 ~ 4)

주의
- 길이로 점수를 주지 마라. 짧아도 정답의 핵심을 맞혔으면 만점이다.
- 문체·친절함은 채점 대상이 아니다. 사실만 본다.
- "확인되지 않습니다 + 담당자 연결"만 한 답변은 fact 0 cover 0 harm 0 으로 하고
  refusal 을 true 로 표시하라.

출력은 JSON 하나만. 다른 말은 쓰지 마라.
%s"""


def live_arms(rows: list[dict], only: set[str] | None = None) -> list[str]:
    """채점 폭을 좁힐 수 있게 한다.

    codex 판정은 비교식이라 **함께 놓인 답이 달라지면 절대값이 흔들린다** —
    같은 답을 5팔로 재고 7팔로 다시 쟀더니 wiki 1.90 → 1.40 으로 움직였다.
    비교하려는 팔만 같은 폭으로 재는 것이 맞다.
    """
    return [a for a in ARMS if any(a in r for r in rows) and (only is None or a in only)]


def order_for(n: int, arms: list[str]) -> list[str]:
    """문항 번호로 결정적으로 순서를 돌린다 — 위치 편향을 없애면서 재현 가능하게."""
    k = n % len(arms)
    return arms[k:] + arms[:k]


def grade_one(row: dict, arms: list[str]) -> dict | None:
    order = order_for(row["n"], arms)
    labels = LABELS[: len(order)]
    schema = ",\n ".join(
        f'"{lab}":{{"fact":0,"cover":0,"harm":0,"total":0,"refusal":false,"why":"한 줄"}}'
        for lab in labels
    )
    body = [RUBRIC % ("{" + schema + "}"), "", f"# 질문\n{row['question']}", "",
            f"# 관리자 정답\n{row['golden']}"]
    for label, arm in zip(labels, order):
        ans = (row.get(arm) or {}).get("answer", "").strip() or "(빈 응답)"
        body.append(f"\n# 답변 {label}\n{ans}")

    proc = subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", "\n".join(body)],
        capture_output=True, text=True, timeout=600,
    )
    m = re.search(r"\{.*\}", proc.stdout, re.S)
    if not m:
        print(f"  #{row['n']} 파싱 실패")
        return None
    try:
        parsed = json.loads(m.group())
    except json.JSONDecodeError:
        print(f"  #{row['n']} JSON 오류")
        return None

    # 갑/을/병/… → 실제 팔 이름으로 되돌린다
    return {arm: parsed.get(label, {}) for label, arm in zip(labels, order)}


def deferral_table(graded: list[dict], arms: list[str]) -> None:
    """③ 유보 정확도.

    지금까지의 채점표에는 **"모른다고 말하는 능력"** 축이 없었다. 오히려 유보하면
    키워드 0% 라 벌점이었다. 그런데 이 판은 반대다 — 정답지 시트 ① 「"확인되지 않습니다
    + 담당자 연결"만 해도 정답인가」가 45/45 전부 "예" 이고, 45문항 중 위험도 '상' 이 28건이다.
    틀린 답보다 유보가 낫다.

    **두 기준을 함께 낸다. 하나만 보면 결론이 뒤집힌다.**

      코퍼스 기준   정답의 근거가 규정집v20+대사전v4 안에 있는가(`corpus_evidence.json`).
                    근거가 없는 문항에서의 유보는 옳은 행동이다.
      관리자 기준   golden 이 확답인가. golden 10건은 **전부 확답형**이라, 이 기준에서는
                    모든 유보가 감점이다. 코퍼스 기준만 보면 이 사실이 안 보인다.
    """
    ev = {k: v for k, v in json.loads(EVIDENCE.read_text(encoding="utf-8")).items()
          if not k.startswith("_")}
    n_out = sum(1 for v in ev.values() if v["label"] == "out")
    n_in = len(ev) - n_out

    print(f"\n③ 유보 정확도 — 코퍼스 근거 있음 {n_in}건 · 없음 {n_out}건")
    print(f"  {'':13} {'정당유보':>8} {'과잉유보':>8} {'정당확답':>8} {'유해확답':>8}")
    for arm in arms:
        good_def = over_def = good_ans = harm_ans = 0
        for g in graded:
            label = ev.get(str(g["n"]), {}).get("label")
            if label is None:
                continue
            grade = g["grades"].get(arm, {})
            if grade.get("refusal"):
                if label == "out":
                    good_def += 1
                else:
                    over_def += 1
            elif grade.get("harm", 0) < 0:
                harm_ans += 1
            elif label == "in":
                good_ans += 1
        print(f"  {TITLE[arm]:13} {good_def:>5}/{n_out} {over_def:>5}/{n_in} "
              f"{good_ans:>8} {harm_ans:>8}")

    print("\n  (관리자 기준 병기 — golden 10건 전부 확답형이므로 유보는 모두 감점)")
    for arm in arms:
        ref = sum(1 for g in graded if g["grades"].get(arm, {}).get("refusal"))
        print(f"    {TITLE[arm]:13} 확답형 문항에서의 유보 {ref}/{len(graded)}건")


def main(only: set[str] | None = None, out: Path = OUT) -> None:
    rows = [r for r in json.loads(ANSWERS.read_text(encoding="utf-8")) if r.get("golden")]
    arms = live_arms(rows, only)
    print(f"정답 있는 문항 {len(rows)}건 × {len(arms)}팔({', '.join(TITLE[a] for a in arms)}) · 눈가림 채점\n")

    graded = []
    for i, row in enumerate(rows, 1):
        res = grade_one(row, arms)
        if not res:
            continue
        graded.append({"n": row["n"], "question": row["question"], "grades": res})
        out.write_text(json.dumps(graded, ensure_ascii=False, indent=2), encoding="utf-8")
        bits = " | ".join(f"{a} {res.get(a, {}).get('total', '?')}" for a in arms)
        print(f"[{i:2d}/{len(rows)}] #{row['n']:<3} {bits}   {row['question'][:32]}")

    print(f"\n→ {out}")
    print("\n② 내용 점수")
    for arm in arms:
        vals = [g["grades"].get(arm, {}).get("total") for g in graded]
        vals = [v for v in vals if isinstance(v, (int, float))]
        ref = sum(1 for g in graded if g["grades"].get(arm, {}).get("refusal"))
        harm = sum(1 for g in graded if g["grades"].get(arm, {}).get("harm", 0) < 0)
        if vals:
            print(f"  {TITLE[arm]:13} 평균 {sum(vals)/len(vals):.2f}/4 · 만점 "
                  f"{sum(1 for v in vals if v == 4)}건 · 유해 {harm}건 · 유보 {ref}건")

    deferral_table(graded, arms)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=None, help="쉼표 구분 팔 키. 생략하면 전부")
    ap.add_argument("--out", default=None, help="결과 파일. 생략하면 grades.json")
    a = ap.parse_args()
    main({x.strip() for x in a.arms.split(",")} if a.arms else None,
         Path(a.out) if a.out else OUT)
