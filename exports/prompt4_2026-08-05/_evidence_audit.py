# 관리자가 붙인 `규정집 근거 상태` 를 독립 재현한다 — v19·v20 양쪽으로.
#
# 왜 어휘 카운트로 하지 않는가 (실측):
#   · 관리자 키워드를 v20 코퍼스에 공백제거 부분문자열로 대조하면 45문항 중 43문항이
#     키워드 대부분 적중한다. '직접 근거 있음'(26)과 '직접 답변 근거 없음'(5)이 구분되지 않는다.
#   · 거짓양성도 난다 — '정자'가 규정집에서 24회 잡히지만 전부 확정자·행정자료·정자세다.
#   결론: 어휘 카운트는 **후보 회수**에만 쓰고, 판정은 조문 전문을 읽는 codex 가 한다.
#
# 왜 v19 도 보는가: 관리자 판정 기준이 v19 다(xlsx 탭 주석에 명시). 봇 11 이 검색하는 것은 v20.
#   v19 → v20 은 제38조 신설로 그 뒤 62개 조문이 +1 밀렸다. 스큐가 결론을 바꾸는지 확인해야 한다.
import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
CORPUS = ROOT / "exports/golden_2026-08/_corpus"
STEER = ROOT / "exports/glossary_steering_2026-08-04"
QUESTIONS = ROOT / "exports/regression/questions.json"

TOP_ART, TOP_GLO = 6, 5
BODY_CAP = 1800
BATCH = 3
TIMEOUT = 900
REASONING = "medium"

_HDR = re.compile(r"(?:^|(?<=[\f\r]))[ \t]*제\s*(\d+)\s*조\s*\(([^)]*)\)", re.M)
_DIGIT_KO = re.compile(r"(\d)\s+(?=[가-힣])")

INSTRUCTION = (
    "너는 종교(세계평화통일가정연합) 축복·가정행정 규정집의 근거 유무를 판정하는 심사관이다.\n"
    "<stdin>으로 JSON 배열이 들어온다. 각 항목:\n"
    "  key: 문항 식별자\n"
    "  question: 식구가 실제로 물은 질문\n"
    "  passages: 이 질문과 어휘가 겹쳐 회수된 규정집 조문·행정용어 후보 (전문)\n\n"
    "**판정 대상은 '어휘가 등장하는가'가 아니라 '이 질문에 답할 수 있는가'다.**\n"
    "질문의 핵심 쟁점을 passages 가 실제로 다루는지만 본다. 관련 어휘가 나와도 "
    "질문이 묻는 판단·기준·절차를 주지 못하면 근거가 아니다.\n\n"
    "각 항목을 다음으로 판정하라.\n"
    "① status — 정확히 셋 중 하나\n"
    "   '직접 근거 있음'      = passages 만으로 질문에 답할 수 있다\n"
    "   '부분 근거'           = 일부만 답하고 나머지는 최신 공문·담당부서 확인이 필요하다\n"
    "   '직접 답변 근거 없음' = 질문의 핵심 쟁점을 다루는 조문이 없다\n"
    "② cited — 근거로 삼은 조문번호·행정용어 번호 배열 (예: ['제65조','행정124']). 없으면 빈 배열.\n"
    "③ core_issue — 이 질문의 핵심 쟁점 한 문장.\n"
    "④ reason — 한국어 1~2문장. 어느 조문의 어느 대목이 답하는지(또는 왜 못 답하는지) 밝혀라.\n\n"
    "passages 에 없는 조문을 지어내지 마라. 확신이 어려우면 reason 에 명시하라.\n"
    "설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·key 로 출력하라. 각 원소 필드:\n"
    "{key, status, cited, core_issue, reason}"
)


def tighten(s):
    return _DIGIT_KO.sub(r"\1", unicodedata.normalize("NFC", str(s or "")))


def squash(s):
    return re.sub(r"\s+", "", tighten(s))


def shingles(s, n=3):
    t = squash(s)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def load_articles(version):
    if version == "v20":
        return json.loads((CORPUS / "articles_v20.json").read_text(encoding="utf-8"))
    text = (STEER / "_reg.txt").read_text(encoding="utf-8")
    hits = [(m.start(), int(m.group(1)), m.group(2).strip()) for m in _HDR.finditer(text)]
    arts = []
    for i, (pos, num, title) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        arts.append({"article": num, "title": title, "body": text[pos:end].rstrip()})
    nums = [a["article"] for a in arts]
    missing = [i for i in range(1, max(nums) + 1) if i not in set(nums)]
    if missing or len(arts) != 99:
        sys.exit(f"v19 조문 추출 실패 — {len(arts)}개 · 결번 {missing}. 판정 중단.")
    print(f"v19 조문 {len(arts)}개 · 결번 0")
    return arts


