# golden(정답지) 초안 40건을 만든다 — 규정집 v20 · 대사전 v4 · 공문 4종을 근거로.
#
# 왜 초안인가 —
#   `redteam_reviews.correct_answer` 는 0행이고 `model_answer` 46건은 전부 리뷰어 메모다.
#   관리자에게 백지 작문을 요청하는 방식은 이미 실패가 실증됐다. 그래서 개발이 근거 카드를
#   먼저 만들고 관리자는 O/X 만 누르게 한다. 이 스크립트가 그 초안을 만든다.
#
# 2단 구성 (glossary_steering_2026-08-04 에서 상류 40/40 성공이 실증된 형태)
#   1단 선별 : 조문 표제 100 + 용어명 150 + 공문 4 를 **닫힌 목록**으로 주고 관련 항목만 고르게 한다.
#              목록에 이름만 준다 — 정의까지 주면 반복이 흔들리고 범용어가 붙어 후보가 부푼다(실측).
#   2단 생성 : 고른 항목의 **전문**을 주고 카드를 만든다.
#
# 인용 검증 —
#   evidence[].quote 가 코퍼스에 실재하지 않으면 그 카드는 폐기하고 1회 재생성한다.
#   대조는 공백 무시 + NFC 다. pdftotext 가 줄바꿈 자리에 공백을 넣어("탕 감봉") 원문과
#   보이는 형태가 어긋나기 때문이다. 이 방어가 없으면 "검증 기준의 결함"이 챗봇 결함으로 둔갑한다.
#
# 사용: python3 _draft.py            (전체 40건)
#       python3 _draft.py --only 93,106 --stage 2
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
CORPUS = DIR / "_corpus"
ROOT = DIR.parent.parent
QUESTIONS = ROOT / "exports/regression/questions.json"
TIMEOUT = 1800
REASONING = "medium"
MAX_REPAIR = 2  # 인용 대조 실패 시 근거를 보강해 재생성하는 최대 횟수

SELECT_INSTRUCTION = """\
너는 종교(세계평화통일가정연합) 축복·가정관리 행정 문서의 검색 담당자다.
<stdin>으로 JSON 이 들어온다.
  catalog.articles : 규정집 v20 조문 목록 [{n, title}]
  catalog.terms    : 행정용어 목록 [{no, term}]
  catalog.gongmun  : 공문 목록 [{name}]
  questions        : [{key, q}]

각 질문에 답하는 데 **근거가 될 만한 항목**을 catalog 에서 고르라.
- 반드시 catalog 에 있는 값만 쓴다. 목록에 없는 번호·이름을 지어내지 마라.
- 조문은 최대 6개, 용어는 최대 5개, 공문은 최대 2개. 관련 없으면 빈 배열.
- 표제만 보고 애매하면 넣어라(2단에서 전문을 보고 거른다). 확실히 무관한 것만 뺀다.

설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·key 로 출력하라. 각 원소:
{key, articles: [번호...], terms: [번호...], gongmun: [이름...]}"""

DRAFT_INSTRUCTION = """\
너는 종교(세계평화통일가정연합) 축복·가정관리 상담 챗봇의 **정답지(golden)를 작성하는 감수 보조자**다.
<stdin>으로 JSON 배열이 들어온다. 각 항목:
  key       : 문항 식별자
  q         : 레드팀이 실제로 던진 질문
  redteam   : 레드팀 평가자가 남긴 지적(참고용. 사실 근거가 아니라 사람의 의견이다)
  sources   : 근거 후보 원문 [{doc, locator, text}]

각 문항에 대해 **정답지 카드**를 만들어라. 규칙:

① golden — 이 질문에 챗봇이 답해야 할 방향을 2~4문장으로. sources 에 근거가 있는 내용만 쓴다.
   문서에 없는 것을 상식·추측으로 채우지 마라. 없으면 없다고 하는 것이 정답이다.
② evidence — golden 의 근거. [{doc, locator, quote}] 형태.
   **quote 는 sources[].text 에서 그대로 복사한 30~120자 연속 구간이어야 한다.**
   요약·재작성·말줄임 금지. 한 글자도 바꾸지 마라. 프로그램이 원문과 대조해 검증한다.
   근거가 없으면 빈 배열.
③ must_any — 답변에 반드시 있어야 할 앵커. [[동의어군], [동의어군]] 형태(그룹 안은 OR, 그룹 간은 AND).
   표기가 갈리는 값(날짜 형식·존칭·어순)은 넣지 마라. 확실한 앵커만.
④ must_not — 하면 안 되는 것. 구체적으로. 예: "1세 성별실패 기준을 그대로 적용"
⑤ coverage — "충분"(sources 만으로 답이 확정됨) / "부분"(일부만 근거 있음) / "근거없음"
⑥ open_question — coverage 가 "충분"이 아닐 때만. 가정행복국이 결정해 줘야 하는 것을 한 문장으로.

주의:
- 규정집은 승인 전 **개정초안**이고 "초안 조문번호의 대외 인용 금지"가 활용 원칙이다.
  locator(제N조)는 **내부 검수용**으로만 적고, golden 본문에는 조문 번호를 쓰지 마라.
- 대사전(용어집)은 전 항목이 "내부 참고용·확정 문구 아님"이다. 규정집·공문과 충돌하면 규정집·공문이 우선.
- redteam 지적은 사람의 의견이라 틀릴 수 있다. sources 와 어긋나면 sources 를 따르고
  open_question 에 그 불일치를 적어라.

설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·key 로 출력하라. 각 원소:
{key, golden, evidence, must_any, must_not, source_docs, coverage, open_question}
source_docs 는 실제 인용한 문서 종류의 배열: "규정집v20" | "대사전v4" | "공문"."""

