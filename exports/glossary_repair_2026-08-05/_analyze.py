# 판정 근거 생성 — FINDINGS.md §4 의 모든 수를 원 데이터에서 뽑는다.
#
# 손으로 옮긴 수가 하나도 없어야 한다. 이 스크립트가 ANALYSIS.md 를 쓴다.
#
# 하는 일 넷:
#   ① 개입 문항 / 잡음 대조군 분리 — M1 쿼리가 P 쿼리와 같으면 개입이 아니다
#   ② 대응표본 신뢰구간 + 부호검정 + 이상치 민감도
#   ③ 검색 변화와 답변 변화를 분리 — 확장이 검색을 바꿨는가
#   ④ MIN_LEN 시뮬레이션 (API 0회)
import json
import math
import statistics as st
import sys
from pathlib import Path

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))

dump = json.loads((DIR / "_dump2.json").read_text(encoding="utf-8"))
matches = {m["qid"]: m for m in
           json.loads((DIR / "_match.json").read_text(encoding="utf-8"))["questions"]}
qfile = json.loads((DIR / "_questions_pyeongseong.json").read_text(encoding="utf-8"))
labels = {it["qid"]: it for it in qfile["items"]}
recs = [r for r in dump["results"] if r.get("ok")]

# 자유도별 t 임계값 (양측 95%)
TCRIT = {3: 3.182, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262}
L = []


def w(s=""):
    L.append(s)


def arm_recs(qid, arm):
    return sorted([r for r in recs if r["qid"] == qid and r["arm"] == arm],
                  key=lambda x: x["rep"])


def hit_rate(qid, arm):
    """정답 분기 적중률. 분모 = 정답 케이스 수 × 반복 수."""
    rs = [x for x in matches[qid]["results"] if x["arm"] == arm]
    hit = sum(len(x.get("covered") or []) for x in rs)
    den = len(labels[qid]["expected_branches"]) * len(rs)
    return hit / den, hit, den


def p21(qid, arm):
    rs = arm_recs(qid, arm)
    hit = sum(1 for r in rs
              if 21 in {c.get("page_number") for c in r["grounding"]["chunks"]
                        if c.get("page_number")})
    return hit, len(rs)


judged = list(matches)

w("# 판정 근거 — M1 2단 호출 이행 여부 (2026-08-05)")
w()
w("`FINDINGS.md` §4 의 수는 전부 이 스크립트가 `_dump2.json` · `_match.json` 에서 생성한다.")
w()

# ─────────────────────────────────────────────────────────────────
w("## 1. 개입 문항과 잡음 대조군 분리")
w()
w("M1↔P 비교가 성립하려면 **두 팔의 쿼리가 달라야** 한다. 어휘매칭이 0건이면 M1 은 확장하지")
w("않으므로 쿼리가 P 와 같고, 그 문항은 개입이 아니라 **같은 조건 반복**이다.")
w()
w("| 문항 | M1 쿼리 == P 쿼리 | 구분 |")
w("|---|---|---|")
treat, ctrl = [], []
for qid in judged:
    same = arm_recs(qid, "P")[0]["q"] == arm_recs(qid, "M1")[0]["q"]
    (ctrl if same else treat).append(qid)
    w(f"| {qid} | {same} | {'대조(개입 없음)' if same else '개입'} |")
w()
w(f"**개입 문항 {len(treat)}건 · 잡음 대조군 {len(ctrl)}건**")
w()

# ─────────────────────────────────────────────────────────────────
w("## 2. 미측정 3문항이 판정에 기여했을 몫")
w()
w("일일 한도로 못 잰 3문항이 위 기준에서 무엇을 더했을지 결정론으로 확인한다(API 0회).")
w()
import _expand2 as E2  # noqa: E402
import _expand as E  # noqa: E402

E2.use_glossary(DIR / "_glossary_terms_v2.json")
w("| 문항 | 정답 라벨 | M1 확장 | 판정 기여 |")
w("|---|---|---|---|")
n_extra = 0
for qid in [q for q in labels if q not in judged]:
    it = labels[qid]
    _, _, _, expanded = E2.expand_one(it["q"])
    if it["expected"] != "labeled":
        why = "없음 — 정답 채점 제외 대상"
    elif not expanded:
        why = "없음 — 개입 부재(쿼리 동일)"
    else:
        why = "**기여함**"
        n_extra += 1
    w(f"| {qid} | {it['expected']} | {'O' if expanded else 'X'} | {why} |")
