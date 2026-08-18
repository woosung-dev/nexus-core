# golden 정답지의 재료(코퍼스)를 만든다 — API 호출 0, 읽기 전용.
#
# 왜 새로 만드나 —
#   디스크의 `glossary_steering_2026-08-04/_reg.txt` 는 **v19** 다. v20 에서 제38조가 신설돼
#   그 뒤 62개 조문 번호가 +1 밀렸다(RAG_SWAP_REVIEW.md §1). v19 기준으로 golden 을 만들면
#   근거 조문이 통째로 어긋난다. 자를 먼저 v20 으로 갈아야 한다.
#
# 조문 경계 정규식은 `glossary_repair_2026-08-05/_xcheck.py` 에서 그대로 가져왔다.
#   `re.M` 의 `^제N조(...)` 만 쓰면 폼피드(\f) 뒤 조문 머리글이 `^` 에 안 걸려 5개를 놓친다.
#   그래서 추출 결과가 100개·결번 0 이 아니면 판정하지 않고 즉시 중단한다.
#
# 산출: _corpus/reg_v20.txt · articles_v20.json · glossary_v4.json · gongmun.json · shift_v19_v20.json
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
CORPUS = DIR / "_corpus"
ROOT = DIR.parent.parent
STEER = ROOT / "exports/glossary_steering_2026-08-04"
GONGMUN_DIR = ROOT / "exports/round3_redteam/03_RAG데이터"
DL = Path.home() / "Downloads"

REG_PDF = DL / "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf"
GLO_PDF = DL / "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf"

EXPECT_ARTICLES = 100  # v19 99 + 제38조(축복자녀 간 축복) 신설
MAX_TERM_CHARS = 3000  # 행정용어 1항목은 실측 300~440자. 넘으면 블록 경계가 샌 것이다.

# 폼피드·캐리지리턴 뒤도 줄머리로 인정한다. 들여쓰기 허용(제88조는 한 칸 들여쓰여 있다).
_HDR = re.compile(r"(?:^|(?<=[\f\r]))[ \t]*제\s*(\d+)\s*조\s*\(([^)]*)\)", re.M)
# pdftotext 는 숫자와 한글 사이에 공백을 넣는다("2 세가정 편성", "40 일수련").
_DIGIT_KO = re.compile(r"(\d)\s+(?=[가-힣])")


def tighten(s: str) -> str:
    """NFC 정규화 + 숫자·한글 사이 공백 제거. 인용 대조의 기준 형태."""
    return _DIGIT_KO.sub(r"\1", unicodedata.normalize("NFC", s))


def pdf_to_text(pdf: Path, out: Path) -> str:
    if not pdf.exists():
        sys.exit(f"원본 없음: {pdf}")
    subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True)
    return out.read_text(encoding="utf-8")


def split_articles(text: str) -> list[dict]:
    """조문 단위로 자른다. 각 조문은 다음 조문 머리글 직전까지."""
    hits = [(m.start(), int(m.group(1)), m.group(2).strip()) for m in _HDR.finditer(text)]
    out = []
    for i, (pos, num, title) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[pos:end].rstrip()
        out.append({"article": num, "title": title, "body": body, "chars": len(body)})
    return out


