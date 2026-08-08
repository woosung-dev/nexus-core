# raw 층을 만든다 — 원본 PDF → 소스 단위 markdown 낱개. API 호출 0, 읽기 전용.
#
# raw 는 **불변**이다(카파시 llm-wiki 3층 중 1층). 에이전트는 여기를 절대 고치지 않고,
# `_verify.py` 가 위키 인용을 되짚을 때의 유일한 기준이 된다.
#
# 파싱을 새로 짜지 않는다 —
#   `golden_2026-08/_corpus_build.py` 가 이미 조문 100개·결번 0·중복 0 을 검증하고
#   실패하면 sys.exit 한다(:68). 대사전 꼬리 경계(4자리 일련번호)도 거기서 막는다(:129-131).
#   경계가 새면 마지막 항목 body 가 300만자가 되어 LLM 입력이 통째로 터진다.
#
# raw 는 **문서 단위로 공유**한다(봇 무관). 같은 규정집을 봇 11·8 이 함께 쓰므로
# sources/ 는 한 벌만 두고 위키만 봇별로 가른다.
#
# 사용: python3 exports/wiki_2026-08/_split.py
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = DIR.parent.parent
GOLDEN = ROOT / "exports/golden_2026-08"
CORPUS = GOLDEN / "_corpus"
SOURCES = DIR / "sources"
DL = Path.home() / "Downloads"

# 핸드오프 §2 에 박아 둔 값. 원본이 바뀌면 여기서 멈춘다 —
# 다른 판으로 위키를 만들면 봇이 실제로 검색하는 문서와 어긋난다.
DOCS = [
    {
        "prefix": "reg",
        "kind": "규정집",
        "doc": "규정집v20",
        "pdf": DL / "신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf",
        "sha256": "d8a5ef90e8036df9e8170d1f0bb3ccfcd3fc8b7f84fa251a2f0335cd4f5d5180",
        "size": 2062334,
        "corpus": "articles_v20.json",
        "expect": 100,
    },
    {
        "prefix": "glo",
        "kind": "대사전",
        "doc": "대사전v4",
        "pdf": DL / "세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf",
        "sha256": "93636bb2855357b61be3d80abe2f25fb407a9e29a07d577d7d0ef1d8b89ed12c",
        "size": 13867017,
        "corpus": "glossary_v4.json",
        "expect": 150,
    },
]

MAX_BLOCK_CHARS = 30000  # 제32조(40일 성별 및 정성기간)가 29,774자로 최대다. 넘으면 경계가 샌 것.


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_corpus() -> None:
    """`_corpus/*.json` 이 PDF 보다 새로우면 그대로 쓰고, 아니면 다시 만든다.

    `_corpus_build.py` 는 pdftotext 로 14MB PDF 를 두 번 훑어 1~2분 걸린다.
    이미 검증을 통과한 산출물이 있으면 재사용하는 편이 낫다.
    """
    paths = [CORPUS / d["corpus"] for d in DOCS]
    newest_pdf = max(d["pdf"].stat().st_mtime for d in DOCS)
    if all(p.exists() for p in paths) and min(p.stat().st_mtime for p in paths) > newest_pdf:
        print("코퍼스 재사용 — _corpus/*.json 이 원본보다 새롭다")
        return
    print("코퍼스 재생성 — _corpus_build.py 실행 (pdftotext 2회, 1~2분)")
    p = subprocess.run([sys.executable, str(GOLDEN / "_corpus_build.py")],
                       capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    if p.returncode != 0:
        sys.exit(f"_corpus_build.py 실패:\n{p.stderr[-800:]}")


def units(spec: dict) -> list[dict]:
    """코퍼스 JSON 을 소스 단위 [{no, locator, body}] 로 통일한다."""
    items = json.loads((CORPUS / spec["corpus"]).read_text(encoding="utf-8"))
    if spec["prefix"] == "reg":
        return [{"no": a["article"],
                 "locator": f"제{a['article']}조({a['title']})",
                 "body": a["body"]} for a in items]
    return [{"no": t["no"],
             "locator": f"행정 {t['no']} {t['term']}",
             "body": t["body"]} for t in items]


def write_source_dir(spec: dict) -> dict:
    sha8 = spec["sha256"][:8]
    out = SOURCES / sha8
    # raw 는 불변이라 갱신이 아니라 통째 교체다. 낱개가 섞이면 결번 판정이 무의미해진다.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    us = units(spec)
    nums = [u["no"] for u in us]
    missing = [i for i in range(1, max(nums) + 1) if i not in set(nums)]
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    oversize = [(u["no"], len(u["body"])) for u in us if len(u["body"]) > MAX_BLOCK_CHARS]
    if len(us) != spec["expect"] or missing or dupes or oversize:
        sys.exit(f"{spec['doc']} 분해 실패 — {len(us)}개 · 결번 {missing} · 중복 {dupes} "
                 f"· 과대 {oversize}. 판정 중단.")

    for u in us:
        src_id = f"{spec['prefix']}-{u['no']}"
        # 프론트매터가 인용을 되짚는 좌표다. `_verify.py` 는 앵커 [[src: reg-43]] 을
        # 여기 src_id 로 찾아 그 파일 **안에서만** quote 를 대조한다.
        # 전체 뭉치에 대조하면 앵커를 잘못 단 인용이 통과해 버린다(_draft.py:246-252 실측).
        (out / f"{u['no']:03d}.md").write_text(
            "---\n"
            f"src_id: {src_id}\n"
            f"doc: {spec['doc']}\n"
            f"sha8: {sha8}\n"
            f"locator: {u['locator']}\n"
            "---\n\n"
            f"{u['body']}\n",
            encoding="utf-8")

    meta = {
        "sha8": sha8,
        "sha256": spec["sha256"],
        "size": spec["size"],
        "kind": spec["kind"],
        "doc": spec["doc"],
        "display_name": spec["pdf"].name,
        "prefix": spec["prefix"],
        "count": len(us),
        "units": [{"src_id": f"{spec['prefix']}-{u['no']}",
                   "file": f"{u['no']:03d}.md",
                   "locator": u["locator"],
                   "chars": len(u["body"])} for u in us],
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(f"{spec['doc']} → sources/{sha8}/ — {len(us)}건 · 결번 0 · 중복 0 "
          f"· 본문 {sum(len(u['body']) for u in us):,}자 · 최대 {max(len(u['body']) for u in us):,}자")
    return meta


def main() -> None:
    for d in DOCS:
        if not d["pdf"].exists():
            sys.exit(f"원본 없음: {d['pdf']}")
        actual = sha256(d["pdf"])
        if actual != d["sha256"]:
            sys.exit(f"원본 sha256 불일치 — {d['pdf'].name}\n"
                     f"  기대 {d['sha256']}\n  실제 {actual}\n"
                     "다른 판으로 위키를 만들면 봇이 검색하는 문서와 어긋난다. 중단.")
        print(f"sha256 확인 — {d['pdf'].name[:44]} ✓")

    ensure_corpus()
    SOURCES.mkdir(parents=True, exist_ok=True)
    metas = [write_source_dir(d) for d in DOCS]
    total = sum(m["count"] for m in metas)
    print(f"\nraw {total}건 · sources/ {len(metas)}개 문서")


if __name__ == "__main__":
    main()
