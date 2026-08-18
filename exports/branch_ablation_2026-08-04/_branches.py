# 분기 추출 + 과분기 판정 — codex CLI 로 의미 기반 판정한다.
#
# 왜 정규식이 아닌가: 모델이 분기를 "· ~인 경우:" 로도, "### 1. 2세가정 편성" 으로도,
# 표로도 쓴다. 정규식은 양방향으로 틀린다(실측 — R-88 에서 `경우:` 패턴은 2분기를 0으로,
# 넓힌 패턴은 참고 헤더까지 3으로 셌다). 세는 대상이 서식이 아니라 의미라서 서식 매칭이
# 도구로 부적합하다.
#
# 생성 모델(gemini)과 판정 모델(codex)을 분리한다 — 자기 답을 자기가 채점하지 않는다.
# (exports/regression/_l3.py 와 같은 방식)
#
# 판정하는 것 둘:
#   ① 분기 수      — A·B 답변이 케이스를 몇 개로 나눴는가
#   ② 과분기 여부  — B 의 각 분기 조건이 R 검색 청크에 실재하는가 (근거 밖 조건 생성률)
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
CORPUS_CHARS = 12000

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
    """codex 출력에서 JSON 객체를 꺼낸다.

    앞뒤에 로그·설명이 붙어 나오는 경우가 있어 첫 `{` 부터 raw_decode 로 훑는다.
    (실측 1회 — 순수 JSON 이 아닌 응답이 섞여 나와 naive 슬라이싱이 깨졌다.)
    """
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


def codex_one(payload, tries=3):
    last = RuntimeError('codex 호출 실패')
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
            return extract_json_object(p.stdout)
        except ValueError as e:
            last = e
            print(f"    (파싱 실패, 재시도 {attempt+1}/{tries})", flush=True)
    raise last


def main(tag, out_name):
    data = json.loads((DIR / f"_dump_{tag}.json").read_text(encoding="utf-8"))
    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    recs = data["results"]

    out_path = DIR / out_name
    done = {}
    if out_path.exists():
        done = {r["qid"]: r for r in json.loads(out_path.read_text(encoding="utf-8"))["questions"]}
        print(f"이전 판정 {len(done)}건 재사용", flush=True)

    results = []
    for it in items:
        qid = it["qid"]
        if qid in done:
            results.append(done[qid])
            continue

        # R 청크 합집합 = 판정 근거
        chunks, seen = [], set()
        for r in recs:
            if r["qid"] != qid or r["arm"] != "R":
                continue
            for c in r["grounding"]["chunks"]:
                k = (nfc(c.get("title")), c.get("page_number"), nfc(c.get("text"))[:60])
                if k in seen:
                    continue
                seen.add(k)
                chunks.append(f"[{c.get('title')} p.{c.get('page_number')}]\n{c.get('text')}")
        corpus = "\n\n".join(chunks)[:CORPUS_CHARS]

        answers = [{"arm": r["arm"], "rep": r["rep"], "answer": r["answer"]}
                   for r in recs if r["qid"] == qid and r["arm"] in ("A", "B")]

        print(f"  codex 판정 {qid} (답변 {len(answers)} · 청크 {len(chunks)} · {len(corpus)}자)…",
              flush=True)
        res = codex_one({"qid": qid, "question": it["q"], "chunks": corpus, "answers": answers})
        res["qid"] = qid
        results.append(res)
        out_path.write_text(json.dumps({"source": f"_dump_{tag}.json", "questions": results},
                                       ensure_ascii=False, indent=1), encoding="utf-8")

    out_path.write_text(json.dumps({"source": f"_dump_{tag}.json", "questions": results},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    # 요약 — 과분기는 A·B 양쪽을 재야 '프롬프트가 유발했는가'를 말할 수 있다.
    def arm_stats(r, arm):
        rows = [x for x in r["results"] if x["arm"] == arm]
        n_br = [x["n_branches"] for x in rows]
        brs = [br for x in rows for br in (x.get("branches") or [])]
        ung = [br["condition"] for br in brs if br.get("grounded") is False]
        return n_br, len(brs), ung

    print(f"\n{'문항':<8}{'A 분기':<10}{'B 분기':<10}{'A 미근거':<9}{'B 미근거'}")
    print("-" * 62)
    tot = {"A": [0, 0, 0], "B": [0, 0, 0]}   # [분기합, 조건수, 미근거수]
    for r in results:
        cells = {}
        for arm in ("A", "B"):
            n_br, n_cond, ung = arm_stats(r, arm)
            cells[arm] = (n_br, ung)
            tot[arm][0] += sum(n_br) / max(len(n_br), 1)
            tot[arm][1] += n_cond
            tot[arm][2] += len(ung)
        print(f"{r['qid']:<8}{str(cells['A'][0]):<10}{str(cells['B'][0]):<10}"
              f"{len(cells['A'][1]):<9}{len(cells['B'][1])}")
    n = len(results)
    print("-" * 62)
    print(f"평균 분기       A={tot['A'][0]/n:.1f}   B={tot['B'][0]/n:.1f}")
    print(f"조건 총수       A={tot['A'][1]}     B={tot['B'][1]}")
    print(f"미근거 조건     A={tot['A'][2]}      B={tot['B'][2]}"
          f"   (비율 A={tot['A'][2]/max(tot['A'][1],1):.0%} · B={tot['B'][2]/max(tot['B'][1],1):.0%})")
    print(f"→ {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="bot7")
    ap.add_argument("--out", default="_branches_bot7.json")
    a = ap.parse_args()
    main(a.tag, a.out)
