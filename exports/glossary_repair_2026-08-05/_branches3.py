# 분기 판정 2단 — ①분기 수·미근거 (선행과 같은 자) ②정답 분기 적중 (신규).
#
# 선행 `_branches2.py` 의 복사본. **1단 INSTRUCTION 은 한 글자도 바꾸지 않았다** —
# 선행 세션(P 1.4 · M1 1.6 · M2 1.6, 미근거 0%)과 같은 자로 재야 비교가 성립한다.
#
# 바꾼 것:
#   ① 팔 목록 파라미터화 (이번은 답변 P·M1, 청크 NP·NM1)
#   ② **2단 추가** — 세어 놓은 분기가 `expected_branches` 를 덮었는지 별도 codex 호출로 판정.
#      지금까지는 분기 '수'만 셌고 '맞는 분기'인지는 안 쟀다. R-219 처럼 틀린 한 분기도 1로 센다.
#      두 지표는 절대 합치지 않는다. 따로 보고한다.
#
# 2단을 문자열 매칭이 아니라 codex 로 하는 이유: 같은 구분을 다른 어휘로 쓴다
# (AGENTS.md §5 — 정규식으로 답변 구조를 세지 마라).
#
# 생성 모델(gemini)과 판정 모델(codex)을 분리한다 — 자기 답을 자기가 채점하지 않는다.
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
TIMEOUT = 900
REASONING = "medium"
CORPUS_CHARS = 24000

ANSWER_ARMS = ("P", "M1")     # --arms 로 덮어쓴다
CHUNK_ARMS = ("NP", "NM1")    # --chunk-arms 로 덮어쓴다

# ↓ 선행 _branches.py · _branches2.py 와 바이트 단위로 동일. 수정 금지.
INSTRUCTION = (
    "너는 종교(세계평화통일가정연합) 축복 규정 답변의 '조건 분기'를 판정하는 심사관이다.\n"
    "<stdin>으로 JSON 객체 하나가 들어온다. 필드:\n"
    "  qid, question — 사용자 질문\n"
    "  chunks        — 이 질문으로 실제 검색된 규정 문서 청크 원문 (판정의 유일한 근거)\n"
    "  answers       — [{arm, rep, answer}] 채점 대상 답변들\n\n"
    "각 answer 에 대해 '분기'를 세라.\n"
    "분기 = 서로 다른 케이스에 서로 다른 결론·절차를 제시한 단위다.\n"
    "  · 서식은 무관하다 — 「~인 경우:」, 「### 1. 2세가정 편성」, 표, 문단 어느 것이든 분기다.\n"
    "  · '참고 사항', '유의점', '상담 권유', '출처' 같은 부가 항목은 분기가 아니다.\n"
    "  · 같은 케이스를 여러 항목으로 쪼갠 것(자격/교육/절차)은 1분기다.\n"
    "  · 케이스 구분 없이 하나의 결론만 말했으면 0분기다.\n\n"
    "모든 답변(arm 무관)에 대해 각 분기 조건이 chunks 에 실재하는지도 판정하라.\n"
    "  grounded=true  — 그 조건 구분이 chunks 원문에 실제로 있다\n"
    "  grounded=false — chunks 에 없는 구분을 답변이 만들어냈다 (과분기)\n"
    "  evidence       — true 일 때 근거가 된 chunks 의 짧은 인용(30자 내외), false 면 null\n"
    "  표현이 달라도 같은 구분이면 true 다. 어휘가 겹쳐도 다른 구분이면 false 다.\n\n"
    "확신이 어려우면 grounded 를 false 로 하지 말고 note 에 명시하라(과잉확신 금지).\n"
    "설명 없이 오직 JSON 객체 하나만 출력하라. 형식:\n"
    '{"qid": "...", "results": [{"arm": "A", "rep": 1, "n_branches": 2, '
    '"branches": [{"condition": "...", "grounded": true, "evidence": "..."}], "note": "..."}]}'
)