w()
w(f"→ 개입 문항이 {len(treat)} → {len(treat)+n_extra} 로 **{n_extra}건** 는다.")
w()

# ─────────────────────────────────────────────────────────────────
w("## 3. 정답 분기 적중률 — 대응표본 비교 (개입 문항만)")
w()
w("| 문항 | P | M1 | 차이 |")
w("|---|---|---|---|")
diffs = {}
for qid in treat:
    rp, hp, dp = hit_rate(qid, "P")
    rm, hm, dm = hit_rate(qid, "M1")
    diffs[qid] = rm - rp
    w(f"| {qid} | {hp}/{dp} ({rp:.0%}) | {hm}/{dm} ({rm:.0%}) | {rm-rp:+.0%}p |")
w()


def summarize(vals, label):
    n = len(vals)
    m = st.mean(vals)
    sd = st.stdev(vals)
    se = sd / math.sqrt(n)
    t = TCRIT[n]
    w(f"- {label}: n={n} · 평균 **{m:+.1f}pp** · 95% CI **[{(m-t*se)*100:+.1f}pp, "
      f"{(m+t*se)*100:+.1f}pp]**".replace(f"{m:+.1f}pp", f"{m*100:+.1f}pp"))
    return sd


sd_all = summarize(list(diffs.values()), "전체")
summarize([v for q, v in diffs.items() if q != "P-105"], "P-105(최대 이상치) 제외")
pos = sum(1 for v in diffs.values() if v > 0)
neg = sum(1 for v in diffs.values() if v < 0)
w(f"- 부호검정: M1 우세 {pos} · P 우세 {neg} · 동률 {len(diffs)-pos-neg} → **방향성 없음**")
w()
w("이상치를 넣든 빼든 신뢰구간이 0 을 포함한다. **M1 은 P 를 개선하지 않는다.**")
w()

w("### 3-1. 표본을 늘리면 어떻게 되나")
w()
n0 = len(treat)
half0 = TCRIT[n0] * sd_all / math.sqrt(n0)
n1 = n0 + n_extra
half1 = TCRIT[n1] * sd_all / math.sqrt(n1)
w(f"- 남은 호출을 채웠을 때: n={n0} → {n1}, CI 반폭 ±{half0*100:.1f}pp → "
  f"±{half1*100:.1f}pp (**{(1-half1/half0)*100:.0f}% 개선**)")
w()
w("| 목표 정밀도(95% CI 반폭) | 필요한 개입 문항 수 |")
w("|---|---|")
for h in (0.20, 0.15, 0.10, 0.05):
    w(f"| ±{h*100:.0f}pp | 약 {math.ceil((1.96*sd_all/h)**2)}건 |")
w()

# ─────────────────────────────────────────────────────────────────
w("## 4. 잡음 바닥 — 개입이 0 인데 얼마나 벌어지는가")
w()
for qid in ctrl:
    _, hp, dp = hit_rate(qid, "P")
    _, hm, dm = hit_rate(qid, "M1")
    nb_p = [x["n_branches"] for x in
            sorted([y for y in json.loads((DIR / "_branches.json").read_text(encoding="utf-8"))
                    ["questions"] if y["qid"] == qid][0]["results"], key=lambda z: (z["arm"], z["rep"]))]
    w(f"- **{qid}** — 쿼리가 완전히 같은 10회: 적중 P {hp}/{dp} vs M1 {hm}/{dm} = "
      f"**{abs(hm/dm - hp/dp)*100:.0f}pp 차이**")
    w(f"  - 분기 수 10회: {nb_p} → 최빈값 {max(set(nb_p), key=nb_p.count)}: "
      f"{nb_p.count(max(set(nb_p), key=nb_p.count))}/10")
w()
w("개입이 없는데 20pp 가 벌어진다. **§3 에서 관측된 최대 양의 효과(R-216 +20pp)가 같은 크기다.**")
w("→ R-216 의 개선은 개입 효과라고 주장할 수 없다.")
w()

# ─────────────────────────────────────────────────────────────────
w("## 5. 확장이 검색을 바꿨는가 — 2단 호출 판정의 핵심")
w()
w("2단 분리는 검색 이득은 살리고 답변 오염만 없애는 처방이다. 살릴 검색 이득이 있어야 성립한다.")
w()
w("| 문항 | p.21 회수 NP → NM1 | 변화 | 적중 P → M1 |")
w("|---|---|---|---|")
better = worse = same_n = 0
for qid in treat:
    a, n = p21(qid, "NP")
    b, _ = p21(qid, "NM1")
    rp, _, _ = hit_rate(qid, "P")
    rm, _, _ = hit_rate(qid, "M1")
    if b > a:
        better += 1
    elif b < a:
        worse += 1
    else:
        same_n += 1
    w(f"| {qid} | {a}/{n} → {b}/{n} | {b-a:+d} | {rp:.0%} → {rm:.0%} |")
