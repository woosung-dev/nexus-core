# 용어집 `근거` 조문 ↔ 규정집 본문 대조 — API 호출 0, 읽기 전용.
#
# 선행 세션이 이 대조를 손으로 돌려 "15건 불일치, 그중 5건 오연결"을 냈다. 그 로직을 스크립트로
# 고정하되 버그 하나를 고쳤다.
#
# ── 고친 버그 ─────────────────────────────────────────────────────────────
# 조문 경계를 `re.M` 의 `^제N조(...)` 로 잡으면 99개 중 94개만 잡힌다.
# `pdftotext` 가 페이지 경계에 폼피드(\f, _reg.txt 에 63개)를 넣는데, 그 뒤에 오는 조문
# 머리글은 줄바꿈이 앞에 없어서 `^` 에 안 걸린다. 누락되는 조문이 39·83·88·89·90 이고
# 여기에 **제88조(추모예배와 사후양육)** 가 들어 있다 — 이번 수리의 정답 조문 중 하나다.
# 자를 안 고치면 114 추모예배를 제88조로 고쳐도 "여전히 불일치"로 나온다.
#
# 그래서 조문 추출 결과가 99개·결번 0 이 아니면 판정하지 않고 즉시 중단한다.
# ──────────────────────────────────────────────────────────────────────────
#
# 판정 규칙: 용어의 `source_articles` 가 가리키는 조문들 중 **하나라도** 그 본문에
# 용어명 또는 별칭 문자열이 있으면 통과. 전부 없으면 불일치.
# 불일치 = 곧바로 오류가 아니다. 문자열만 없고 내용은 맞는 경우가 10건 있다(핸드오프 §3-1).
# 이 스크립트는 후보를 좁혀 줄 뿐이고, 오연결 판정은 사람이 조문 표제를 보고 한다.
#
# 사용:
#   python3 _xcheck.py                                  # v1(원본 ETL 산출물)
#   python3 _xcheck.py --glossary _glossary_terms_v2.json
#   python3 _xcheck.py --glossary _glossary_terms_v2.json --baseline _xcheck_v1.json
import argparse
import json
import re
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
STEER = DIR.parent / "glossary_steering_2026-08-04"
ABLAT = DIR.parent / "branch_ablation_2026-08-04"

REG = STEER / "_reg.txt"                       # 규정집 2026 전문 (pdftotext -layout)
TITLES = STEER / "_article_titles.json"        # 조문 표제 99개 (결번 0)
DEFAULT_GLOSSARY = ABLAT / "_glossary_terms.json"

EXPECT_ARTICLES = 99

# 폼피드·캐리지리턴 뒤도 줄머리로 인정한다. 앞의 들여쓰기(제88조는 한 칸 들여쓰여 있다)도 허용.
_HDR = re.compile(r"(?:^|(?<=[\f\r]))[ \t]*제\s*(\d+)\s*조\s*\(([^)]*)\)", re.M)
_RANGE = re.compile(r"^제(\d+)~(\d+)조$")
_SINGLE = re.compile(r"^제(\d+)조$")
# pdftotext 는 숫자와 한글 사이에 공백을 넣는다("2 세가정 편성", "40 일수련"). AGENTS.md §5.
_DIGIT_KO = re.compile(r"(\d)\s+(?=[가-힣])")


def norm(s: str) -> str:
    """NFC 정규화 + 숫자·한글 사이 공백 제거 + 전체 공백 제거.

    RAG 파일명·본문에 NFD/NFC 가 섞여 있어 정규화 없이 비교하면 거짓음성이 난다(AGENTS.md §5).
    """
    s = unicodedata.normalize("NFC", s or "")
    prev = None
    while prev != s:                          # "3 일 행사" 처럼 연쇄된 경우까지
        prev = s
        s = _DIGIT_KO.sub(r"\1", s)
    return re.sub(r"\s+", "", s)