# 2단 — 신규. 정답 라벨 대조 전용이고 1단과 절대 섞지 않는다.
MATCH_INSTRUCTION = (
    "너는 종교(세계평화통일가정연합) 축복 규정 답변이 '정해진 정답 케이스'를 덮었는지 판정하는 "
    "심사관이다. 분기 개수를 세는 것이 아니다 — 사람이 규정집 조문으로 미리 정해 둔 케이스를 "
    "답변이 다뤘는지만 본다.\n"
    "<stdin>으로 JSON 객체 하나가 들어온다. 필드:\n"
    "  qid, question    — 사용자 질문\n"
    "  expected_cases   — [{case, must[], articles[]}] 반드시 구분되어야 하는 케이스와 그 필수 요소\n"
    "  must_not         — [문자열] 하면 안 되는 안내\n"
    "  answers          — [{arm, rep, answer}] 채점 대상 답변들\n\n"
    "각 answer 에 대해 판정하라.\n"
    "  covered   — expected_cases 중 답변이 실제로 다룬 case 이름들. 표현이 달라도 같은 케이스면 "
    "덮은 것으로 본다(예: '2세가정 편성' = '축복자녀가정 편성').\n"
    "  missing   — 다루지 않은 case 이름들\n"
    "  partial   — case 는 언급했으나 must 요소를 빠뜨린 것: [{case, missing_must[]}]\n"
    "  violated  — 답변이 어긴 must_not 문자열들 (없으면 빈 배열)\n"
    "  spurious  — expected_cases 에 없는 케이스를 만들어내 갈라놓은 것 (없으면 빈 배열)\n\n"
    "expected_cases 가 빈 배열이면 covered·missing·partial 을 모두 빈 배열로 두고 "
    "note 에 '정답 라벨 없음'이라고만 쓴다.\n"
    "확신이 어려우면 missing 으로 몰지 말고 note 에 명시하라(과잉확신 금지).\n"
    "설명 없이 오직 JSON 객체 하나만 출력하라. 형식:\n"
    '{"qid": "...", "results": [{"arm": "A", "rep": 1, "covered": ["..."], "missing": ["..."], '
    '"partial": [{"case": "...", "missing_must": ["..."]}], "violated": [], "spurious": [], '
    '"note": "..."}]}'
)


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def extract_json_object(text):
    t = re.sub(r"```$", "", re.sub(r"^```(?:json)?", "", text.strip()).strip()).strip()
    dec = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(t[i:])
        except ValueError:
            continue
        if isinstance(obj, dict) and "results" in obj:
            return obj
    raise ValueError(f"JSON 객체 못 찾음: {t[:200]!r}")


def codex_one(instruction, payload, expect_keys, tries=3):
    """codex 1회. 반환 (arm, rep) 집합이 입력과 다르면 재시도한다 —
    INSTRUCTION 예시가 arm:"A" 라 팔 이름을 흘릴 수 있어 확인한다."""
    last = RuntimeError("codex 호출 실패")
    for attempt in range(tries):
        p = subprocess.run(
            ["codex", "exec", instruction, "-s", "read-only",
             "-c", f'model_reasoning_effort="{REASONING}"'],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, cwd=str(ROOT), timeout=TIMEOUT)
        if p.returncode != 0:
            last = RuntimeError(f"codex exit {p.returncode}: {p.stderr[-300:]}")
            continue
        try:
            obj = extract_json_object(p.stdout)
        except ValueError as e:
            last = e
            print(f"    (파싱 실패, 재시도 {attempt+1}/{tries})", flush=True)
            continue
        got = {(r.get("arm"), r.get("rep")) for r in obj["results"]}
        if got != expect_keys:
            last = ValueError(f"팔·반복 불일치: {sorted(got)} != {sorted(expect_keys)}")
            print(f"    (팔 라벨 불일치, 재시도 {attempt+1}/{tries})", flush=True)
            continue
        return obj
    raise last


def build_corpus(recs, qid):
    """중립 팔 청크 합집합. 쪽수 순 정렬해 잘림을 결정론으로 만든다."""
    chunks, seen = [], set()
    for r in recs:
        if r["qid"] != qid or r["arm"] not in CHUNK_ARMS:
            continue
        for c in r["grounding"]["chunks"]:
            k = (nfc(c.get("title")), c.get("page_number"), nfc(c.get("text"))[:60])
            if k in seen:
                continue
            seen.add(k)
            chunks.append((c.get("page_number") or 0,
                           f"[{c.get('title')} p.{c.get('page_number')}]\n{c.get('text')}"))
    chunks.sort(key=lambda x: x[0])
    return len(chunks), "\n\n".join(t for _, t in chunks)[:CORPUS_CHARS]


