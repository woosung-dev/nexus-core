# 1차 관측표 — 질문 → 조문 매핑. REPORT1.md 를 만든다.
#
# 원칙(선행 _report.py 와 동일): 자동 판정하지 않는다. 셀 수 있는 것만 계산하고
# "이 조문이 이 질문의 정답 근거인가"는 사람이 채울 빈칸으로 남긴다.
# 내 추정은 별도 파일에 '참고(추정)' 라고 명시해 따로 붙인다 — 확정 칸과 섞지 않는다.
import json
import re
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
SRC = DIR.parent / "branch_ablation_2026-08-04"

import sys  # noqa: E402
sys.path.insert(0, str(DIR))
from _expand import articles_for, lexical_match, load_questions  # noqa: E402

_NUM = re.compile(r"^제(\d+)조$")


def nums_of(arts):
    return sorted({int(m.group(1)) for a in arts if (m := _NUM.match(a))})


def compact(ns):
    """[3,39,40,41,42,43] → '3 · 39-43'"""
    if not ns:
        return "—"
    out, i = [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(str(ns[i]) if j == i else f"{ns[i]}-{ns[j]}")
        i = j + 1
    return " · ".join(out)


def prior_neutral_chunks():
    """선행 세션 봇11 중립(R)팔 청크 — 같은 봇·모델·문항. 원질문 검색이 무엇을 물어왔는지의 참고치."""
    d = json.loads((SRC / "_dump_bot11full.json").read_text(encoding="utf-8"))
    by_q = {}
    for r in d["results"]:
        if r["arm"] != "R":
            continue
        buf = by_q.setdefault(r["qid"], {"text": [], "pages": set()})
        for c in r["grounding"]["chunks"]:
            buf["text"].append(unicodedata.normalize("NFC", c.get("text") or ""))
            if c.get("page_number") is not None:
                buf["pages"].add(c["page_number"])
    return {k: {"text": "\n".join(v["text"]), "pages": sorted(v["pages"])} for k, v in by_q.items()}


def main():
    items = load_questions()
    maps = json.loads((DIR / "_map.json").read_text(encoding="utf-8"))["results"]
    prior = prior_neutral_chunks()

    by = {}
    for r in maps:
        by[(r["mode"], r["qid"], r["rep"])] = r

    L = ["# 1차 관측 — 질문 → 조문 매핑 (2026-08-04)", "",
         "선행 세션 하류는 검증됐다(조문을 주면 분기가 산다). 이 표는 **상류** 관측이다 —",
         "질문에서 그 조문에 스스로 도달하는가.", "",
         "- **M1** 어휘매칭 (API 0회) · **M2n** LLM 매핑, 어휘목록=이름만(1,945자) ·",
         "  **M2d** LLM 매핑, 어휘목록=이름+정의(11,233자)",
         "- 매핑 40/40 성공 · 목록 밖 용어 0건 · 재시도 0회",
         "- `기존검색` = 선행 세션 중립팔이 **원 질문**으로 물어온 청크에 그 조문 번호가 이미 있었는가",
         "  (있으면 확장이 새로 여는 게 아니라는 뜻이다)", "",
         "## 표 A — 조문 도달", "",
         "| 문항 | 반복안정 M1/M2n/M2d | M1 조문 | M2n 조문 | M2d 조문 | 기존검색 M2d | **정답근거? M1 / M2n / M2d** |",
         "|---|---|---|---|---|---|---|"]

    detail = []
    summary = {}
    for it in items:
        qid = it["qid"]
        m1 = lexical_match(it["q"])
        m1_arts = articles_for([h for h in m1 if h["articles"]])
        cells, stab, termsets = {}, {}, {}
        for mode, key in (("names", "M2n"), ("defs", "M2d")):
            reps = [by.get((mode, qid, r)) for r in (1, 2)]
            reps = [r for r in reps if r]
            sets = [tuple(sorted(r["terms"])) for r in reps]
            stab[key] = "="if len(set(sets)) == 1 else "≠"
            # 두 반복의 합집합을 대표값으로 쓴다(흔들림은 stab 로 따로 보고).
            uni, seen = [], set()
            for r in reps:
                for h in r["hits"]:
                    if h["term"] not in seen:
                        seen.add(h["term"])
                        uni.append(h)
            termsets[key] = uni
            cells[key] = articles_for(uni)

        pri = prior.get(qid, {"text": "", "pages": []})
        d_nums = nums_of(cells["M2d"])
        hit = sum(1 for n in d_nums if f"제{n}조" in pri["text"])

        L.append(f"| **{qid}** | {'=' if m1 else '—'}/{stab['M2n']}/{stab['M2d']} | "
                 f"{compact(nums_of(m1_arts))} | {compact(nums_of(cells['M2n']))} | "
                 f"{compact(nums_of(cells['M2d']))} | {hit}/{len(d_nums)} | ___ / ___ / ___ |")

        summary[qid] = {"m1": nums_of(m1_arts), "m2n": nums_of(cells["M2n"]),
                        "m2d": nums_of(cells["M2d"]), "prior_pages": pri["pages"]}

        detail.append(f"### {qid} — {it['branch_axis']} · 위험 {it['risk']}\n")
        detail.append(f"> {it['q'][:200]}\n")
        detail.append(f"원질문 검색이 물어온 쪽수(선행 중립팔): {pri['pages'] or '—'}\n")
        for label, hits in (("M1 어휘매칭", m1), ("M2n 이름만", termsets["M2n"]),
                            ("M2d 이름+정의", termsets["M2d"])):
            if not hits:
                detail.append(f"**{label}** — 매칭 0건 (확장하지 않음 = P 팔과 동일)\n")
                continue
            detail.append(f"**{label}**\n")
            detail.append("| 용어 | 조문 | 정의 |")
            detail.append("|---|---|---|")
            for h in hits:
                dfn = re.sub(r"\s+", " ", h["definition"])[:90]
                detail.append(f"| {h['term']} | {' '.join(h['articles'])} | {dfn} |")
            detail.append("")
        detail.append("")

    L += ["", "반복안정 `=` 두 반복의 용어 집합이 같음 · `≠` 다름 · `—` M1 매칭 0건", "",
          "## 표 B — 문항별 상세 (용어·정의·조문)", ""]
    L += detail

    (DIR / "REPORT1.md").write_text("\n".join(L), encoding="utf-8")
    (DIR / "_summary1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("\n".join(L[:40]))
    print(f"\n→ {DIR/'REPORT1.md'}")


if __name__ == "__main__":
    main()