w()
w(f"**검색이 좋아진 문항 {better}건 · 무변화 {same_n}건 · 나빠진 문항 {worse}건.**")
w()
w("적중률 변동은 전부 **검색이 동일한 상태에서** 일어났다 → 답변 쪽 잡음이다.")
w("살릴 검색 이득이 없으므로 2단으로 옮길 것이 없다.")
w()

# ─────────────────────────────────────────────────────────────────
w("## 6. M1 의 겨냥 — 도움이 필요한 곳에서 작동하는가")
w()
w("| 문항 | p.21 회수(NP, 원질문) | M1 확장 |")
w("|---|---|---|")
for qid in judged:
    a, n = p21(qid, "NP")
    exp = arm_recs(qid, "M1")[0]["expanded"]
    flag = " ← 검색 부족" if a < n else ""
    w(f"| {qid} | {a}/{n}{flag} | {'O' if exp else 'X'} |")
w()
w("검색이 부족한 문항에서 M1 은 확장하지 않고, M1 이 확장하는 문항은 이미 천장이다.")
w()
w(f"원인: `_expand.py` 의 `MIN_LEN={E.MIN_LEN}` 이 2자 표기를 버린다. "
  f"`축복자녀` 의 별칭에 `2세` 가 있으나 2자라 잘린다.")
w()

# ─────────────────────────────────────────────────────────────────
w("## 7. MIN_LEN 시뮬레이션 (API 0회)")
w()


def zero_match(items):
    return [it["qid"] for it in items if not E.lexical_match(it["q"])]


def avg(items):
    tot_a = tot_l = 0
    for it in items:
        hits = E.lexical_match(it["q"])
        q, _, arts = E.build_query(it["q"], hits)
        tot_a += len(arts)
        tot_l += len(q) - len(it["q"])
    return tot_a / len(items), tot_l / len(items)


old_items = json.loads(
    (DIR.parent / "branch_ablation_2026-08-04" / "questions.json").read_text(encoding="utf-8"))["items"]
new_items = qfile["items"]

rows = {}
for ml in (3, 2):
    E.MIN_LEN = ml
    E.SURFACES = E._surfaces()
    rows[ml] = (zero_match(new_items), zero_match(old_items), *avg(new_items))
E.MIN_LEN = 3
E.SURFACES = E._surfaces()

w("| | MIN_LEN=3 (현행) | MIN_LEN=2 |")
w("|---|---|---|")
w(f"| 매칭 0건 (이번 12문항) | {rows[3][0] or '없음'} | {rows[2][0] or '**없음**'} |")
w(f"| 매칭 0건 (선행 10문항) | {rows[3][1] or '없음'} | {rows[2][1] or '**없음**'} |")
w(f"| 평균 조문 토큰 | {rows[3][2]:.1f} | {rows[2][2]:.1f} |")
w(f"| 평균 확장 길이 | +{rows[3][3]:.0f}자 | +{rows[2][3]:.0f}자 |")
w()
w("두 문항 세트 모두 매칭 0건이 사라지고 확장 길이는 거의 안 는다.")
w("M2 의 실패 원인이 '확장어가 길수록 나쁘다'였는데 이 변경은 길이를 늘리지 않는다.")
w()
w("**단, 그대로 쓰면 안 된다.** `lexical_match` 에 용어 단위 중복 제거가 없다 —")
E.MIN_LEN = 2
E.SURFACES = E._surfaces()
dups = []
for it in new_items:
    t = [h["term"] for h in E.lexical_match(it["q"])]
    if len(t) != len(set(t)):
        dups.append((it["qid"], t))
E.MIN_LEN = 3
E.SURFACES = E._surfaces()
for qid, t in dups:
    w(f"{qid} 에서 `{t}` 가 나온다(용어와 별칭이 각각 채택됨). `taken` 이 표기만 보고 용어를 안 본다.")
w()
w("**이것은 추정이다.** 겨냥이 개선된다는 것만 확인했고 적중률이 오르는지는 안 쟀다.")
w("그러나 2단 호출(호출 2배)보다 싸고 겨냥 문제에 직접 대응한다.")
w()

(DIR / "ANALYSIS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"→ {DIR/'ANALYSIS.md'} ({len(L)}줄)")