def report_branches(results):
    def arm_stats(r, arm):
        rows = [x for x in r["results"] if x["arm"] == arm]
        n_br = [x["n_branches"] for x in rows]
        brs = [br for x in rows for br in (x.get("branches") or [])]
        ung = [br["condition"] for br in brs if br.get("grounded") is False]
        return n_br, len(brs), ung

    print("\n" + "=" * 78)
    print("표 1. 분기 수 · 미근거 조건 (선행과 같은 자)")
    print("=" * 78)
    hdr = "".join(f"{a} 분기".ljust(22) for a in ANSWER_ARMS)
    hdr += "".join(f"{a} 미근거".ljust(10) for a in ANSWER_ARMS)
    print(f"{'문항':<9}{hdr}")
    print("-" * (9 + 32 * len(ANSWER_ARMS)))
    tot = {a: [0.0, 0, 0] for a in ANSWER_ARMS}
    for r in results:
        cells = {}
        for arm in ANSWER_ARMS:
            n_br, n_cond, ung = arm_stats(r, arm)
            cells[arm] = (n_br, ung)
            tot[arm][0] += sum(n_br) / max(len(n_br), 1)
            tot[arm][1] += n_cond
            tot[arm][2] += len(ung)
        line = f"{r['qid']:<9}" + "".join(str(cells[a][0]).ljust(22) for a in ANSWER_ARMS)
        line += "".join(str(len(cells[a][1])).ljust(10) for a in ANSWER_ARMS)
        print(line)
    n = len(results)
    print("-" * (9 + 32 * len(ANSWER_ARMS)))
    print("평균 분기    " + "  ".join(f"{a}={tot[a][0]/n:.1f}" for a in ANSWER_ARMS))
    print("조건 총수    " + "  ".join(f"{a}={tot[a][1]}" for a in ANSWER_ARMS))
    print("미근거 조건  " + "  ".join(
        f"{a}={tot[a][2]}({tot[a][2]/max(tot[a][1],1):.0%})" for a in ANSWER_ARMS))

    # 기준선 안정성 — 같은 조건 5회가 갈리는가
    print("\n" + "=" * 78)
    print("표 2. 반복 간 일관성 (핸드오프 §6 — 5회 중 4회 이상 같아야 자가 잡힌 것)")
    print("=" * 78)
    print(f"{'문항':<9}{'팔':<5}{'분기 수 5회':<22}{'최빈값 비율':<14}판정")
    print("-" * 78)
    for r in results:
        for arm in ANSWER_ARMS:
            n_br, _, _ = arm_stats(r, arm)
            if not n_br:
                continue
            top = max(set(n_br), key=n_br.count)
            ratio = n_br.count(top) / len(n_br)
            verdict = "일관" if ratio >= 0.8 else "갈림 ⚠"
            print(f"{r['qid']:<9}{arm:<5}{str(n_br):<22}{top}:{n_br.count(top)}/{len(n_br)}"
                  f"{'':<7}{verdict}")


def report_match(matches, labels):
    print("\n" + "=" * 78)
    print("표 3. 정답 분기 적중 (신규 — 분기 '수'가 아니라 '맞는 분기'인가)")
    print("=" * 78)
    print(f"{'문항':<9}{'팔':<5}{'적중':<10}{'누락':<10}{'부분':<8}{'must_not 위반':<14}{'과잉'}")
    print("-" * 78)
    agg = {a: [0, 0, 0, 0, 0] for a in ANSWER_ARMS}   # [적중, 기대총, 위반, 부분, 과잉]
    for m in matches:
        lab = labels[m["qid"]]
        if lab["expected"] != "labeled":
            print(f"{m['qid']:<9}{'—':<5}(정답 라벨 없음 — 채점 제외: {lab['note'][:40]})")
            continue
        n_exp = len(lab["expected_branches"])
        for arm in ANSWER_ARMS:
            rows = [x for x in m["results"] if x["arm"] == arm]
            if not rows:
                continue
            hit = sum(len(x.get("covered") or []) for x in rows)
            miss = sum(len(x.get("missing") or []) for x in rows)
            part = sum(len(x.get("partial") or []) for x in rows)
            vio = sum(len(x.get("violated") or []) for x in rows)
            spur = sum(len(x.get("spurious") or []) for x in rows)
            tot_exp = n_exp * len(rows)
            agg[arm][0] += hit
            agg[arm][1] += tot_exp
            agg[arm][2] += vio
            agg[arm][3] += part
            agg[arm][4] += spur
            print(f"{m['qid']:<9}{arm:<5}{f'{hit}/{tot_exp}':<10}{miss:<10}{part:<8}"
                  f"{vio:<14}{spur}")
    print("-" * 78)
    for arm in ANSWER_ARMS:
        h, t, v, p, s = agg[arm]
        print(f"{arm}  정답 분기 적중 {h}/{t} ({h/max(t,1):.0%}) · "
              f"must_not 위반 {v} · 부분충족 {p} · 과잉분기 {s}")


