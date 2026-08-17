# 2차 관측표 — 검색이 무엇을 물어왔나. REPORT2.md 를 만든다.
#
# 여기서 계산하는 것은 셀 수 있는 것뿐이다 — 청크 수, 회수 쪽수, p.21 회수, 인용 수, 답변 길이.
# 분기 수·미근거 조건은 _branches2.py(codex) 산출물을 읽어 붙이기만 한다.
#
# p.21 = 2026 정본 편성 비교표. 선행 세션이 R-219 실패의 직접 원인으로 지목한 청크다.
import json
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
PERSONA = ("P", "M1", "M2")
NEUTRAL = ("NP", "NM1", "NM2")
TWIN = {"P": "NP", "M1": "NM1", "M2": "NM2"}
REG = "규정집"          # 봇11 문서 2종 중 규정집 2026 (나머지는 용어집 대사전)
KEY_PAGE = 21


def pages_of(rec):
    return sorted({c.get("page_number") for c in rec["grounding"]["chunks"]
                   if c.get("page_number") is not None})


def has_key_page(rec):
    return any(c.get("page_number") == KEY_PAGE
               and REG in unicodedata.normalize("NFC", c.get("title") or "")
               for c in rec["grounding"]["chunks"])


def main():
    d = json.loads((DIR / "_dump.json").read_text(encoding="utf-8"))
    recs = [r for r in d["results"] if r.get("ok")]
    qids = []
    for r in d["results"]:
        if r["qid"] not in qids:
            qids.append(r["qid"])

    br_path = DIR / "_branches.json"
    br = {}
    if br_path.exists():
        for q in json.loads(br_path.read_text(encoding="utf-8"))["questions"]:
            for row in q["results"]:
                br.setdefault((q["qid"], row["arm"]), []).append(row)

    by = {}
    for r in recs:
        by.setdefault((r["qid"], r["arm"]), []).append(r)

    L = ["# 2차 관측 — 검색이 무엇을 물어왔나 (2026-08-04)", "",
         f"봇 {d['bot']['id']} · 모델 {d['bot']['model']} · filter `{d['metadata_filter']}` · "
         f"top_k {d['rag_top_k']} · temp {d['rag_temperature']} · M2 어휘목록 {d['m2_mode']}", "",
         f"페르소나 system_instruction sha `{d['persona_sp_sha256']}` "
         f"(= bot.system_prompt + _FOLLOWUPS_INSTRUCTION) · 중립 sha `{d['neutral_sp_sha256']}`", "",
         "`p.21` = 2026 정본 편성 비교표. 선행 세션이 R-219 실패의 직접 원인으로 지목한 청크다.",
         "페르소나 팔은 청크 보고를 누락하므로 **검색 판정은 중립 팔로 한다**(AGENTS.md §3-3).", "",
         "## 표 A — 팔별 집계", "",
         "| 팔 | 프롬프트 | 청크0 보고 | 평균 청크 | **p.21 회수** | 평균 인용 | 평균 길이 |",
         "|---|---|---|---|---|---|---|"]

    for arm in list(PERSONA) + list(NEUTRAL):
        rs = [r for r in recs if r["arm"] == arm]
        if not rs:
            continue
        z = sum(1 for r in rs if r["grounding"]["n_chunks"] == 0)
        nch = sum(r["grounding"]["n_chunks"] for r in rs) / len(rs)
        k = sum(1 for r in rs if has_key_page(r))
        cit = sum(r.get("n_citations", 0) for r in rs) / len(rs)
        ln = sum(len(r.get("answer") or "") for r in rs) / len(rs)
        L.append(f"| {arm} | {'페르소나' if arm in PERSONA else '중립'} | {z}/{len(rs)} | "
                 f"{nch:.1f} | **{k}/{len(rs)}** | {cit:.1f} | {ln:.0f}자 |")

    L += ["", "## 표 B — 문항별 p.21 회수 (중립 팔, 반복 2회)", "",
          "| 문항 | 분기축 | NP (원질문) | NM1 (어휘확장) | NM2 (LLM확장) | M1 확장? |",
          "|---|---|---|---|---|---|"]

    q_axis = {r["qid"]: r["branch_axis"] for r in d["results"]}
    for qid in qids:
        cells = []
        for arm in NEUTRAL:
            rs = sorted(by.get((qid, arm), []), key=lambda r: r["rep"])
            cells.append("".join("Y" if has_key_page(r) else "·" for r in rs) or "—")
        m1 = by.get((qid, "M1"), [])
        exp = "O" if (m1 and m1[0].get("expanded")) else "X"
        L.append(f"| **{qid}** | {q_axis.get(qid,'')} | {cells[0]} | {cells[1]} | {cells[2]} | {exp} |")

    L += ["", "`Y` 회수 · `·` 미회수 (반복 2회를 나란히)", ""]

    if br:
        L += ["## 표 C — 분기 수 · 미근거 조건 (codex 의미판정)", "",
              "| 문항 | P 분기 | M1 분기 | M2 분기 | P 미근거 | M1 미근거 | M2 미근거 |",
              "|---|---|---|---|---|---|---|"]
        tot = {a: [0.0, 0, 0] for a in PERSONA}
        for qid in qids:
            cell = {}
            for arm in PERSONA:
                rows = br.get((qid, arm), [])
                nb = [x["n_branches"] for x in rows]
                brs = [b for x in rows for b in (x.get("branches") or [])]
                ung = [b for b in brs if b.get("grounded") is False]
                cell[arm] = (nb, len(ung))
                tot[arm][0] += sum(nb) / max(len(nb), 1)
                tot[arm][1] += len(brs)
                tot[arm][2] += len(ung)
            L.append(f"| **{qid}** | " + " | ".join(str(cell[a][0]) for a in PERSONA) + " | "
                     + " | ".join(str(cell[a][1]) for a in PERSONA) + " |")
        n = len(qids)
        L.append("| **평균/합계** | " + " | ".join(f"{tot[a][0]/n:.1f}" for a in PERSONA) + " | "
                 + " | ".join(f"{tot[a][2]}/{tot[a][1]} ({tot[a][2]/max(tot[a][1],1):.0%})"
                              for a in PERSONA) + " |")
        L += ["", "분기 수는 반복 2회를 `[r1, r2]` 로 나란히 적었다. "
              "codex 판정은 실행 간 변동이 있으니 소수점이 아니라 방향만 읽는다.", ""]
    else:
        L += ["## 표 C — 분기 수 · 미근거 조건", "", "_branches.json 없음 — `_branches2.py` 먼저 실행", ""]

    L += ["## 표 D — 확장 쿼리 원문", "", "| 문항 | M1 | M2 |", "|---|---|---|"]
    for qid in qids:
        m1 = (by.get((qid, "M1")) or [{}])[0]
        m2 = (by.get((qid, "M2")) or [{}])[0]
        L.append(f"| **{qid}** | {' '.join(m1.get('exp_terms') or []) or '(확장 없음)'} "
                 f"→ {len(m1.get('exp_articles') or [])}조문 | "
                 f"{' '.join(m2.get('exp_terms') or []) or '(확장 없음)'} "
                 f"→ {len(m2.get('exp_articles') or [])}조문 |")

    errs = [r for r in d["results"] if not r.get("ok")]
    bad_sp = [r for r in recs if r["arm"] in PERSONA and r.get("sp_sha256") != d["persona_sp_sha256"]]
    L += ["", "## 실행 위생", "",
          f"- 호출 {d['count']}건 · 오류 {len(errs)}건",
          f"- 페르소나 팔 프롬프트 해시 불일치 {len(bad_sp)}건 (0 이어야 운영과 동일 조건)",
          f"- 팔 사이에 바뀐 것: 사용자 메시지뿐. 프롬프트·필터·모델·top_k·temperature 고정", ""]

    (DIR / "REPORT2.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n→ {DIR/'REPORT2.md'}")


if __name__ == "__main__":
    main()