def build_regbook() -> list[dict]:
    text = pdf_to_text(REG_PDF, CORPUS / "reg_v20.txt")
    arts = split_articles(text)
    nums = [a["article"] for a in arts]
    missing = [i for i in range(1, max(nums) + 1) if i not in set(nums)]
    dupes = [n for n in set(nums) if nums.count(n) > 1]
    if len(arts) != EXPECT_ARTICLES or missing or dupes:
        sys.exit(f"조문 추출 실패 — {len(arts)}개 · 결번 {missing} · 중복 {dupes}. 판정 중단.")
    (CORPUS / "articles_v20.json").write_text(
        json.dumps(arts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"규정집 v20 — 조문 {len(arts)}개 · 결번 0 · 중복 0 · 본문 {sum(a['chars'] for a in arts):,}자")
    return arts


def build_shift_map(arts_v20: list[dict]) -> None:
    """v19 표제와 대조해 '+1 이동 62개'를 재확인한다.

    v19 인용이 섞여 들어올 때 어디로 옮겨야 하는지 알려주는 대조표이기도 하다.
    """
    old_path = STEER / "_article_titles.json"
    if not old_path.exists():
        print("v19 표제 없음 — 이동 대조 건너뜀")
        return
    raw = json.loads(old_path.read_text(encoding="utf-8"))
    v19 = {int(k): v for k, v in raw.items()} if isinstance(raw, dict) else \
          {int(x["article"]): x["title"] for x in raw}
    v20 = {a["article"]: a["title"] for a in arts_v20}

    same, shifted, unmatched = [], [], []
    for n, t in sorted(v19.items()):
        if v20.get(n) == t:
            same.append(n)
        elif v20.get(n + 1) == t:
            shifted.append({"v19": n, "v20": n + 1, "title": t})
        else:
            unmatched.append({"v19": n, "title": t, "v20_same_num": v20.get(n)})
    (CORPUS / "shift_v19_v20.json").write_text(json.dumps(
        {"unchanged": same, "shifted_plus1": shifted, "unmatched": unmatched},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v19→v20 대조 — 그대로 {len(same)} · +1 이동 {len(shifted)} · 미매칭 {len(unmatched)}")
    if unmatched:
        for u in unmatched[:10]:
            print(f"   미매칭 제{u['v19']}조 {u['title']!r} (v20 같은번호={u['v20_same_num']!r})")


def build_glossary() -> None:
    """대사전 v4 의 앞부분 행정용어만 뽑는다 (뒤 ~1,960쪽은 사상교리 대사전).

    v4 는 `근거 제N조` 필드를 의도적으로 삭제했다(147→0). 스키마에서 optional 로 둔다.
    """
    txt_path = CORPUS / "glossary_v4.txt"
    text = pdf_to_text(GLO_PDF, txt_path)
    # 머리글은 "행정 N <용어명>" 한 줄. 뒤이어 관련·기존 표기 / 항목체계 / 용어 설명 / 업무 참고.
    hdr = re.compile(r"(?:^|(?<=[\f\r\n]))[ \t]*행정\s*(\d+)[ \t]+(\S[^\n]*)", re.M)
    hits = [(m.start(), m.end(), int(m.group(1)), m.group(2).strip()) for m in hdr.finditer(text)]
    # 목차에도 같은 패턴이 나온다 → 본문 블록만 남긴다(뒤에 '용어 설명'이 있는 것).
    hits = [h for h in hits if "용어 설명" in text[h[1]:h[1] + 1200]]

    def field(block: str, key: str) -> str:
        m = re.search(rf"{key}\s+(.+?)(?=\n\s*\n|\n\s*(?:관련·기존 표기|항목체계|용어 설명|업무 참고)\b|\Z)",
                      block, re.S)
        return tighten(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""

    # 마지막 행정용어 뒤에는 대사전 3,455항목(약 300만자)이 이어진다. 경계를 닫지 않으면
    # 마지막 항목의 body 가 문서 전체를 삼킨다(실제로 행정 150 이 3,044,608자가 됐다).
    # 대사전 항목은 `0001 10·14 참부모님 천주축복결혼식` 처럼 4자리 일련번호로 시작한다.
    # 쪽번호는 뒤에 내용이 없어 이 패턴에 걸리지 않는다.
    tail = re.compile(r"(?:^|(?<=[\f\r\n]))[ \t]*\d{4}[ \t]+\S", re.M)
    m_tail = tail.search(text, hits[-1][0]) if hits else None
    doc_end = m_tail.start() if m_tail else len(text)

    items = []
    for i, (pos, _end_hdr, num, term) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else doc_end
        block = text[pos:end].rstrip()
        aliases = field(block, "관련·기존 표기")
        items.append({
            "no": num,
            "term": tighten(term),
            "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
            "category": field(block, "항목체계").split("자료 성격")[0].strip(),
            "definition": field(block, "용어 설명"),
            "note": field(block, "업무 참고"),
            "body": block,
        })
    nodef = [x["no"] for x in items if not x["definition"]]
    # 경계가 다시 새면 카드 생성 입력이 통째로 터진다 — 조용히 지나가지 않게 막는다.
    oversize = [(x["no"], len(x["body"])) for x in items if len(x["body"]) > MAX_TERM_CHARS]
    if oversize:
        sys.exit(f"행정용어 블록 경계 실패 — 과대 항목 {oversize}. 판정 중단.")
    (CORPUS / "glossary_v4.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"대사전 v4 행정용어 — {len(items)}건 · 정의 누락 {len(nodef)}건 {nodef[:10]} "
          f"· 최대 블록 {max(len(x['body']) for x in items):,}자")


def build_gongmun() -> None:
    # raw.txt 는 같은 공문의 OCR 원본이라 md 와 중복이다 — md 만 쓴다.
    docs = []
    for p in sorted(GONGMUN_DIR.glob("*.md")):
        if p.name.startswith(("누락공문", "추가자료")):
            continue
        docs.append({"name": p.name, "body": p.read_text(encoding="utf-8")})
    (CORPUS / "gongmun.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"공문 — {len(docs)}건: " + ", ".join(d["name"] for d in docs))


if __name__ == "__main__":
    CORPUS.mkdir(parents=True, exist_ok=True)
    arts = build_regbook()
    build_shift_map(arts)
    build_glossary()
    build_gongmun()
