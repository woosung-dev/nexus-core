# 위키 검증 — 인용이 원문에 실재하는가 + 형식 규약을 지켰는가. API 호출 0, 읽기 전용.
#
# 대조는 **앵커가 가리키는 raw 안에서만** 한다.
#   전체 뭉치에 대조하면 앵커를 잘못 단 인용이 통과한다 — golden 에서 실측된 함정이다
#   (`_draft.py:246-252`: gid 216 이 선별에 없던 제40조를 인용했는데 다른 조문 본문에 앞 6자가
#    우연히 걸렸다).
#
# 정규화는 `_common.squash` — NFC + 숫자·한글 공백 + 전체 공백 제거.
# pdftotext 가 줄바꿈 자리에 공백을 넣기 때문에 공백을 남기면 멀쩡한 인용이 거짓 불일치로 떨어진다.
#
# 사용:
#   python3 _verify.py --bot 11                 # 전체
#   python3 _verify.py --bot 11 --ingested      # ingest 성공한 소스만 커버리지 판정
import argparse
import json
import re
import sys
from pathlib import Path

from _common import BOTS, load_sources, squash

SECTIONS = ["요약", "사실", "모순", "문서에 없음", "관련", "근거 좌표"]
# 앵커가 반드시 있어야 하는 섹션. 요약은 아래 사실의 압축이라 면제(AGENTS.md §1-①).
ANCHORED = {"사실", "모순", "문서에 없음"}

_ANCHOR = re.compile(r"\[\[src:\s*([a-z]+-\d+)\s*\]\]")
_PAGELINK = re.compile(r"\[\[page:\s*([^\]]+?)\s*\]\]")
_FM = re.compile(r"^---\n(.*?)\n---\n+(.*)", re.S)


def parse_page(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = _FM.match(raw)
    if not m:
        return {"path": path, "error": "프론트매터 없음"}
    head = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
    body = m.group(2)

    # 섹션 분해 — "## 제목" 부터 다음 "## " 직전까지
    sections, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    return {"path": path, "slug": head.get("slug", path.stem), "head": head,
            "sections": {k: "\n".join(v) for k, v in sections.items()}, "body": body}


def check_quotes(page: dict, units: dict) -> list[dict]:
    """`>` 인용을 **바로 위 항목의 앵커**가 가리키는 원문에서만 찾는다.

    한 항목에 앵커가 여럿이면 그중 하나에만 있으면 통과다(근거가 둘 이상인 문장).
    """
    bad = []
    anchors: list[str] = []
    for line in page["body"].splitlines():
        s = line.strip()
        if s.startswith(">"):
            quote = s.lstrip("> ").strip()
            if not quote:
                continue
            if not anchors:
                bad.append({"quote": quote[:60], "reason": "앵커 없는 인용"})
                continue
            sq = squash(quote)
            hit = any(sq in squash(units[a]["text"]) for a in anchors if a in units)
            unknown = [a for a in anchors if a not in units]
            if not hit:
                bad.append({"quote": quote[:60], "anchors": anchors,
                            "reason": "원문에 없음" + (f" · 모르는 앵커 {unknown}" if unknown else "")})
        elif found := _ANCHOR.findall(s):
            anchors = found          # 새 항목의 앵커로 교체
        elif not s:
            anchors = []             # 빈 줄이면 항목이 끝난 것으로 본다
    return bad


def check_format(page: dict) -> list[str]:
    errs = []
    missing = [s for s in SECTIONS if s not in page["sections"]]
    if missing:
        errs.append(f"섹션 누락 {missing}")
    for name in ANCHORED & set(page["sections"]):
        for line in page["sections"][name].splitlines():
            s = line.strip()
            # 항목 줄(- 로 시작)만 본다. 인용(>)·소제목(###)·빈 줄은 제외.
            if s.startswith("- ") and not _ANCHOR.search(s):
                errs.append(f"[{name}] 앵커 없는 항목: {s[:50]}")
    # 본문에 조문번호가 새어나왔는가 (AGENTS.md §1-⑤). 앵커·근거 좌표는 제외한다.
    for name in ("요약", "사실", "모순", "문서에 없음"):
        if name not in page["sections"]:
            continue
        for line in page["sections"][name].splitlines():
            s = _ANCHOR.sub("", line)
            if s.strip().startswith(">"):
                continue             # 인용은 원문이라 조문번호가 들어 있어도 된다
            if re.search(r"제\s*\d+\s*조", s):
                errs.append(f"[{name}] 본문에 조문번호: {s.strip()[:50]}")
    return errs


def main(bot: int, ingested_only: bool) -> None:
    bot_dir = BOTS / str(bot)
    units = load_sources(bot)
    pages_dir = bot_dir / "wiki" / "pages"
    pages = sorted(pages_dir.glob("*.md")) if pages_dir.exists() else []
    if not pages:
        sys.exit(f"페이지 없음: {pages_dir}")

    slugs, total_q, bad_q, fmt_errs = set(), 0, 0, 0
    used, links = set(), set()
    print(f"페이지 {len(pages)}쪽\n")
    for p in pages:
        pg = parse_page(p)
        if pg.get("error"):
            print(f"✗ {p.name} — {pg['error']}")
            fmt_errs += 1
            continue
        slugs.add(pg["slug"])
        used |= set(_ANCHOR.findall(pg["body"]))
        links |= set(_PAGELINK.findall(pg["body"]))
        nq = sum(1 for ln in pg["body"].splitlines() if ln.strip().startswith(">"))
        total_q += nq
        bq, fe = check_quotes(pg, units), check_format(pg)
        bad_q += len(bq)
        fmt_errs += len(fe)
        mark = "✓" if not bq and not fe else "✗"
        print(f"{mark} {pg['slug']} — 인용 {nq}건 · 앵커 {len(set(_ANCHOR.findall(pg['body'])))}종")
        for b in bq:
            print(f"    인용 불일치 [{b['reason']}] {b.get('anchors', '')} {b['quote']!r}")
        for e in fe:
            print(f"    형식 {e}")

    # 커버리지 — ingest 한 소스가 페이지에 실제로 실렸는가
    state_p = bot_dir / "_ingest_state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {}
    scope = {s for s, v in state.items() if v.get("ok")} if ingested_only else set(units)
    uncovered = sorted(scope - used, key=lambda s: (s.split("-")[0], int(s.split("-")[1])))
    dangling = sorted(links - slugs)

    print(f"\n인용 대조 {total_q - bad_q}/{total_q}"
          + (f" · 불일치 {bad_q}건" if bad_q else " (100%)"))
    print(f"형식 위반 {fmt_errs}건")
    print(f"소스 커버리지 {len(scope) - len(uncovered)}/{len(scope)}"
          + (f" · 미수록 {uncovered}" if uncovered else ""))
    print(f"교차참조 {len(links)}건 · 아직 없는 페이지를 가리킴 {len(dangling)}건 {dangling[:8]}")

    ok = bad_q == 0 and fmt_errs == 0 and not uncovered
    print(f"\n종합: {'통과' if ok else '⚠ 확인 필요'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", type=int, default=11)
    ap.add_argument("--ingested", action="store_true", help="ingest 성공분만 커버리지 판정")
    a = ap.parse_args()
    main(a.bot, a.ingested)
