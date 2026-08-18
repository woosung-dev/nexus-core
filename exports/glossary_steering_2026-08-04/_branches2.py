# 분기 추출 + 미근거 조건 판정 — 선행 _branches.py 의 팔 이름만 바꾼 복사본.
#
# INSTRUCTION 은 한 글자도 바꾸지 않는다. 선행 세션(봇7 A=2.5/B=2.4, 미근거 13%/16%)과
# 같은 자로 재야 비교가 성립한다.
#
# 바꾼 것 셋:
#   ① 채점 대상 팔  A,B → P,M1,M2
#   ② 판정 근거 corpus  R → 중립 3팔(NP·NM1·NM2) 합집합
#      팔마다 검색이 다르므로 팔별 corpus 가 더 정확하지만, 그러면 분기 '수'를 팔 사이에
#      일관되게 셀 수 없다(호출이 갈리면 세는 기준이 흔들린다). 합집합은 확장 팔에
#      불리한(= 보수적인) 선택이다 — P 가 못 본 근거까지 P 에게 인정해 준다.
#   ③ CORPUS_CHARS 12000 → 24000. 팔이 3배라 12000 이면 뒤쪽 청크가 잘려
#      M2 만 물어온 청크가 근거에서 빠진다.
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

ANSWER_ARMS = ("P", "M1", "M2")
CHUNK_ARMS = ("NP", "NM1", "NM2")

# ↓ 선행 _branches.py 와 바이트 단위로 동일. 수정 금지.
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


def codex_one(payload, expect_keys, tries=3):
    """codex 1회. 반환 (arm, rep) 집합이 입력과 다르면 재시도한다 —
    INSTRUCTION 예시가 arm:"A" 라 팔 이름을 흘릴 수 있어 확인한다."""
    last = RuntimeError("codex 호출 실패")
    for attempt in range(tries):
        p = subprocess.run(
            ["codex", "exec", INSTRUCTION, "-s", "read-only",
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


def main(dump_name, out_name):
    data = json.loads((DIR / dump_name).read_text(encoding="utf-8"))
    recs = data["results"]
    qids = []
    for r in recs:
        if r["qid"] not in qids:
            qids.append(r["qid"])

    out_path = DIR / out_name
    done = {}
    if out_path.exists():
        done = {r["qid"]: r for r in json.loads(out_path.read_text(encoding="utf-8"))["questions"]}
        print(f"이전 판정 {len(done)}건 재사용", flush=True)

    results = []
    for qid in qids:
        if qid in done:
            results.append(done[qid])
            continue

        # 중립 3팔 청크 합집합 = 판정 근거. 쪽수 순으로 정렬해 잘림을 결정론으로 만든다.
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
        corpus = "\n\n".join(t for _, t in chunks)[:CORPUS_CHARS]

        answers = [{"arm": r["arm"], "rep": r["rep"], "answer": r["answer"]}
                   for r in recs if r["qid"] == qid and r["arm"] in ANSWER_ARMS]
        question = next(r["orig_q"] for r in recs if r["qid"] == qid)
        expect = {(a["arm"], a["rep"]) for a in answers}

        print(f"  codex 판정 {qid} (답변 {len(answers)} · 청크 {len(chunks)} · {len(corpus)}자)…",
              flush=True)
        res = codex_one({"qid": qid, "question": question, "chunks": corpus, "answers": answers},
                        expect)
        res["qid"] = qid
        results.append(res)
        out_path.write_text(json.dumps({"source": dump_name, "questions": results},
                                       ensure_ascii=False, indent=1), encoding="utf-8")

    out_path.write_text(json.dumps({"source": dump_name, "questions": results},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    def arm_stats(r, arm):
        rows = [x for x in r["results"] if x["arm"] == arm]
        n_br = [x["n_branches"] for x in rows]
        brs = [br for x in rows for br in (x.get("branches") or [])]
        ung = [br["condition"] for br in brs if br.get("grounded") is False]
        return n_br, len(brs), ung

    hdr = "".join(f"{a} 분기".ljust(11) for a in ANSWER_ARMS)
    hdr += "".join(f"{a} 미근거".ljust(10) for a in ANSWER_ARMS)
    print(f"\n{'문항':<8}{hdr}")
    print("-" * (8 + 21 * len(ANSWER_ARMS)))
    tot = {a: [0.0, 0, 0] for a in ANSWER_ARMS}        # [분기합, 조건수, 미근거수]
    for r in results:
        cells = {}
        for arm in ANSWER_ARMS:
            n_br, n_cond, ung = arm_stats(r, arm)
            cells[arm] = (n_br, ung)
            tot[arm][0] += sum(n_br) / max(len(n_br), 1)
            tot[arm][1] += n_cond
            tot[arm][2] += len(ung)
        line = f"{r['qid']:<8}" + "".join(str(cells[a][0]).ljust(11) for a in ANSWER_ARMS)
        line += "".join(str(len(cells[a][1])).ljust(10) for a in ANSWER_ARMS)
        print(line)
    n = len(results)
    print("-" * (8 + 21 * len(ANSWER_ARMS)))
    print("평균 분기    " + "  ".join(f"{a}={tot[a][0]/n:.1f}" for a in ANSWER_ARMS))
    print("조건 총수    " + "  ".join(f"{a}={tot[a][1]}" for a in ANSWER_ARMS))
    print("미근거 조건  " + "  ".join(
        f"{a}={tot[a][2]}({tot[a][2]/max(tot[a][1],1):.0%})" for a in ANSWER_ARMS))
    print(f"→ {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="_dump.json")
    ap.add_argument("--out", default="_branches.json")
    a = ap.parse_args()
    main(a.dump, a.out)