def load_bodies():
    """조문 번호 → 본문. 다음 조문 머리글 직전까지를 그 조문의 본문으로 본다."""
    reg = REG.read_text(encoding="utf-8")
    marks = [(m.start(), int(m.group(1)), m.group(2)) for m in _HDR.finditer(reg)]

    bodies, seen_titles = {}, {}
    for i, (pos, num, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(reg)
        bodies[num] = bodies.get(num, "") + reg[pos:end]
        seen_titles.setdefault(num, title)

    missing = [n for n in range(1, EXPECT_ARTICLES + 1) if n not in bodies]
    extra = [n for n in bodies if not 1 <= n <= EXPECT_ARTICLES]
    if missing or extra or len(bodies) != EXPECT_ARTICLES:
        raise SystemExit(
            f"⚠ 조문 추출 실패 — {len(bodies)}개 (기대 {EXPECT_ARTICLES}) "
            f"결번={missing} 범위밖={extra}\n"
            f"   경계 정규식이 폼피드를 못 넘고 있을 수 있다. 자가 고장난 채로 판정하지 않는다.")

    # 표제까지 대조해 조문 번호가 밀리지 않았음을 확인한다.
    ref = json.loads(TITLES.read_text(encoding="utf-8"))
    bad = [n for n in sorted(bodies) if norm(seen_titles[n]) != norm(ref[str(n)])]
    if bad:
        raise SystemExit(f"⚠ 조문 표제 불일치 {len(bad)}건: {bad[:10]} — _article_titles.json 과 어긋난다")

    return bodies, ref


def expand(arts):
    """`제86~87조` → [86, 87]. 예상 밖 표기는 (None, 원문) 으로 남긴다."""
    nums, unknown = [], []
    for a in arts:
        a = (a or "").strip()
        if not a:
            continue
        m = _RANGE.match(a)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            nums += list(range(lo, hi + 1))
            continue
        m = _SINGLE.match(a)
        if m:
            nums.append(int(m.group(1)))
            continue
        unknown.append(a)
    return nums, unknown


def check(glossary_path, bodies, titles):
    g = json.loads(Path(glossary_path).read_text(encoding="utf-8"))
    rows, no_articles = [], []
    for t in g["terms"]:
        nums, unknown = expand(t["source_articles"])
        if not nums:
            no_articles.append(t["no"])
            continue
        keys = [k for k in [t["term"]] + list(t.get("aliases") or []) if k]
        hit = None
        for n in nums:
            body = norm(bodies.get(n, ""))
            for k in keys:
                if norm(k) in body:
                    hit = (n, k)
                    break
            if hit:
                break
        if hit is None:
            rows.append({
                "no": t["no"], "term": t["term"], "aliases": t.get("aliases") or [],
                "source_articles": t["source_articles"],
                "targets": [{"no": n, "title": titles[str(n)]} for n in nums],
                "unknown_tokens": unknown,
            })
    return g, rows, no_articles


def main(glossary, baseline, out):
    bodies, titles = load_bodies()
    print(f"조문 추출 {len(bodies)}/{EXPECT_ARTICLES} · 결번 0 · 표제 대조 일치")

    g, rows, no_articles = check(glossary, bodies, titles)
    print(f"용어집 {Path(glossary).name} — {g['count']}개 "
          f"(근거 조문 없는 항목 {len(no_articles)}개)\n")

    print(f"문자열 불일치 {len(rows)}건")
    for r in rows:
        tgt = " / ".join(f"제{t['no']}조({t['title']})" for t in r["targets"])
        print(f"  {r['no']:>3} {r['term']:<14} {'·'.join(r['source_articles']):<16} → {tgt}")

    if baseline:
        base = {x["no"] for x in json.loads(Path(baseline).read_text(encoding="utf-8"))["mismatch"]}
        now = {x["no"] for x in rows}
        gone, new = sorted(base - now), sorted(now - base)
        print(f"\n기준({Path(baseline).name}) 대비 — 사라진 항목 {gone} · 새로 생긴 항목 {new}")
        if new:
            print("  ⚠ 새로 생긴 항목이 있다. 롤백하고 대조 로직을 먼저 고친다(핸드오프 §6).")

    p = DIR / out
    p.write_text(json.dumps({
        "glossary": str(Path(glossary)), "term_count": g["count"],
        "articles_parsed": len(bodies), "mismatch_count": len(rows), "mismatch": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {p}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--glossary", default=str(DEFAULT_GLOSSARY))
    ap.add_argument("--baseline", default="")
    ap.add_argument("--out", default="_xcheck.json")
    a = ap.parse_args()
    main(a.glossary, a.baseline, a.out)