def rank(question, anchors, units, keyfn, textfn, top):
    """어휘 겹침으로 후보를 회수한다. 판정 근거가 아니라 회수용 점수다."""
    qs = shingles(question)
    aw = [squash(a) for a in anchors if len(squash(a)) >= 2]
    scored = []
    for u in units:
        body = squash(textfn(u))
        if not body:
            continue
        hit = sum(1 for a in aw if a in body)
        ov = len(qs & shingles(textfn(u))) / max(len(qs), 1)
        scored.append((hit * 2 + ov * 6, hit, keyfn(u), u))
    scored.sort(key=lambda x: (-x[0], x[2]))
    return [s[3] for s in scored[:top]]


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


def main(version, label=""):
    arts = load_articles(version)
    glo = json.loads((CORPUS / "glossary_v4.json").read_text(encoding="utf-8"))
    gong = json.loads((CORPUS / "gongmun.json").read_text(encoding="utf-8"))
    items = [i for i in json.loads(QUESTIONS.read_text(encoding="utf-8"))["items"]
             if i["bucket"] != "C"]
    out = DIR / f"_evidence_{version}{label}.json"

    graded = {}
    if out.exists():
        graded = {r["key"]: r for r in json.loads(out.read_text(encoding="utf-8"))["rows"]}
        print(f"이전 판정 {len(graded)}건 재사용")

    todo = []
    for it in items:
        key = str(it["no"])
        if key in graded:
            continue
        a = rank(it["q"], it["anchors"], arts,
                 lambda u: u["article"], lambda u: u["body"], TOP_ART)
        g = rank(it["q"], it["anchors"], glo,
                 lambda u: u["no"], lambda u: u["body"], TOP_GLO)
        m = rank(it["q"], it["anchors"], gong,
                 lambda u: u["name"], lambda u: u["body"], 1)
        passages = (
            [{"id": f"제{x['article']}조({x['title']})", "text": tighten(x["body"])[:BODY_CAP]}
             for x in a]
            + [{"id": f"행정{x['no']} {x['term']}", "text": tighten(x["body"])[:BODY_CAP]}
               for x in g]
            + [{"id": f"공문 {x['name']}", "text": tighten(x["body"])[:BODY_CAP]} for x in m])
        todo.append({"key": key, "question": it["q"], "passages": passages,
                     "_admin": it["evidence_status"], "_cat": it["cat"]})

    print(f"[{version}] 판정 대상 {len(todo)}문항")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        print(f"  codex 배치 {i//BATCH+1}/{(len(todo)+BATCH-1)//BATCH}…", flush=True)
        got = codex_batch([{k: v for k, v in c.items() if not k.startswith("_")} for c in chunk])
        for c in chunk:
            g = got.get(c["key"])
            if not g:
                print(f"    ⚠ 판정 누락: #{c['key']}")
                continue
            graded[c["key"]] = {
                "key": c["key"], "cat": c["_cat"], "q": c["question"],
                "admin_status": c["_admin"], "our_status": g.get("status"),
                "agree": c["_admin"] == g.get("status"),
                "cited": g.get("cited"), "core_issue": g.get("core_issue"),
                "reason": g.get("reason"),
                "candidates": [p["id"] for p in c["passages"]]}
        out.write_text(json.dumps(
            {"version": version, "rows": sorted(graded.values(), key=lambda r: int(r["key"]))},
            ensure_ascii=False, indent=1), encoding="utf-8")

    rows = sorted(graded.values(), key=lambda r: int(r["key"]))
    ok = sum(1 for r in rows if r["agree"])
    print(f"\n[{version}] 관리자 라벨과 일치 {ok}/{len(rows)} ({100*ok/max(len(rows),1):.0f}%)")
    mx = {}
    for r in rows:
        mx[(r["admin_status"], r["our_status"])] = mx.get((r["admin_status"], r["our_status"]), 0) + 1
    print("혼동행렬 (관리자 → 우리):")
    for (a, o), n in sorted(mx.items(), key=lambda x: -x[1]):
        print(f"   {a:<14} → {o:<14} {n:>2}")
    print("\n불일치:")
    for r in rows:
        if not r["agree"]:
            print(f"  #{r['key']:>2} [{r['admin_status']} → {r['our_status']}] {r['q'][:52]}")
            print(f"      {r['reason']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=["v19", "v20"], required=True)
    # 심사자(codex) 자신의 실행 간 변동을 재려면 같은 버전을 다른 라벨로 한 번 더 돌린다.
    # 버전 스큐를 주장하기 전에 잡음 바닥부터 알아야 한다.
    ap.add_argument("--label", default="", help="출력 파일 접미사 (재현성 측정용)")
    a = ap.parse_args()
    main(a.version, a.label)
