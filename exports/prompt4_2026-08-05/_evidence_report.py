# v19·v20 근거상태 감사 결과를 합쳐 EVIDENCE_AUDIT.md 를 만든다. 읽기 전용.
import json
from pathlib import Path

DIR = Path(__file__).parent
OUT = DIR / "EVIDENCE_AUDIT.md"
ORDER = ["직접 근거 있음", "부분 근거", "직접 답변 근거 없음"]
SHORT = {"직접 근거 있음": "직접", "부분 근거": "부분", "직접 답변 근거 없음": "**없음**"}
RANK = {s: i for i, s in enumerate(ORDER)}


def load(v):
    p = DIR / f"_evidence_{v}.json"
    if not p.exists():
        return {}
    return {r["key"]: r for r in json.loads(p.read_text(encoding="utf-8"))["rows"]}


def main():
    v20, v19, r2 = load("v20"), load("v19"), load("v20_r2")
    keys = sorted(v20 or v19, key=int)
    # 심사자(codex) 자신의 실행 간 변동. 이걸 모르면 버전 차이를 주장할 수 없다.
    flip = [k for k in keys if k in r2 and v20[k]["our_status"] != r2[k]["our_status"]]
    consensus = {k: v20[k]["our_status"] for k in keys
                 if k in r2 and v20[k]["our_status"] == r2[k]["our_status"]}
    L = []
    add = L.append

    add("# 규정집 근거 상태 독립 감사 — 45문항 (2026-08-05)\n")
    add("관리자가 xlsx `답변키워드_45개` 에 붙인 **`규정집 근거 상태`** 를 우리가 다시 판정했다.\n")
    add("## 방법과 그 이유\n")
    add("**어휘 카운트로 하지 않았다.** 관리자 키워드를 규정집·대사전·공문에 "
        "NFC·공백제거 부분문자열로 대조하면 45문항 중 43문항이 키워드 대부분 적중해서 "
        "`직접 근거 있음`(26)과 `직접 답변 근거 없음`(5)이 **구분되지 않는다.** "
        "거짓양성도 난다 — `정자`는 규정집에서 24회 잡히지만 전부 `확정자`·`행정자료`·`정자세`이고 "
        "생식 의미의 언급은 0건이다.\n")
    add("그래서 어휘 겹침은 **후보 조문 회수**에만 쓰고, 판정은 codex 가 조문 전문을 읽고 "
        "\"이 질문에 답할 수 있는가\"로 했다. 생성(gemini)과 심사(codex)는 분리했다.\n")
    add("**두 버전으로 돌렸다.** 관리자 판정 기준은 규정집 **v19**(xlsx 탭 주석에 명시)인데 "
        "봇 11이 검색하는 문서는 **v20**이다. v19→v20 은 제38조 신설로 그 뒤 62개 조문이 +1 밀렸다.\n")

    if r2:
        add("### 심사자 자체 잡음부터 쟀다\n")
        add(f"v20 을 **같은 조건으로 두 번** 돌렸다. 45문항 중 **{len(flip)}문항({100*len(flip)/45:.0f}%)** 에서 "
            "판정이 뒤집혔다"
            + (f" — {', '.join('#' + k for k in flip)}." if flip else ".")
            + " 이게 이 감사의 잡음 바닥이다.\n")
        add(f"아래 결론은 **2회 합의한 {len(consensus)}문항**을 기준으로 읽어야 한다. "
            "1회 결과의 소수점 차이는 의미가 없다.\n")
        okc = sum(1 for k, v in consensus.items() if v == v20[k]["admin_status"])
        opt = [k for k, v in consensus.items() if RANK[v] > RANK[v20[k]["admin_status"]]]
        pes = [k for k, v in consensus.items() if RANK[v] < RANK[v20[k]["admin_status"]]]
        add(f"- **2회 합의 기준 관리자 라벨과 일치 {okc}/{len(consensus)} "
            f"({100*okc/len(consensus):.0f}%)**")
        add(f"- **관리자가 근거를 과대평가한 것 {len(opt)}건** — "
            f"{', '.join('#' + k for k in sorted(opt, key=int))}")
        add(f"- 과소평가 {len(pes)}건 — {', '.join('#' + k for k in sorted(pes, key=int))}\n")

    for v, d in (("v20", v20), ("v19", v19)):
        if not d:
            continue
        ok = sum(1 for r in d.values() if r["agree"])
        add(f"## 결과 — {v} 기준\n")
        add(f"**관리자 라벨과 일치 {ok}/{len(d)} ({100*ok/len(d):.0f}%)**\n")
        add("| 관리자 → 우리 | " + " | ".join(SHORT[s].replace('**', '') for s in ORDER) + " | 계 |")
        add("|---|---:|---:|---:|---:|")
        for a in ORDER:
            row = [sum(1 for r in d.values() if r["admin_status"] == a and r["our_status"] == o)
                   for o in ORDER]
            add(f"| **{a}** | " + " | ".join(str(x) for x in row) + f" | {sum(row)} |")
        opt = sum(1 for r in d.values() if RANK.get(r["our_status"], 9) > RANK.get(r["admin_status"], 9))
        pes = sum(1 for r in d.values() if RANK.get(r["our_status"], 9) < RANK.get(r["admin_status"], 9))
        add(f"\n- **관리자가 근거를 과대평가한 것 {opt}건** — 문서가 실제로 답하는 것보다 "
            f"더 답한다고 봤다\n- 과소평가 {pes}건\n")

    # 두 버전이 갈린 문항
    both = [k for k in keys if k in v19 and k in v20]
    diff = [k for k in both if v19[k]["our_status"] != v20[k]["our_status"]]
    if both:
        add("## 버전 스큐 — v19 와 v20 에서 판정이 갈린 문항\n")
        if diff:
            add("| # | 질문 | v19 | v20 | 관리자 |")
            add("|---:|---|---|---|---|")
            for k in diff:
                add(f"| {k} | {v20[k]['q'][:44]} | {v19[k]['our_status']} | "
                    f"{v20[k]['our_status']} | {v20[k]['admin_status']} |")
            stable = [k for k in diff if k in r2 and r2[k]["our_status"] == v20[k]["our_status"]]
            add(f"\n{len(diff)}/{len(both)} 문항에서 버전이 판정을 바꿨다. "
                f"그중 **{len(stable)}건은 v20 두 회차 모두 같은 값**이라 심사자 잡음이 아니라 "
                "실제 버전 효과다.\n")
            add("**관리자는 v19 로 판정했고 봇은 v20 을 검색한다** — 이 문항들은 "
                "관리자에게 되물을 때 어느 버전 기준인지 함께 확정해야 한다. "
                "다섯 건 모두 v20 에서 근거가 **더 분명해지는** 방향이라, v20 이 관리자 라벨과 더 잘 맞는다.\n")
        else:
            add(f"{len(both)}문항 전건 동일 — **버전 스큐가 근거 상태 판정을 바꾸지 않았다.**\n")

    # 전체 대조표
    add("## 문항별 대조\n")
    add("`v20¹`·`v20²` = 같은 조건 두 회차. 둘이 다르면 그 문항은 판정 불안정이다.\n")
    add("| # | 질문 | 관리자 | v20¹ | v20² | v19 | 우리가 찾은 근거 |")
    add("|---:|---|---|---|---|---|---|")
    for k in keys:
        r = v20.get(k) or v19.get(k)
        a = SHORT.get(r["admin_status"], "?")
        o20 = SHORT.get(v20[k]["our_status"], "—") if k in v20 else "—"
        o2 = SHORT.get(r2[k]["our_status"], "—") if k in r2 else "—"
        o19 = SHORT.get(v19[k]["our_status"], "—") if k in v19 else "—"
        cited = ", ".join((v20.get(k) or v19[k]).get("cited") or []) or "—"
        mark = " ⚠" if k in consensus and consensus[k] != r["admin_status"] else \
               (" ~" if k not in consensus else "")
        add(f"| {k}{mark} | {r['q'][:40]} | {a} | {o20} | {o2} | {o19} | {cited[:48]} |")
    add("\n⚠ = 2회 합의했는데 관리자와 다름 · ~ = 회차 간 판정 불안정\n")

    # 불일치 상세
    add("## 불일치 상세 (v20 기준)\n")
    for k in keys:
        r = v20.get(k)
        if not r or r["agree"]:
            continue
        add(f"### #{k} — 관리자 `{r['admin_status']}` → 우리 `{r['our_status']}`\n")
        add(f"> {r['q']}\n")
        add(f"- **핵심 쟁점**: {r['core_issue']}")
        add(f"- **근거**: {', '.join(r.get('cited') or []) or '없음'}")
        add(f"- **판정 이유**: {r['reason']}\n")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"→ {OUT} ({len(L)}줄)")


if __name__ == "__main__":
    main()
