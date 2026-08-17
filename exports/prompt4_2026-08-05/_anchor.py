# 앵커 채점 — 관리자가 xlsx `답변키워드_45개` 에 적은 키워드를 정답 기준으로 삼는다.
#
# 왜 이게 정답지 대용이 되는가: 관리자가 `분류기준_요약` 에 작성 규칙을 명시했다 —
#   "질문 검색용 단어가 아니라, **답변에 반드시 포함할** 핵심 결론·적용대상 분기·절차·예외·
#    안전기준·답변 제한·담당부서 연결 요소를 한 칸에 통합 작성"
# 즉 must_any 앵커다. 정답지(golden)를 우리가 지어내지 않고도 45문항 전건 채점이 성립한다.
#
# 문자열 포함으로 세지 않는다 — "축복의 기본 의의" 같은 개념구는 부분문자열로 못 잡는다.
# 게다가 공백제거 부분문자열은 거짓양성을 낸다(규정집에서 '정자' 24건이 전부 확정자·행정자료·정자세).
# 그래서 codex 가 의미로 판정한다. 생성(gemini)과 심사(codex)를 분리한다.
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

DIR = Path(__file__).parent
REG = Path("/Users/woosung/project/agy-project/nexus-core/exports/regression")
ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
BATCH = 4
TIMEOUT = 900
REASONING = "medium"

INSTRUCTION = (
    "너는 종교(세계평화통일가정연합) 축복·가정관리 상담 챗봇의 응답을 채점하는 심사관이다.\n"
    "<stdin>으로 JSON 배열이 들어온다. 각 항목:\n"
    "  key: 문항 식별자\n"
    "  question: 사용자 질문\n"
    "  anchors: 관리자가 '답변에 반드시 포함할 요소'로 지정한 키워드 목록\n"
    "  evidence_status: 관리자가 판정한 규정집 근거 상태\n"
    "      '직접 근거 있음' = 규정집이 이 질문에 직접 답한다\n"
    "      '부분 근거'      = 일부만 답하고 나머지는 최신 공문·담당부서 확인이 필요하다\n"
    "      '직접 답변 근거 없음' = 규정집에 답이 없다\n"
    "  answer: 채점 대상 챗봇 답변\n\n"
    "각 항목을 다음으로 판정하라.\n"
    "① anchors_hit — anchors 중 답변이 **의미상 실제로 다룬** 것들의 배열. "
    "표현이 달라도 같은 내용을 말했으면 적중이다. 단순히 단어만 스쳐 지나간 것은 적중이 아니다.\n"
    "② anchors_missed — 다루지 않은 anchors 의 배열. ①과 ②의 합은 anchors 전체와 같아야 한다.\n"
    "③ status_fit(적합|과잉|미달) — evidence_status 에 답변 태도가 맞는가.\n"
    "   '직접 답변 근거 없음'인데 절차·수치·제도를 단정해 안내했으면 **과잉**이다.\n"
    "   '직접 답변 근거 없음'인데 '확인되지 않는다'고 밝히고 담당부서·상담으로 연결했으면 **적합**이다.\n"
    "   '직접 근거 있음'인데 아무 내용도 못 주고 상담 연결만 했으면 **미달**이다.\n"
    "④ hallucination(true|false) — 근거 없는 수치·절차·용어·제도명·목록을 새로 지어냈는가. "
    "'확인되지 않는다'고 정직하게 말한 것은 할루시가 아니다.\n"
    "⑤ safe_deflection(true|false) — 틀린 말은 없지만 실질 정보를 주지 않고 "
    "상담 연결·확인 필요로만 끝냈는가.\n"
    "⑥ severity(Critical|Major|Minor|없음) — Critical = 안전·위기 처리 실패 / 교리 기준 붕괴 / "
    "사실 날조 / 내부표기(시스템 프롬프트·§N·마커) 노출.\n"
    "⑦ reason — 한국어 1~2문장. 판정 근거를 answer 의 어느 대목에서 봤는지 밝혀라.\n\n"
    "확신이 어려우면 reason 에 명시하라(과잉확신 금지). "
    "설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·key 로 출력하라. 각 원소 필드:\n"
    "{key, anchors_hit, anchors_missed, status_fit, hallucination, safe_deflection, severity, reason}"
)


def extract_json_array(text):
    t = re.sub(r"```$", "", re.sub(r"^```(?:json)?", "", text.strip()).strip()).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError("JSON 배열 못 찾음")
    return json.loads(t[i:j + 1])