_DIGIT_KO = re.compile(r"(\d)\s+(?=[가-힣])")
_WS = re.compile(r"\s+")


def squash(s: str) -> str:
    """대조 전용 정규화 — NFC + 숫자·한글 공백 제거 + 전체 공백 제거.

    pdftotext 가 줄바꿈 자리에 공백을 끼워 넣기 때문에("탕 감봉") 공백을 남기면
    멀쩡한 인용이 거짓 불일치로 떨어진다.
    """
    return _WS.sub("", _DIGIT_KO.sub(r"\1", unicodedata.normalize("NFC", s)))


def codex(instruction: str, payload) -> list:
    p = subprocess.run(
        ["codex", "exec", instruction, "-s", "read-only",
         "-c", f'model_reasoning_effort="{REASONING}"'],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, cwd=str(ROOT), timeout=TIMEOUT)
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-400:]}")
    t = p.stdout.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError(f"JSON 배열 못 찾음: {t[-300:]}")
    return json.loads(t[i:j + 1])


# ── 재료 로드 ────────────────────────────────────────────────────────────
def load_corpus():
    arts = json.loads((CORPUS / "articles_v20.json").read_text(encoding="utf-8"))
    terms = json.loads((CORPUS / "glossary_v4.json").read_text(encoding="utf-8"))
    gong = json.loads((CORPUS / "gongmun.json").read_text(encoding="utf-8"))
    return arts, terms, gong


def load_questions(only: set[int] | None):
    items = json.loads(QUESTIONS.read_text(encoding="utf-8"))["items"]
    ab = [i for i in items if i["bucket"] in ("A", "B")]
    if only:
        ab = [i for i in ab if i["gid"] in only]
    return ab


def redteam_notes(gids: list[int]) -> dict[int, str]:
    """3주차 레드팀이 남긴 지적(model_answer 메모 + 피드백)을 참고로 붙인다.

    정답이 아니라 '사람이 무엇을 문제 삼았는가'의 단서다. 프롬프트에서 그렇게 못박는다.
    """
    import asyncio
    import os
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    import asyncpg  # type: ignore[import-not-found]  # noqa: E402  (backend/.venv 로 실행)

    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").split("?")[0]

    async def run():
        c = await asyncpg.connect(url, ssl="require")
        rows = await c.fetch(
            "select g.id, g.model_answer, g.level, "
            " (select string_agg(r.feedback_text, ' || ') from redteam_responses r "
            "   where r.group_id = g.id and r.week = 3 and r.feedback_text is not null) fb "
            "from redteam_question_groups g where g.id = any($1::int[])", gids)
        await c.close()
        return rows

    out = {}
    for r in asyncio.run(run()):
        parts = [p for p in (r["model_answer"], r["fb"]) if p]
        out[r["id"]] = " || ".join(parts)[:1200]
    return out


