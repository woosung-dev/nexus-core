# _dump_*.json → REPORT.md (관측표).
#
# 원칙: 자동 판정을 하지 않는다 (핸드오프 §8 "관측을 먼저 기록하고 판정은 그 뒤에").
# 이 스크립트가 계산하는 것은 셀 수 있는 것뿐이다 — 청크 수, 문서 제목, custom_metadata 유무,
# 반복 간 차이. 과분기 여부(조건이 청크에 실재하는가)는 사람이 기입하는 빈칸으로 남긴다.
# 토큰 겹침 비율은 읽는 순서를 정하기 위한 힌트일 뿐 판정값이 아니다.
import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

DIR = Path(__file__).parent

# "· 2세가 40일 정성기간 중인 경우:" 같은 분기 머리줄에서 조건 문구를 뽑는다.
# 리스트 마커·볼드·콜론 변형을 허용한다. A 팔이 다른 형식으로 분기해도 잡히게 넓게 둔다.
BRANCH_RE = re.compile(
    r"^[ \t]*(?:[·•\-\*]\s*)?(?:\*\*)?\s*([^\n]{2,80}?경우)\s*(?:\*\*)?\s*[::]",
    re.M)

# 겹침 힌트용 토큰: 2자 이상 한글/영숫자 덩어리.
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")
# 조건 문구 어디에나 나오는 기능어 — 겹침 계산에서 빼지 않으면 전부 높게 나온다.
STOP = {"경우", "해당", "이후", "이전", "그리고", "또는", "하는", "받은", "있는", "없는", "대한"}


def nfc(s):
    """RAG 파일명·본문에 NFD/NFC 가 섞여 있다. 비교 전에 정규화하지 않으면 거짓음성이 난다."""
    return unicodedata.normalize("NFC", s or "")


def branches(answer):
    """답변에서 분기 조건 문구 목록. 중복은 순서를 지키며 제거."""
    out, seen = [], set()
    for m in BRANCH_RE.finditer(answer or ""):
        c = re.sub(r"\s+", " ", m.group(1)).strip(" *·•-")
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def overlap_hint(condition, corpus):
    """조건 문구의 내용어가 R 청크 본문에 얼마나 나타나는가. 판정값 아님 — 읽는 순서용."""
    toks = [t for t in TOKEN_RE.findall(nfc(condition)) if t not in STOP]
    if not toks:
        return None, [], []
    c = nfc(corpus)
    hit = [t for t in toks if t in c]
    miss = [t for t in toks if t not in c]
    return len(hit) / len(toks), hit, miss


def load(tag):
    p = DIR / f"_dump_{tag}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_branches(name):
    """_branches.py(codex 의미판정) 산출물. 있으면 분기 수의 정본으로 쓴다.

    정규식 카운트는 서식에 걸려 양방향으로 틀린다(실측). 판정 결과가 있으면 그쪽을 쓰고,
    없으면 정규식 값을 '힌트'로만 표시한다."""
    p = DIR / name
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for q in data["questions"]:
        for r in q["results"]:
            out[(q["qid"], r["arm"], r["rep"])] = r
    return out


def by_key(data):
    """(qid, arm, rep) → record"""
    return {(r["qid"], r["arm"], r["rep"]): r for r in data["results"]}