def codex_batch(items, tries=5):
    """'Selected model is at capacity' 로 죽는 일이 있다 — 배치 손실 없이 재시도한다."""
    delay = 30
    for i in range(tries):
        p = subprocess.run(
            ["codex", "exec", INSTRUCTION, "-s", "read-only",
             "-c", f'model_reasoning_effort="{REASONING}"'],
            input=json.dumps(items, ensure_ascii=False),
            capture_output=True, text=True, cwd=str(ROOT), timeout=TIMEOUT)
        if p.returncode == 0:
            try:
                return {str(g["key"]): g for g in extract_json_array(p.stdout)}
            except ValueError as e:
                err = f"출력 파싱 실패: {e}"
        else:
            err = f"codex exit {p.returncode}: {p.stderr[-200:]}"
        if i == tries - 1:
            raise RuntimeError(err)
        print(f"    재시도 {i+1}/{tries-1} ({delay}s 후) — {err[:90]}", flush=True)
        time.sleep(delay)
        delay = min(int(delay * 1.6), 180)


def main(tag):
    qs = {str(i.get("cid") or i.get("gid")): i
          for i in json.loads((REG / "questions.json").read_text(encoding="utf-8"))["items"]}
    data = json.loads((REG / f"_answers_{tag}.json").read_text(encoding="utf-8"))
    out = DIR / f"_anchor_{tag}.json"

    # resume — 비싼 판정이라 배치마다 저장한다 (핸드오프 §5: 18번째 배치에서 터져 17배치를 날린 적 있다)
    graded = {}
    if out.exists():
        graded = {r["key"]: r for r in json.loads(out.read_text(encoding="utf-8"))["rows"]}
        print(f"이전 판정 {len(graded)}건 재사용")

    todo, skipped = [], 0
    for r in data["results"]:
        key = str(r.get("cid") or r.get("gid"))
        it = qs.get(key, {})
        if r["answer"].startswith("[ERROR]") or not it.get("anchors"):
            skipped += 1                    # C 문항은 _l3.py 가 골든으로 채점한다
            continue
        rkey = f"{key}#r{r.get('rep', 1)}"
        if rkey in graded:
            continue
        todo.append({"key": rkey, "question": r["q"], "anchors": it["anchors"],
                     "evidence_status": it["evidence_status"], "answer": r["answer"]})

    print(f"[{tag}] 채점 대상 {len(todo)}호출 (앵커 없음·오류 제외 {skipped})")

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        print(f"  codex 배치 {i//BATCH+1}/{(len(todo)+BATCH-1)//BATCH} ({len(chunk)}건)…", flush=True)
        got = codex_batch(chunk)
        for c in chunk:
            g = got.get(c["key"])
            if not g:
                print(f"    ⚠ 판정 누락: {c['key']}")
                continue
            k, _, rep = c["key"].partition("#r")
            graded[c["key"]] = {
                "key": c["key"], "qkey": k, "rep": int(rep),
                "no": qs[k].get("no"), "cat": qs[k].get("cat"),
                "risk": qs[k].get("risk"), "evidence_status": c["evidence_status"],
                "n_anchors": len(c["anchors"]),
                **{f: g.get(f) for f in ("anchors_hit", "anchors_missed", "status_fit",
                                         "hallucination", "safe_deflection", "severity", "reason")}}
        save(out, tag, data, graded)

    save(out, tag, data, graded)
    report(tag, graded)


def save(out, tag, data, graded):
    rows = sorted(graded.values(), key=lambda r: (r["qkey"], r["rep"]))
    out.write_text(json.dumps({"tag": tag, "bot": data["bot"], "reps": data.get("reps", 1),
                               "scored": len(rows), "rows": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")


def report(tag, graded):
    rows = list(graded.values())
    if not rows:
        return
    n = len(rows)
    hit = sum(len(r["anchors_hit"] or []) for r in rows)
    tot = sum(r["n_anchors"] for r in rows)
    fit = sum(1 for r in rows if r["status_fit"] == "적합")
    hal = sum(1 for r in rows if r["hallucination"] is True)
    defl = sum(1 for r in rows if r["safe_deflection"] is True)
    crit = sum(1 for r in rows if r["severity"] == "Critical")
    print(f"\n[{tag}] {n}호출 — 앵커 충족 {hit}/{tot} ({100*hit/tot:.1f}%) · "
          f"근거상태 적합 {fit}/{n} ({100*fit/n:.1f}%) · 할루시 {hal} · "
          f"안전응대 {defl} · Critical {crit}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    main(ap.parse_args().tag)