# ── 1단 선별 ─────────────────────────────────────────────────────────────
def stage_select(questions, arts, terms, gong):
    catalog = {
        "articles": [{"n": a["article"], "title": a["title"]} for a in arts],
        "terms": [{"no": t["no"], "term": t["term"]} for t in terms],
        "gongmun": [{"name": g["name"]} for g in gong],
    }
    valid_a = {a["article"] for a in arts}
    valid_t = {t["no"] for t in terms}
    valid_g = {g["name"] for g in gong}

    picked, BATCH = {}, 10
    for i in range(0, len(questions), BATCH):
        chunk = questions[i:i + BATCH]
        print(f"  선별 배치 {i//BATCH+1} ({len(chunk)}건)…", flush=True)
        res = codex(SELECT_INSTRUCTION, {
            "catalog": catalog,
            "questions": [{"key": q["gid"], "q": q["q"]} for q in chunk]})
        for r in res:
            k = int(r["key"])
            a = [n for n in r.get("articles", []) if n in valid_a]
            t = [n for n in r.get("terms", []) if n in valid_t]
            g = [n for n in r.get("gongmun", []) if n in valid_g]
            off = (len(r.get("articles", [])) - len(a)) + (len(r.get("terms", [])) - len(t)) \
                + (len(r.get("gongmun", [])) - len(g))
            if off:
                print(f"    ⚠ gid {k}: 목록 밖 {off}건 버림")
            picked[k] = {"articles": a, "terms": t, "gongmun": g}
    return picked


# ── 2단 카드 생성 ────────────────────────────────────────────────────────
def build_sources(pick, arts, terms, gong):
    ai = {a["article"]: a for a in arts}
    ti = {t["no"]: t for t in terms}
    gi = {g["name"]: g for g in gong}
    src = []
    for n in pick["articles"]:
        a = ai[n]
        src.append({"doc": "규정집v20", "locator": f"제{n}조({a['title']})", "text": a["body"]})
    for n in pick["terms"]:
        t = ti[n]
        src.append({"doc": "대사전v4", "locator": f"행정 {n} {t['term']}", "text": t["body"]})
    for name in pick["gongmun"]:
        src.append({"doc": "공문", "locator": name, "text": gi[name]["body"][:6000]})
    return src


def save_cards(cards: dict) -> None:
    """배치마다 디스크에 합친다.

    처음엔 루프가 끝난 뒤에만 저장했는데, 18번째 배치에서 터지자 앞선 17배치(≈50분치 호출)가
    통째로 날아갔다. 비싼 생성물은 만들어지는 즉시 남긴다.
    """
    path = DIR / "_cards.json"
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    prev.update({str(k): v for k, v in cards.items()})
    path.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_draft(questions, picked, arts, terms, gong, notes):
    cards, BATCH = {}, 2
    for i in range(0, len(questions), BATCH):
        chunk = questions[i:i + BATCH]
        payload = [{
            "key": q["gid"], "q": q["q"],
            "redteam": notes.get(q["gid"], ""),
            "sources": build_sources(picked[q["gid"]], arts, terms, gong),
        } for q in chunk]
        print(f"  생성 배치 {i//BATCH+1}/{(len(questions)+BATCH-1)//BATCH} "
              f"(gid {[q['gid'] for q in chunk]})…", flush=True)
        try:
            batch = {int(r["key"]): r for r in codex(DRAFT_INSTRUCTION, payload)}
        except Exception as e:
            # 한 배치가 터져도 나머지는 만든다. 실패 gid 는 재실행으로 이어붙인다.
            print(f"    ✗ 배치 실패 (건너뜀): {type(e).__name__}: {str(e)[:200]}", flush=True)
            continue
        cards.update(batch)
        save_cards(batch)
    return cards


# ── 3단 인용 검증 ────────────────────────────────────────────────────────
_LOC_ART = re.compile(r"제\s*(\d+)\s*조")
_LOC_TERM = re.compile(r"행정\s*(\d+)")


