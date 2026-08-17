# 용어집 PDF → 행정용어 레코드 추출 (ETL 초안).
#
# 원본 출처: R2 버킷. 업로드 엔드포인트가 원본을 R2에 저장하지만 키를 uuid4 로 랜덤화하고
# 매핑을 DB 에 남기지 않아(문서 테이블 없음) 파일명으로는 못 찾는다. 대신 Gemini store 의
# custom_metadata(content_sha256) 와 size 로 특정해 내려받고 sha256 으로 검증했다.
#
# PDF 구조 (pdftotext -layout 기준):
#   행정 <N> <용어명>
#   관련·기존 표기 <별칭…>        (선택)
#   항목체계 <분류> 근거 <조문…>
#   정의 <본문>
#   행정상 유의 <본문>            (선택)
#   검토상태 <본문>               (선택)
#
# 산출: PR #38 glossary_terms 스키마에 맞춘 JSON
#   {term, aliases[], definition, category, source_articles[], admin_note, review_status, no}
import argparse
import json
import re
import subprocess
from pathlib import Path

DIR = Path(__file__).parent

# "제 39~42 조", "제 3 조" → 공백 제거해 "제39~42조" 로 정규화
_SP_NUM = re.compile(r"제\s*(\d+)\s*(?:~\s*(\d+)\s*)?조")
_HEAD = re.compile(r"^행정\s+(\d{1,3})\s+(.+?)\s*$")
_FIELDS = ("관련·기존 표기", "항목체계", "정의", "행정상 유의", "검토상태", "관련 표기")
_NOISE = re.compile(r"^(세계평화통일가정연합 대사전|가정행복국 행정 용어 통합본|\d+)\s*$")


# pdftotext -layout 은 숫자와 한글 사이에 공백을 넣는다("2 세가정 편성", "40 일수련").
# 별칭은 사용자 입력과 문자열 매칭되어야 하므로 반드시 붙여야 한다.
_DIGIT_KO = re.compile(r"(\d)\s+([가-힣])")


def tighten(s: str) -> str:
    prev = None
    while prev != s:                       # "3 일 행사" 처럼 연쇄된 경우까지
        prev = s
        s = _DIGIT_KO.sub(r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_articles(s: str) -> list[str]:
    out = []
    for m in _SP_NUM.finditer(s or ""):
        out.append(f"제{m.group(1)}~{m.group(2)}조" if m.group(2) else f"제{m.group(1)}조")
    return out


def extract_text(pdf: Path, first: int, last: int) -> str:
    p = subprocess.run(["pdftotext", "-f", str(first), "-l", str(last), "-layout", str(pdf), "-"],
                       capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"pdftotext 실패: {p.stderr[:200]}")
    return p.stdout


def parse(text: str) -> list[dict]:
    lines = [ln.rstrip() for ln in text.splitlines()]
    entries, cur, field, buf = [], None, None, []

    def flush_field():
        nonlocal field, buf
        if cur is not None and field and buf:
            cur[field] = re.sub(r"\s+", " ", " ".join(buf)).strip()
        field, buf = None, []

    def flush_entry():
        nonlocal cur
        if cur:
            entries.append(cur)
        cur = None

    for ln in lines:
        s = ln.strip()
        if not s or _NOISE.match(s):
            continue
        h = _HEAD.match(s)
        if h:
            flush_field()
            flush_entry()
            cur = {"no": int(h.group(1)), "term": h.group(2).strip()}
            continue
        if cur is None:
            continue
        hit = next((f for f in _FIELDS if s.startswith(f)), None)
        if hit:
            flush_field()
            rest = s[len(hit):].strip()
            # "항목체계 교육 근거 제3조" → 분류와 근거를 분리
            if hit == "항목체계":
                m = re.split(r"\s*근거\s*", rest, maxsplit=1)
                cur["category"] = m[0].strip()
                if len(m) > 1:
                    cur["_articles_raw"] = m[1].strip()
                continue
            field = {"관련·기존 표기": "aliases_raw", "관련 표기": "aliases_raw",
                     "정의": "definition", "행정상 유의": "admin_note",
                     "검토상태": "review_status"}[hit]
            buf = [rest] if rest else []
        elif field:
            buf.append(s)
    flush_field()
    flush_entry()

    out = []
    for e in entries:
        al = e.pop("aliases_raw", "") or ""
        aliases = [a.strip() for a in re.split(r"[,、·/]|\s{2,}", al) if a.strip()]
        aliases = [a for a in aliases if a and a != "없음"]
        out.append({
            "no": e["no"], "term": tighten(e["term"]),
            "aliases": [tighten(a) for a in aliases],
            "definition": tighten(e.get("definition", "")),
            "category": tighten(e.get("category", "")),
            "source_articles": norm_articles(e.pop("_articles_raw", "")),
            "admin_note": tighten(e.get("admin_note", "")),
            "review_status": tighten(e.get("review_status", "")),
        })
    return out


def main(pdf, first, last, out_name, expect):
    text = extract_text(Path(pdf).expanduser(), first, last)
    rows = parse(text)
    rows.sort(key=lambda r: r["no"])

    nos = [r["no"] for r in rows]
    missing = [n for n in range(1, expect + 1) if n not in nos]
    dup = sorted({n for n in nos if nos.count(n) > 1})

    print(f"추출 {len(rows)}개 (기대 {expect})")
    if missing:
        print(f"  누락 번호: {missing}")
    if dup:
        print(f"  중복 번호: {dup}")
    print(f"  별칭 있음      {sum(1 for r in rows if r['aliases'])}/{len(rows)}")
    print(f"  근거 조문 있음  {sum(1 for r in rows if r['source_articles'])}/{len(rows)}")
    print(f"  정의 있음      {sum(1 for r in rows if r['definition'])}/{len(rows)}")
    print(f"  행정상 유의    {sum(1 for r in rows if r['admin_note'])}/{len(rows)}")
    print(f"  검토상태       {sum(1 for r in rows if r['review_status'])}/{len(rows)}")
    empty = [r["no"] for r in rows if not r["definition"]]
    if empty:
        print(f"  ⚠ 정의 비어있는 항목: {empty}")

    p = DIR / out_name
    p.write_text(json.dumps({"source": "세계평화통일가정연합 대사전 · 가정행복국 행정용어 통합본",
                             "pages": [first, last], "count": len(rows), "terms": rows},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {p}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=35)
    ap.add_argument("--expect", type=int, default=147)
    ap.add_argument("--out", default="_glossary_terms.json")
    a = ap.parse_args()
    main(a.pdf, a.first, a.last, a.out, a.expect)