def main(dump_name, qpath, out1, out2):
    data = json.loads((DIR / dump_name).read_text(encoding="utf-8"))
    recs = data["results"]
    labels = {it["qid"]: it
              for it in json.loads(Path(qpath).read_text(encoding="utf-8"))["items"]}

    qids = []
    for r in recs:
        if r["qid"] not in qids:
            qids.append(r["qid"])

    p1, p2 = DIR / out1, DIR / out2
    done1 = {r["qid"]: r for r in json.loads(p1.read_text(encoding="utf-8"))["questions"]} \
        if p1.exists() else {}
    done2 = {r["qid"]: r for r in json.loads(p2.read_text(encoding="utf-8"))["questions"]} \
        if p2.exists() else {}
    if done1 or done2:
        print(f"이전 판정 재사용 — 1단 {len(done1)}건 · 2단 {len(done2)}건", flush=True)

    # 일일 한도로 중간에 끊긴 문항은 판정하지 않는다 — 팔마다 반복 수가 다르면
    # 분기 수 평균과 적중률이 팔 사이에 비교 불가능해진다. 건너뛴 것은 명시한다.
    reps_seen = {}
    for qid in qids:
        cnt = {a: sum(1 for r in recs
                      if r["qid"] == qid and r["arm"] == a and r.get("ok"))
               for a in ANSWER_ARMS}
        reps_seen[qid] = cnt
    full = max((min(c.values()) for c in reps_seen.values()), default=0)
    skipped = [q for q in qids if min(reps_seen[q].values()) != full
               or len(set(reps_seen[q].values())) != 1]
    if skipped:
        print(f"⚠ 반복 수가 {full}회로 안 채워져 판정에서 제외: "
              + " · ".join(f"{q}{reps_seen[q]}" for q in skipped), flush=True)
    qids = [q for q in qids if q not in skipped]
    print(f"판정 대상 {len(qids)}문항 × 팔 {list(ANSWER_ARMS)} × {full}회", flush=True)

    results, matches = [], []
    for qid in qids:
        answers = [{"arm": r["arm"], "rep": r["rep"], "answer": r["answer"]}
                   for r in recs if r["qid"] == qid and r["arm"] in ANSWER_ARMS and r.get("ok")]
        if not answers:
            continue
        question = next(r["orig_q"] for r in recs if r["qid"] == qid)
        expect = {(a["arm"], a["rep"]) for a in answers}
        lab = labels[qid]

        if qid in done1:
            results.append(done1[qid])
        else:
            n_chunks, corpus = build_corpus(recs, qid)
            print(f"  [1단] {qid} (답변 {len(answers)} · 청크 {n_chunks} · {len(corpus)}자)…",
                  flush=True)
            res = codex_one(INSTRUCTION,
                            {"qid": qid, "question": question, "chunks": corpus,
                             "answers": answers}, expect)
            res["qid"] = qid
            results.append(res)
            p1.write_text(json.dumps({"source": dump_name, "questions": results},
                                     ensure_ascii=False, indent=1), encoding="utf-8")

        if qid in done2:
            matches.append(done2[qid])
        else:
            print(f"  [2단] {qid} (정답 케이스 {len(lab['expected_branches'])})…", flush=True)
            res2 = codex_one(MATCH_INSTRUCTION,
                             {"qid": qid, "question": question,
                              "expected_cases": lab["expected_branches"],
                              "must_not": lab["must_not"], "answers": answers}, expect)
            res2["qid"] = qid
            matches.append(res2)
            p2.write_text(json.dumps({"source": dump_name, "questions": matches},
                                     ensure_ascii=False, indent=1), encoding="utf-8")

    p1.write_text(json.dumps({"source": dump_name, "questions": results},
                             ensure_ascii=False, indent=1), encoding="utf-8")
    p2.write_text(json.dumps({"source": dump_name, "questions": matches},
                             ensure_ascii=False, indent=1), encoding="utf-8")

    report_branches(results)
    report_match(matches, labels)
    print(f"\n→ {p1}\n→ {p2}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="_dump2.json")
    ap.add_argument("--questions", default=str(DIR / "_questions_pyeongseong.json"))
    ap.add_argument("--out1", default="_branches.json")
    ap.add_argument("--out2", default="_match.json")
    ap.add_argument("--arms", default=",".join(ANSWER_ARMS), help="채점 대상 팔")
    ap.add_argument("--chunk-arms", default=",".join(CHUNK_ARMS),
                    help="판정 근거 청크를 뽑을 팔 (중립 팔이어야 한다 — 페르소나는 보고를 억제한다)")
    a = ap.parse_args()
    ANSWER_ARMS = tuple(x.strip() for x in a.arms.split(",") if x.strip())
    CHUNK_ARMS = tuple(x.strip() for x in a.chunk_arms.split(",") if x.strip())
    main(a.dump, a.questions, a.out1, a.out2)