def main(main_tag, probe_tag, out_name, branch_file):
    BR = load_branches(branch_file)
    main_d = load(main_tag)
    if not main_d:
        raise SystemExit(f"_dump_{main_tag}.json 없음")
    probe_d = load(probe_tag)

    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    qorder = [i["qid"] for i in items]
    qmeta = {i["qid"]: i for i in items}

    M = by_key(main_d)
    P = by_key(probe_d) if probe_d else {}
    arms = main_d["arms"]
    reps = main_d["reps"]
    L = []

    b = main_d["bot"]
    L += [f"# 조건부 분기 절제 실험 — 관측표 ({main_tag})", "",
          "> 자동 판정 없음. 아래는 관측치이고, 판정은 §7 표에 사람이 기입한다.", "",
          "## 실행 메타", "",
          "| 항목 | 값 |", "| --- | --- |",
          f"| 봇 | {b['id']} · {b['name']} |",
          f"| 모델 | `{b['model']}` ({b['model_source']}) |",
          f"| evidence_policy_mode | `{b['evidence_policy_mode']}` |",
          f"| system_prompt | {b['system_prompt_len']}자 · sha `{b['system_prompt_sha256']}` |",
          f"| top_k / temperature | {main_d['rag_top_k']} / {main_d['rag_temperature']} |",
          f"| 팔 / 반복 | {', '.join(arms)} / {reps}회 |",
          f"| history | {main_d['history']} (단일 턴) |",
          f"| store | `{main_d['store']}` |", ""]
    if probe_d:
        pb = probe_d["bot"]
        L += [f"체크 D 대조군: 봇 {pb['id']} · {pb['name']} · 모델 `{pb['model']}` ({pb['model_source']})", ""]

    errs = [r for r in main_d["results"] if not r.get("ok")]
    if errs:
        L += [f"⚠️ 오류 {len(errs)}건: " + ", ".join(f"{r['qid']}/{r['arm']}r{r['rep']}" for r in errs), ""]

    # ── 요약 ──────────────────────────────────────────────────────────
    if BR:
        def stats(arm):
            rows = [BR[k] for k in BR if k[1] == arm]
            nb = [r["n_branches"] for r in rows]
            conds = [c for r in rows for c in (r.get("branches") or [])]
            ung = [c for c in conds if c.get("grounded") is False]
            return (sum(nb) / max(len(nb), 1), len(conds), len(ung))
        a_avg, a_c, a_u = stats("A")
        b_avg, b_c, b_u = stats("B")
        L += ["---", "", "## 요약 (codex 의미판정 기준)", "",
              "| 지표 | A 기준선 | B 분기프롬프트 |", "| --- | --- | --- |",
              f"| 평균 분기 수 | {a_avg:.1f} | {b_avg:.1f} |",
              f"| 조건 총수 | {a_c} | {b_c} |",
              f"| **미근거 조건(과분기)** | {a_u} ({a_u/max(a_c,1):.0%}) | {b_u} ({b_u/max(b_c,1):.0%}) |",
              "",
              "분기 수는 서식이 아니라 의미로 세야 해서 codex 로 판정했다 "
              "(정규식은 「### 1. 2세가정 편성」 형식의 분기를 0으로 세는 등 양방향으로 틀렸다). "
              "판정 자체에 실행 간 변동이 있으므로 **소수점 차이는 읽지 말고 방향만 본다.**", ""]

    # ── 체크 A ─────────────────────────────────────────────────────────
    L += ["---", "", "## 체크 A — `custom_metadata` 회수 여부", ""]
    tot = present = 0
    keys = defaultdict(int)
    for r in main_d["results"]:
        for c in r["grounding"]["chunks"]:
            if "title" not in c:
                continue
            tot += 1
            cm = c.get("custom_metadata")
            if cm:
                present += 1
                for m in cm:
                    keys[m["key"]] += 1
    pct = f"{100*present/tot:.1f}%" if tot else "—"
    L += [f"관측 청크 **{tot}개** 중 `custom_metadata`가 채워진 것 **{present}개 ({pct})**", ""]
    if keys:
        L += ["| key | 등장 청크 수 |", "| --- | --- |"]
        L += [f"| `{k}` | {v} |" for k, v in sorted(keys.items())]
        L += ["", "→ 업로드 시 박은 메타데이터가 grounding 으로 회수된다. "
                  "**조건 메타데이터를 문서에 붙이면 조건 다양성 판정을 결정론으로 만들 수 있다.**", ""]
    else:
        L += ["→ 회수되지 않는다. 조건 판정은 제목·본문 파싱 폴백으로 가야 한다.", ""]

    # page_number / uri / confidence_scores 부수 관측
    pg = sum(1 for r in main_d["results"] for c in r["grounding"]["chunks"] if c.get("page_number") is not None)
    ur = sum(1 for r in main_d["results"] for c in r["grounding"]["chunks"] if c.get("uri"))
    sup = [s for r in main_d["results"] for s in r["grounding"]["supports"]]
    cs = sum(1 for s in sup if s["confidence_scores"])
    L += [f"부수 관측 — `page_number` {pg}/{tot} · `uri` {ur}/{tot} · "
          f"`confidence_scores` {cs}/{len(sup)} supports", ""]

    # ── 체크 C 재료: 팔별 청크 관측 ────────────────────────────────────
    L += ["---", "", "## 팔별 검색 관측 (체크 C 재료)", "",
          "| 문항 | " + " | ".join(f"{a} 청크" for a in arms) + " | R 고유문서 |",
          "| --- | " + " | ".join("---" for _ in arms) + " | --- |"]
    for qid in qorder:
        cells = []
        for a in arms:
            v = [M[(qid, a, rp)]["grounding"]["n_chunks"] for rp in range(1, reps + 1) if (qid, a, rp) in M]
            cells.append("/".join(str(x) for x in v) if v else "—")
        titles = {nfc(c.get("title")) for rp in range(1, reps + 1)
                  if (qid, "R", rp) in M for c in M[(qid, "R", rp)]["grounding"]["chunks"] if c.get("title")}
        L.append(f"| {qid} | " + " | ".join(cells) + f" | {len(titles)} |")
    L += ["", f"셀은 반복 {reps}회 값을 `/`로 이어 쓴 것이다.", ""]

    # ── 문항별 상세 ────────────────────────────────────────────────────
    L += ["---", "", "## 문항별 관측", ""]
    for qid in qorder:
        it = qmeta[qid]
        L += [f"### {qid} (gid {it['gid']}) · 분기축: {it['branch_axis']}", "",
              f"> {it['q']}", "",
              f"출처: `{it['source']}` · 위험 {it.get('risk')} · {it.get('note','')}", ""]

        # R 청크
        rchunks, seen = [], set()
        for rp in range(1, reps + 1):
            for c in M.get((qid, "R", rp), {}).get("grounding", {}).get("chunks", []):
                k = (nfc(c.get("title")), c.get("page_number"), nfc(c.get("text"))[:80])
                if k not in seen:
                    seen.add(k)
                    rchunks.append(c)
        L += [f"**R 검색 청크 ({len(rchunks)}개, 반복 합집합)**", ""]
        if not rchunks:
            L += ["_청크 없음 — 이 문항은 검색이 빈손이다._", ""]
        for c in rchunks:
            L += [f"- **{c.get('title')}** p.{c.get('page_number')} ({c.get('text_len')}자)",
                  f"  > {re.sub(chr(10)+'+', ' ', (c.get('text') or ''))[:400]}…"]
        L += [""]

        # A·B 답변과 분기
        for a in [x for x in arms if x != "R"]:
            for rp in range(1, reps + 1):
                r = M.get((qid, a, rp))
                if not r:
                    continue
                j = BR.get((qid, a, rp)) if BR else None
                if j:
                    conds = j.get("branches") or []
                    L += [f"**{a} rep{rp}** — 분기 **{j['n_branches']}개**(codex 판정) · "
                          f"인용 {r.get('n_citations',0)} · 청크 {r['grounding']['n_chunks']} · "
                          f"{len(r.get('answer') or '')}자", ""]
                    for c in conds:
                        gd = c.get("grounded")
                        mark = "✅ 근거있음" if gd is True else ("❌ **미근거**" if gd is False else "— 판정없음")
                        ev = f" · 근거: “{c.get('evidence')}”" if c.get("evidence") else ""
                        L += [f"  - `{c.get('condition')}` {mark}{ev}"]
                    if j.get("note"):
                        L += [f"  - _판정 메모: {j['note']}_"]
                    L += [""]
                else:
                    bl = branches(r.get("answer"))
                    L += [f"**{a} rep{rp}** — 분기 {len(bl)}개(정규식 힌트) · 인용 {r.get('n_citations',0)} · "
                          f"청크 {r['grounding']['n_chunks']} · {len(r.get('answer') or '')}자", ""]
                    if bl:
                        L += ["  " + " / ".join(f"`{x}`" for x in bl), ""]
                L += ["<details><summary>답변 펼치기</summary>", "",
                      (r.get("answer") or "_(빈 응답)_"), "", "</details>", ""]

        # 과분기 요약 — codex 판정이 있으면 그것을, 없으면 어휘겹침 힌트를 쓴다
        if BR:
            rows = []
            for a in [x for x in arms if x != "R"]:
                for rp in range(1, reps + 1):
                    jj = BR.get((qid, a, rp))
                    for c in (jj or {}).get("branches", []):
                        if c.get("grounded") is False:
                            rows.append((a, rp, c.get("condition")))
            if rows:
                L += ["**미근거 조건 (과분기)**", "", "| 팔 | rep | 조건 |", "| --- | --- | --- |"]
                L += [f"| {a} | {rp} | {c} |" for a, rp, c in rows] + [""]
            else:
                L += ["**미근거 조건 (과분기)** — 없음", ""]
        else:
            corpus = " ".join((c.get("text") or "") for c in rchunks)
            bconds, seenc = [], set()
            for rp in range(1, reps + 1):
                for c in branches(M.get((qid, "B", rp), {}).get("answer")):
                    if c not in seenc:
                        seenc.add(c)
                        bconds.append(c)
            L += ["**과분기 판정** — B의 분기 조건이 R 청크에 실재하는가 (사람이 기입)", "",
                  "| B 분기 조건 | 청크 어휘 겹침(힌트) | 미출현 어휘 | 실재? |",
                  "| --- | --- | --- | --- |"]
            if not bconds:
                L += ["| _(B가 분기 형식으로 답하지 않음)_ | — | — | — |"]
            for c in bconds:
                ratio, _hit, miss = overlap_hint(c, corpus)
                L.append(f"| {c} | {'—' if ratio is None else f'{ratio:.0%}'} | "
                         f"{', '.join(miss[:6]) or '—'} | ☐ Y ☐ N |")
            L += [""]

    # ── 비결정성 ───────────────────────────────────────────────────────
    L += ["---", "", "## 반복 간 흔들림 (비결정성)", "",
          "| 문항 | " + " | ".join(f"{a} 분기수" for a in arms if a != "R") + " | 흔들림 |",
          "| --- | " + " | ".join("---" for a in arms if a != "R") + " | --- |"]
    for qid in qorder:
        cells, wob = [], False
        for a in [x for x in arms if x != "R"]:
            if BR:
                v = [BR[(qid, a, rp)]["n_branches"] for rp in range(1, reps + 1) if (qid, a, rp) in BR]
            else:
                v = [len(branches(M[(qid, a, rp)].get("answer"))) for rp in range(1, reps + 1) if (qid, a, rp) in M]
            cells.append("/".join(map(str, v)) if v else "—")
            wob |= len(set(v)) > 1
        L.append(f"| {qid} | " + " | ".join(cells) + f" | {'⚠️ 있음' if wob else '없음'} |")
    L += ["", "흔들리는 문항은 1회 결과로 판정하지 않는다 (PR #51 의 교훈).", ""]

    # ── 체크 D ────────────────────────────────────────────────────────
    L += ["---", "", "## 체크 D — 분기 근거가 Store 에 있는가", ""]
    if not probe_d:
        L += ["_대조 봇 프로브 미실행._", ""]
    else:
        L += [f"| 문항 | 봇{b['id']} R 청크 | 봇{probe_d['bot']['id']} R 청크 | 봇{probe_d['bot']['id']} 문서 |",
              "| --- | --- | --- | --- |"]
        for qid in qorder:
            m = [M[(qid, "R", rp)]["grounding"]["n_chunks"] for rp in range(1, reps + 1) if (qid, "R", rp) in M]
            pv, pt = [], set()
            for rp in range(1, probe_d["reps"] + 1):
                if (qid, "R", rp) in P:
                    g = P[(qid, "R", rp)]["grounding"]
                    pv.append(g["n_chunks"])
                    pt |= {nfc(c.get("title")) for c in g["chunks"] if c.get("title")}
            L.append(f"| {qid} | {'/'.join(map(str,m)) or '—'} | {'/'.join(map(str,pv)) or '—'} | "
                     f"{', '.join(sorted(pt)) or '—'} |")
        L += ["", "양쪽 모두 0 → 문서 결손. 대조 봇만 있음 → 운영 봇 문서집합 결손.", ""]

    # ── 판정란 ────────────────────────────────────────────────────────
    L += ["---", "", "## 판정 (핸드오프 §7 — 관측을 다 읽은 뒤 기입)", "",
          "| 관측 | 해당? | 결론 | 다음 투자 |", "| --- | --- | --- | --- |",
          "| B에서 청크에 없는 조건이 1건이라도 등장 | ☐ | 프롬프트 단독 불가 · 과분기 실증 | 카드 코퍼스 1순위 |",
          "| B 분기수 > A 이고 모든 조건이 청크에 실재 | ☐ | 재료 충분 → 생성 문제 | 카드 축소 · `<branches>` 구조화 |",
          "| B ≈ A | ☐ | 재료 문제 | 카드 코퍼스 1순위 |",
          "| 양쪽 봇 모두 근거 없음 | ☐ | 문서 결손 | 문서 확보가 선행 |",
          "| 운영 봇만 빈손 | ☐ | 운영 봇 문서집합 결손 | 2026 정본 적재 선행 |", "",
          "**결론이 나기 전까지 카드 코퍼스 작성을 시작하지 않는다.**", "",
          "### 한계", "",
          "- R 은 *검색 결과*가 아니라 **모델이 보고한 청크**다. 중립 프롬프트에서 보고율이 높아 "
          "현재 가용한 최선의 근사지만, 검색이 실제로 무엇을 반환했는지의 직접 관측은 이 스택에서 불가능하다.",
          "- 문항의 전제(\"이 질문은 실제로 케이스별로 답이 갈리는가\")는 **도메인 확인 전**이다. "
          "레드팀이 분기 오류를 지적한 건에서 뽑았을 뿐이다.",
          f"- 운영 봇은 `history_window={b['history_window']}` 이지만 이 실험은 단일 턴이다.", ""]

    (DIR / out_name).write_text("\n".join(L), encoding="utf-8")
    print(f"→ {DIR / out_name}  ({len(L)}줄)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="bot7", help="본실행 덤프 태그")
    ap.add_argument("--probe-tag", default="bot11", help="체크 D 대조 덤프 태그")
    ap.add_argument("--out", default="REPORT.md")
    ap.add_argument("--branches", default="_branches_bot7_v2.json",
                    help="codex 의미판정 결과 (없으면 정규식 힌트만)")
    a = ap.parse_args()
    main(a.tag, a.probe_tag, a.out, a.branches)
