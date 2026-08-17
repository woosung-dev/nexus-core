"""replay 결과를 「왜 답 못 했나」 4값으로 가른다. **LLM 호출 0회.**

## 이 스크립트가 푸는 문제

STEP 3 의 목적은 「무엇을 못 답하나」를 목록으로 만드는 것이다. 그 목록에서
**`문서없음`(관리자에게 자료 요청)과 `검색못함`(우리 검색기 잘못)을 가르는 것이 전부다.**
둘을 섞으면 우리 검색 문제인 것을 「자료 주세요」로 떠넘기게 되고, 한 번 그러면 신뢰를 잃는다.

## 판정은 문자열 매칭으로만 한다

**검색 점수로 결손을 판정하는 것은 3전 3패다.** 여기서도 안 쓴다.
질문의 말이 코퍼스 250유닛 **원문에 있느냐**만 본다.

## 어떻게 「말이 있는지」 보나 — 어미 사전 없이

한국어 어절은 `[명사][조사/어미]` 라 명사가 앞에 온다. 그래서 어절의 **접두 부분문자열 중
코퍼스에 실제로 있는 가장 긴 것**을 그 어절의 개념으로 본다.

    "축복반지는" → "축복반지"(2유닛에 있음)   ← 개념 발견
    "오른손"     → "오른손"·"오른" 다 없음    ← MISS

어미 벗기기 사전을 쓰면 실패한다(실측: `축복반지는` df=0 vs `축복반지` df=2 로 갈렸다).
접두 방식은 사전이 필요 없다.

`squash()` 는 반드시 쓴다 — pdftotext 가 숫자·한글 사이에 공백을 넣는다(`제 41 조`).

## ⚠⚠ 어휘로 가를 수 있는 것에는 한계가 있다 — 이걸 모르고 손대지 마라

45문항 정답지로 자를 검증했다. 정답지가 「문서에없음」이라고 판정한 7문항 중
**MISS 신호가 뜬 것은 2건뿐이다.**

| 문항 | 어휘 신호 |
|---|---|
| 초등학교 저학년 성폭행이 탈선인가 | ✅ `성폭행`·`초등학교` 가 코퍼스에 없다 |
| 대학원 장학 축복 특별 전형 | ✅ `대학원` 이 없다 |
| 하늘이 정해준 인연이 존재하나 | ❌ `인연`(2유닛)·`결혼`(26유닛) 다 있다. **말은 있는데 답이 없다** |
| 교류 기간이 정해져 있나 | ❌ `교류`·`기간` 다 있다 |
| 미성년자도 축복 가능한가 | ❌ `미성년자`(2유닛) 있다 |
| 3일 행사 기도는 어떻게 하나 | ❌ `기도`·`행사` 다 있다 |

**어휘 매칭은 「그 말이 코퍼스에 있나」까지만 답한다. 「그 쟁점에 답이 있나」는 못 답한다.**
검색 점수로 판정하려다 3전 3패한 것과 같은 벽이다 — 자를 더 정교하게 만들어도 안 넘는다.

### ⚠⚠ 그래서 `문서없음` 을 자료 요청 근거로 **그대로 쓰지 마라**

600건 replay 에서 `문서없음` 167건이 나왔는데, **167건 전부가 자료를 3건 이상 받았다.**
「검색이 빈손」은 0건이다. 원문을 열어 보니 대부분 **다른 말로 다루고 있었다.**

    「야동을 어떻게 생각하나요?」  코퍼스에 `야동` 없음 → 자는 「문서없음」
                               실제로는 제65·66조가 **「음란물」** 로 정면으로 다룬다

관리자 요청서에 「성 관련 자료가 없습니다」를 넣기 직전에 잡았다. 규정집은 제65조 ⑧에서
**「세부 행위의 방법을 기준표처럼 설명하지 않는다」** 고 이미 정해 두었다 — 자료가 없는 게 아니라
**답하지 않기로 정한 것**이었다.

**반드시 `injected` 유닛의 원문을 열어 보고 나서 자료 결손이라고 말해라.**

그래서 이 스크립트는 **판정하지 않는다.** 확실한 것만 라벨을 달고 나머지는 `미분류` 로 남긴다.
`미분류` 가 많이 나오는 것이 정직한 결과다. **k(반복 횟수) 순으로 정렬해 사람이 위에서부터 본다.**

## 거대 유닛 함정

`reg-100`(29,774자 · 데스밸리 특별성염)과 `reg-3`(8,377자 · 용어의 정리)에는 **아무 말이나 다 있다**
(중앙값은 232자다). 「질문의 말이 reg-100 에 있다」는 아무 정보가 아니다.
그래서 `BIG_UNIT` 이상은 검색못함 증거에서 뺀다.

## 자의 실측 성능 (45문항 정답지 대조 · `s1_lex_0813` 답못함 75셀)

| 정답지 | → 문서없음 | → 검색못함 | → 미분류 | 계 |
|---|---:|---:|---:|---:|
| 일치·부분일치 (답이 문서에 있다) | 18 | 3 | 16 | 37 |
| 문서에없음 | **6** | 0 | 8 | 14 |
| 불일치 | 4 | 0 | 2 | 6 |
| 함정(C) | 8 | 2 | 6 | 18 |

**「문서없음」 재현율 43%(6/14).** 나머지는 `미분류` 로 흘렀다 — 말은 있는데 답이 없는 경우다.

**「일치·부분일치인데 문서없음」 18셀을 실사하면 세 종류가 섞여 있다.**

| 종류 | 예 | 판단 |
|---|---|---|
| 진짜 결손 | `스킨십`·`불륜`·`아내`·`Blessing 4u` 가 코퍼스에 없다 | 정답지 쪽이 느슨했다 |
| **용어 불일치** | 사용자는 `외도`·`폭행`, 규정집은 `탈선` | 결손이 아니라 **동의어 문제** |
| 기능어 잔여 | `언제부터`·`쓰러질`·`내년에는` | 노이즈 |

세 번째만 걸러내려고 자를 더 조이면 첫 번째가 죽는다. **그래서 여기서 멈췄다.**
사람이 MISS 어절만 보면 30초에 가른다 — FINDINGS.md 는 그걸 그대로 보여준다.

> **용어 불일치는 별도 축이다.** `문서없음` 으로 관리자에게 올리면 안 된다.
> 검색 동의어나 용어집으로 풀 문제다. 사람 확인 때 이 축부터 걸러라.

## 쓰는 법

    cd backend && .venv/bin/python ../exports/replay_2026-08/_triage.py --tag replay_0814
    cd backend && .venv/bin/python ../exports/replay_2026-08/_triage.py --tag replay_0814 --md
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "exports/wiki_2026-08"))
sys.path.insert(0, str(ROOT / "exports/regression"))

from _common import load_sources, squash  # noqa: E402
from _kpi import replay as gate_replay  # noqa: E402  strict 게이트 오프라인 재현

# 변별력 상한. 250유닛 중 60건(24%) 넘게 나오면 「축복」·「가정」 류라 판정에 못 쓴다.
DF_MAX = 60
MINLEN = 2
# 이 크기를 넘는 유닛은 「말이 있다」의 증거로 못 쓴다(중앙값 232자 · 12건이 여기 걸린다).
BIG_UNIT = 3000

# 용언 활용형·관형형·부사형 꼬리. MISS 어절이 이걸로 끝나면 **개념이 아니라 서술어**다.
#   걷어내는 것  깜빡하고 · 빼먹었어 · 당했습니다 · 프리패스라던데 · 친절한 · 부드러운 · 열심히
#   남기는 것    성폭행을 · 대학원 · 남편이 · 불륜을 · 스킨십은 · B4U
# **조사 `을/를/은/는/이/가` 는 일부러 안 넣었다** — 「성폭행을」의 신호가 죽는다.
# 「기한」·「권한」처럼 `한` 으로 끝나는 명사는 코퍼스에 있어서 애초에 MISS 에 안 온다.
_VERBY = re.compile(
    r"(?:다|요|까|죠|네|고|서|며|면|지|자|나|데|걸|게|듯|든|어|아|여"
    r"|한|운|된|히|린|찮|롭|랑|처럼|만큼)$"
)

# 질문 어투·기능어. 600건 실측 MISS 빈도 상위에서 **명백한 것만** 골랐다.
# 「남편」·「아이」·「불륜」·「스킨십」 처럼 코퍼스에 없는 **실질 개념**은 일부러 안 넣었다 —
# 그게 바로 찾으려는 결손이다.
STOP = {
    "어떻게", "있나요", "어떤", "되나요", "너무", "싶은데", "뭐야", "좋을까", "건가요", "같아",
    "싶어", "많이", "있습니다", "무엇인가요", "될까", "저는", "저를", "저도", "저에게",
    "어디까지", "그런데", "할까요", "어떤게", "좋을까요", "좋은", "자꾸", "할까", "거야",
    "해도", "했어", "싶지", "혹시", "될까요", "언제", "알게", "모르겠어", "싶어요", "이번에",
    "무엇이", "뭔가요", "돼요", "그냥", "했지만", "그래도", "궁금해", "그리고", "갖고",
    "이런", "뭐가", "정말", "있고", "것인가", "뭐예요", "얼마예요", "생겼습니다", "했습니다",
    "만나고", "받으면", "받으려고", "받나요", "좋아하는", "세인데", "세입니다", "알고",
    "이게", "둘다", "보면", "때까지", "어디", "누가", "언제까지", "인가요", "합니까",
}

_WORD = re.compile(r"[가-힣]+|[A-Za-z0-9]+")

# 심경·관계 어휘. **판정이 아니라 힌트다**(evidence 에 `⟨상담?⟩`, FINDINGS 에 ●/○).
# 이 말이 들어간 질문은 대개 「규정집에 없다」가 아니라 **규정집이 답할 문제가 아니다** —
# 고립감·부채 압박·외도 뒤 죄책감·매칭 실패 상처·시댁 갈등 같은 상담·목회 영역이다.
# 이걸 `문서없음` 으로 관리자에게 올리면 **헛된 요청**이 된다(600건 replay 에서 큰 군집을 이룬다).
# 임계값은 1개다 — 2개로 하면 「고립감」 하나짜리를 놓친다(실측 4건 vs 20건).
_FEELING = (
    "불안", "상처", "두려", "압박", "고립", "죄책", "공포", "외로", "우울", "슬프", "슬픔",
    "화가", "분노", "서운", "미안", "부담", "걱정", "혼란", "갈등", "괴로", "설레", "눈길",
    "힘들", "지쳐", "지침", "위로", "격려", "확신", "자존", "열등", "눈치", "취약", "후회",
    "자책", "부끄", "수치", "미련", "심리적", "감정", "마음이", "심경",
)


class Corpus:
    """코퍼스 250유닛의 원문 색인. 봇 11 manifest 기준."""

    def __init__(self, bot_id: int = 11):
        units = load_sources(bot_id)
        self.units = units
        # locator 도 붙인다 — 「제41조」·「행정 47 미납 정산」 로 물어보는 질문이 있다.
        # **casefold 한다.** 안 하면 `B4U`(코퍼스 13유닛)를 소문자 `b4u` 로 찾아 거짓 MISS 가
        # 난다 — 2026-08-15 에 관리자 요청서에 「B4U 자료가 없습니다」를 넣을 뻔했다.
        self.txt = {sid: squash(u["text"] + " " + u["locator"]).casefold()
                    for sid, u in units.items()}
        self.blob = "\x1f".join(self.txt.values())  # 존재 여부 1차 판별(빠르다)
        self._df: dict[str, int] = {}

    def df(self, tok: str) -> int:
        if tok in self._df:
            return self._df[tok]
        t = squash(tok).casefold()
        n = 0 if (not t or t not in self.blob) else sum(1 for x in self.txt.values() if t in x)
        self._df[tok] = n
        return n

    def hits(self, tok: str, small_only: bool = False) -> list[str]:
        t = squash(tok).casefold()
        out = [sid for sid, x in self.txt.items() if t in x]
        if small_only:
            out = [s for s in out if len(self.units[s]["text"]) <= BIG_UNIT]
        return out

    def concept(self, word: str) -> tuple[str, int] | None:
        """어절 → (코퍼스에 있는 가장 긴 접두, df). 없으면 None."""
        w = word.casefold()
        for L in range(len(w), MINLEN - 1, -1):
            d = self.df(w[:L])
            if d:
                return (w[:L], d)
        return None

    def analyze(self, q: str) -> tuple[list, list]:
        """질문 → (변별 개념 [(말, df)], 코퍼스에 없는 말 [어절])."""
        found, miss = [], []
        for w in _WORD.findall(q):
            if len(w) < MINLEN or w in STOP:
                continue
            c = self.concept(w)
            if c is None:
                # 용언 활용형은 개념이 아니다 — 결손 신호로 못 쓴다
                if not _VERBY.search(w):
                    miss.append(w)
            elif c[1] <= DF_MAX:
                found.append(c)
        # 같은 개념이 여러 어절에서 나오면 한 번만
        seen, uf = set(), []
        for t, d in sorted(found, key=lambda x: (x[1], -len(x[0]))):
            if t not in seen:
                seen.add(t)
                uf.append((t, d))
        return uf, sorted(set(miss), key=len, reverse=True)

    def best_units(self, found: list, n: int = 3) -> list[tuple[str, int]]:
        """변별 개념을 **절반 이상** 담은 유닛. 「검색이 여기를 뽑았어야 했다」의 후보.

        절반 조건이 없으면 개념 2개만 겹쳐도 걸려 거의 모든 턴이 `검색못함` 이 된다(실측).
        거대 유닛은 아무 말이나 다 있어 증거가 안 되므로 뺀다.
        """
        if len(found) < 3:
            return []
        need = max(3, (len(found) + 1) // 2)
        c: Counter = Counter()
        for t, _ in found:
            for sid in self.hits(t, small_only=True):
                c[sid] += 1
        return [(sid, k) for sid, k in c.most_common(n) if k >= need]


def injected(row: dict) -> set[str]:
    """이 턴에 실제로 주입된 유닛 id. `…+N` 센티넬은 버린다(`turn_trace._clip`)."""
    for s in ((row.get("trace") or {}).get("stages") or []):
        if s.get("stage") == "retrieval":
            refs = s.get("unit_refs") or []
            return {r.split(":", 1)[0] for r in refs if not r.startswith("…")}
    return set()


def classify(held: bool, found: list, miss: list, best: list, inj: set,
             feelings: int = 0) -> tuple[str, str, str]:
    """(triage 후보, 확신도, 근거 한 줄).

    **판정이 아니라 후보다.** 어휘로 못 가르는 것은 `미분류` 로 남긴다 — 그게 정직하다.
    순서가 중요하다: `문서없음`(코퍼스에 말 자체가 없다)이 가장 강한 증거라 먼저 본다.
    """
    if not held:
        return ("답변함", "-", "게이트를 통과했다")
    # ① 코퍼스에 말 자체가 없다 — 어휘로 확실히 아는 유일한 경우
    strong_miss = [w for w in miss if len(w) >= 3]
    if strong_miss:
        conf = "강" if not found else ("중" if len(strong_miss) >= 2 else "약")
        tail = "" if not found else f" (다른 말은 있음: {found[0][0]})"
        mark = " ⟨상담?⟩" if feelings else ""
        return ("문서없음", conf, f"코퍼스에 없는 말: {' '.join(strong_miss[:4])}{tail}{mark}")
    # ② 말은 있는데 그 말이 몰린 유닛이 주입 안 됐다
    #
    # ⚠ 확신도를 나눈다. 21건 실사에서 **8건은 최상위 유닛이 이미 주입돼 있었고**
    # 2·3순위만 빠진 경우였다. 그건 「검색이 놓쳤다」가 아니다 — 이미 제일 좋은 것을 뽑았다.
    # 이 목록은 우리 검색기 개선용이라 과대평가하면 헛수고를 부른다.
    uncaught = [sid for sid, _ in best if sid not in inj]
    if uncaught:
        top_missed = best[0][0] not in inj
        return ("검색못함", "강" if top_missed else "약",
                f"변별어가 가장 몰린 {uncaught[0]} 이 주입 안 됨 (주입 {len(inj)}건)"
                if top_missed else
                f"{uncaught[0]} 이 빠짐 — 다만 최상위 {best[0][0]} 은 주입됐다 (증거 약함)")
    if not found and not miss:
        return ("해당없음", "약", "규정 어휘가 없는 질문")
    # ③ 말은 다 있고 유닛도 주입됐는데 답을 못 했다 = 어휘로는 못 가른다
    return ("미분류", "-", "말도 유닛도 있는데 답을 못 했다 — 어휘로는 못 가른다. 사람이 볼 것")


def run(tag: str, want_md: bool) -> None:
    src = ROOT / f"exports/regression/_e2e_{tag}.json"
    if not src.exists():
        sys.exit(f"없다: {src}")
    rows = [r for r in json.loads(src.read_text(encoding="utf-8"))["results"] if not r.get("error")]

    kmap = {}
    inp = DIR / "_input.json"
    if inp.exists():
        for it in json.loads(inp.read_text(encoding="utf-8"))["items"]:
            kmap[it["cid"]] = it["k"]

    C = Corpus()
    out = []
    for r in rows:
        d = gate_replay(r)
        held = d["blocked"] or d["sr"]
        found, miss = C.analyze(r["q"])
        best = C.best_units(found)
        inj = injected(r)
        feelings = sum(1 for w in _FEELING if w in r["q"])
        tri, conf, why = classify(held, found, miss, best, inj, feelings)
        out.append({
            "cid": r.get("cid"), "k": kmap.get(r.get("cid"), 1), "q": r["q"],
            "held": held, "gate_why": d["why"], "triage": tri, "confidence": conf,
            "evidence": why,
            "feelings": feelings,
            "found": found[:8], "missing": miss[:6],
            "best_units": best, "injected": sorted(inj),
            "answer_head": (r.get("answer") or "")[:160].replace("\n", " "),
        })
    out.sort(key=lambda x: (-x["k"], x["cid"] or ""))

    dst = DIR / f"_triage_{tag}.json"
    dst.write_text(json.dumps({"tag": tag, "count": len(out), "rows": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    held_rows = [r for r in out if r["held"]]
    print(f"\n═══ {tag} · {len(out)}건 ═══")
    print(f"  답 못 함 {len(held_rows)}건 ({len(held_rows) / len(out) * 100:.1f}%)")
    print(f"  원발화 기준: 못 답한 질문이 덮는 반복 횟수 {sum(r['k'] for r in held_rows)}회 "
          f"/ 전체 {sum(r['k'] for r in out)}회")
    print("\n  triage 후보 (※ 판정 아님 — 상위 항목은 사람이 확인한다)")
    for t, n in Counter(r["triage"] for r in out).most_common():
        ks = sum(r["k"] for r in out if r["triage"] == t)
        strong = sum(1 for r in out if r["triage"] == t and r["confidence"] == "강")
        print(f"    {t:6} {n:>4}건 (원발화 {ks:>4}회) · 확신 강 {strong}건")
    print(f"\n  → {dst}")

    if want_md:
        write_md(tag, out)


def write_md(tag: str, out: list) -> None:
    held = [r for r in out if r["held"]]
    pick = lambda t: [r for r in held if r["triage"] == t]  # noqa: E731
    nodoc, notfound, unk = pick("문서없음"), pick("검색못함"), pick("미분류")
    ksum = lambda rs: sum(r["k"] for r in rs)  # noqa: E731
    L = [
        f"# replay 결손 목록 — {tag}",
        "",
        "> 라이브 실사용자 질문을 로컬 봇 29 로 다시 물어 만든 목록이다. **빈도(k) 순.**",
        f"> 생성: `_triage.py --tag {tag} --md` · LLM 호출 0회 · 판정은 코퍼스 250유닛 문자열 매칭",
        "",
        "## ⚠ 이 표를 관리자에게 그대로 보내지 마라",
        "",
        "자동 분류는 **후보**다. 45문항 정답지 대조에서 「문서없음」 재현율은 43% 였고,",
        "「문서없음」 으로 잡힌 것 중에는 **용어 불일치**(사용자 `외도`·`폭행` ↔ 규정집 `탈선`)와",
        "기능어 노이즈가 섞인다. **관리자 요청서에는 「확인」 열에 표시한 것만 올린다.**",
        "",
        "확인할 때 가르는 축 **네 가지**:",
        "",
        "1. **진짜 결손** — 규정집이 그 쟁점을 안 다룬다 → **관리자 요청**",
        "2. **용어 불일치** — 다른 말로는 다룬다(사용자 `외도` ↔ 규정집 `탈선`) → 검색 동의어·용어집",
        "3. **상담 영역** — 규정이 답할 문제가 아니다(고립감·죄책감·부채 압박·시댁 갈등)",
        "   → 응대 문구·목회 연결. **관리자에게 「규정집에 넣어달라」고 하면 헛된 요청이 된다**",
        "4. **노이즈** — 기능어가 MISS 로 남은 것 → 버린다",
        "",
        "> `상담?` 열: `●` 심경 어휘 2개 이상 · `○` 1개. 3번일 가능성 신호일 뿐 **판정은 아니다.**",
        "",
        "## 요약",
        "",
        "| | 질문 | 원발화 |",
        "|---|---:|---:|",
        f"| 전체 | {len(out)} | {ksum(out)} |",
        f"| **답 못 함** | **{len(held)}** | **{ksum(held)}** |",
        f"| ↳ 문서없음 후보 | {len(nodoc)} | {ksum(nodoc)} |",
        f"| ↳ 검색못함 후보 | {len(notfound)} | {ksum(notfound)} |",
        f"| ↳ 미분류(어휘로 못 가름) | {len(unk)} | {ksum(unk)} |",
        "",
        "## 1. 문서없음 후보 — 관리자 요청 재료",
        "",
        "「코퍼스에 없는 말」을 보고 위 4축으로 가른다.",
        "",
        "| k | cid | 질문 | 코퍼스에 없는 말 | 확신 | 상담? | 판정(1~4) |",
        "|---:|---|---|---|:--:|:--:|:--:|",
    ]
    for r in nodoc[:120]:
        L.append(f"| {r['k']} | {r['cid'] or '-'} | {r['q'][:58]} | {' '.join(r['missing'][:4])} "
                 f"| {r['confidence']} | {'●' if r.get('feelings', 0) >= 2 else ('○' if r.get('feelings') else '')} | |")
    L += [
        "",
        "## 2. 검색못함 후보 — 우리 검색기가 고칠 것",
        "",
        "질문의 변별어가 몰린 유닛이 **주입되지 않았다**. 관리자에게 올리지 않는다.",
        "",
        "| k | cid | 질문 | 있는데 못 뽑은 유닛 | 주입된 유닛 |",
        "|---:|---|---|---|---|",
    ]
    for r in notfound[:80]:
        u = ", ".join(f"`{s}`({n})" for s, n in r["best_units"][:2])
        L.append(f"| {r['k']} | {r['cid'] or '-'} | {r['q'][:52]} | {u} | "
                 f"{', '.join(r['injected'][:4])} |")
    L += [
        "",
        "## 3. 미분류 — 말도 유닛도 있는데 답을 못 했다",
        "",
        "**어휘로는 못 가른다.** 대신 **게이트가 왜 막았는지**로 가르면 갈 곳이 보인다.",
        "",
        "| 게이트 사유 | 질문 | 원발화 | 어디로 |",
        "|---|---:|---:|---|",
    ]
    _ROUTE = {
        "①주입 근거를 안 짚음(표기 누락)":
            "**게이트 과잉 차단.** 자료는 제대로 뽑혔는데 모델이 표기를 안 했다 → 우리 문제",
        "②주입 목록 밖 근거를 댐(지어냄)": "게이트가 **옳게** 막았다 → 모델/생성 쪽",
        "표기 없음 + 지어냄": "게이트가 옳게 막았다 → 모델/생성 쪽",
        "통과": "게이트는 통과했는데 봇이 스스로 「확인되지 않습니다」 → 규정 결손일 수 있다",
        "주입 0건": "검색이 빈손 → 검색기",
        "검색 폴백": "lexical 이 비어 file_search 로 넘어갔다 → 코퍼스/검색기",
    }
    for why, n in Counter(r["gate_why"] for r in unk).most_common():
        k = sum(r["k"] for r in unk if r["gate_why"] == why)
        L.append(f"| {why} | {n} | {k} | {_ROUTE.get(why, '—')} |")
    L += [
        "",
        "> **「표기 누락」이 크면 프롬프트를 또 만들지 마라.** 인용 형식 지시는 45문항에서 7건→1건으로",
        "> 표적을 맞혔는데도 실사용자 질문에서는 다시 커진다 — 「축복은 왜 받아야 해요?」처럼 조문을",
        "> 인용할 자리가 없는 열린 질문이 많기 때문이다. 프롬프트가 아니라 **게이트 쪽**을 봐야 한다.",
        "",
        "| k | cid | 질문 | 게이트 사유 | 주입된 유닛 | 판정 |",
        "|---:|---|---|---|---|:--:|",
    ]
    for r in unk[:80]:
        L.append(f"| {r['k']} | {r['cid'] or '-'} | {r['q'][:52]} | {r['gate_why']} | "
                 f"{', '.join(r['injected'][:4])} | |")
    dst = DIR / "FINDINGS.md"
    dst.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  → {dst}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="_e2e_<tag>.json 의 태그")
    ap.add_argument("--md", action="store_true", help="FINDINGS.md 도 쓴다")
    a = ap.parse_args()
    run(a.tag, a.md)