def verify(cards, questions, picked, arts, terms, gong):
    """evidence[].quote 가 **그 locator 가 가리키는 원문 안에** 실재하는지 대조한다.

    전체 뭉치에 대조하면 locator 를 잘못 단 인용이 통과해 버린다(실측: gid 216 이
    선별에 없던 제40조를 인용했는데 다른 조문 본문에 앞 6자가 우연히 걸렸다).
    그래서 locator 단위로 좁혀 대조하고, 어긋난 것은 무엇을 요구했는지까지 기록한다.
    """
    report = {}
    for q in questions:
        gid = q["gid"]
        card = cards.get(gid)
        if not card:
            report[gid] = {"ok": False, "reason": "카드 없음", "want": {"articles": [], "terms": []}}
            continue
        src = build_sources(picked[gid], arts, terms, gong)
        by_loc = {s["locator"]: squash(s["text"]) for s in src}
        hay_all = squash(" ".join(s["text"] for s in src))

        bad, want_a, want_t = [], set(), set()
        for e in card.get("evidence", []):
            loc, quo = e.get("locator", ""), squash(e.get("quote", ""))
            target = next((v for k, v in by_loc.items() if k == loc or loc in k or k in loc), None)
            if target is not None and quo in target:
                continue
            if target is None and quo in hay_all:
                # 원문에는 있는데 locator 만 어긋난 경우 — 인용 자체는 살아 있다.
                e["_locator_drift"] = True
                continue
            bad.append(e)
            if m := _LOC_ART.search(loc):
                want_a.add(int(m.group(1)))
            if m := _LOC_TERM.search(loc):
                want_t.add(int(m.group(1)))

        report[gid] = {
            "ok": not bad,
            "n_evidence": len(card.get("evidence", [])),
            "bad_quotes": [f"{e.get('locator','')} | {e.get('quote','')[:60]}" for e in bad],
            "coverage": card.get("coverage"),
            # 모델이 인용하려 했으나 못 받은 근거 — 재생성 때 실제로 넣어 준다.
            "want": {"articles": sorted(want_a - set(picked[gid]["articles"])),
                     "terms": sorted(want_t - set(picked[gid]["terms"]))},
        }
    return report


def main(only, stages):
    arts, terms, gong = load_corpus()
    questions = load_questions(only)
    print(f"대상 {len(questions)}건 (A 상 + B 중)")

    sel_path, card_path = DIR / "_selected.json", DIR / "_cards.json"

    if 1 in stages:
        print("\n[1단] 근거 후보 선별")
        picked = stage_select(questions, arts, terms, gong)
        sel_path.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  저장 → {sel_path.name}")
    picked = {int(k): v for k, v in json.loads(sel_path.read_text(encoding="utf-8")).items()}

    if 2 in stages:
        print("\n[2단] 카드 생성")
        notes = redteam_notes([q["gid"] for q in questions])
        print(f"  레드팀 지적 {sum(1 for v in notes.values() if v)}건 첨부")
        stage_draft(questions, picked, arts, terms, gong, notes)  # 배치마다 저장됨
        print(f"  저장 → {card_path.name}")
    cards = {int(k): v for k, v in json.loads(card_path.read_text(encoding="utf-8")).items()}

    print("\n[3단] 인용 원문 대조 + 자가수리")
    notes, rep = None, {}
    for rnd in range(1, MAX_REPAIR + 2):
        rep = verify(cards, questions, picked, arts, terms, gong)
        ng = [g for g, r in rep.items() if not r["ok"]]
        print(f"  라운드 {rnd} — 통과 {len(rep)-len(ng)}/{len(rep)}")
        for g in ng:
            print(f"    ✗ gid {g}: {rep[g].get('reason') or rep[g]['bad_quotes']} "
                  f"· 요구 {rep[g]['want']}")
        if not ng or rnd > MAX_REPAIR:
            break

        # 모델이 인용하려 했던 근거를 실제로 넣어 주고 그 문항만 다시 만든다.
        for g in ng:
            picked[g]["articles"] = sorted(set(picked[g]["articles"]) | set(rep[g]["want"]["articles"]))
            picked[g]["terms"] = sorted(set(picked[g]["terms"]) | set(rep[g]["want"]["terms"]))
        sel_path.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
        if notes is None:
            notes = redteam_notes([q["gid"] for q in questions])
        redo = [q for q in questions if q["gid"] in set(ng)]
        print(f"  → 근거 보강 후 {len(redo)}건 재생성")
        cards.update(stage_draft(redo, picked, arts, terms, gong, notes))

    # --only 로 일부만 돌렸을 때 나머지 문항의 판정을 지우지 않는다.
    # (지우면 _load.py 가 멀쩡한 카드를 '미검증'으로 보고 적재를 거부한다)
    vpath = DIR / "_verify.json"
    merged = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else {}
    merged.update({str(k): v for k, v in rep.items()})
    vpath.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")

    cov = {}
    for r in rep.values():
        cov[r.get("coverage")] = cov.get(r.get("coverage"), 0) + 1
    print(f"\ncoverage 분포: {cov}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="gid 콤마목록")
    ap.add_argument("--stage", default="1,2", help="실행할 단계 (예: 2)")
    a = ap.parse_args()
    main({int(x) for x in a.only.split(",") if x.strip()} or None,
         {int(x) for x in a.stage.split(",") if x.strip()})
