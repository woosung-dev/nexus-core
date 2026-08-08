# 실제 위키 산출물 → 관리자 화면 데이터(wiki.ts · sources.ts). API 호출 0.
#
# 왜 이 단계가 있나 —
#   화면이 읽던 `wiki.ts` 는 사람이 손으로 쓴 상수였다(핸드오프 §14). 그래서 화면 숫자가
#   파이프라인 산출물과 달랐고, 봇 11 에 없는 공문이 근거로 달려 있었다.
#   DB 적재(_load.py)는 아직이므로, 그 전에 **파일 → TS** 로 직결해 화면을 실데이터로 확인한다.
#
# 이건 임시 다리다. 6단계에서 DB 적재로 바뀌면 이 스크립트는 버린다.
#
# 사용: python3 exports/wiki_2026-08/_gen_admin.py --bot 11
import argparse
import json
import re
import sys
from pathlib import Path

from _common import BOTS, load_sources

DIR = Path(__file__).parent
ROOT = DIR.parent.parent
OUT = ROOT / "frontend-admin/src/features/llm-wiki"

_ANCHOR = re.compile(r"\[\[src:\s*([a-z]+-\d+)\s*\]\]")
_PAGELINK = re.compile(r"\[\[page:\s*([^\]]+?)\s*\]\]")
_FM = re.compile(r"^---\n(.*?)\n---\n+(.*)", re.S)


def j(v) -> str:
    """TS 리터럴로 안전하게 — 한글은 이스케이프하지 않는다."""
    return json.dumps(v, ensure_ascii=False)


STUB_BANNER = """\
/**
 * LLM 위키 — **빈 껍데기다. 실데이터가 아니다.**
 *
 * 채우려면: python3 exports/wiki_2026-08/_gen_admin.py --bot 11
 *   (원본 PDF 2종 + ingest 산출물이 로컬에 있어야 한다)
 *
 * 왜 비어 있나 — 이 레포는 public 이고, 실데이터에는 규정집 v20(승인 전 개정초안,
 * "초안 조문번호의 대외 인용 금지")과 대사전 v4(사용 승인 미결) 전문이 들어간다.
 * 커밋되면 되돌릴 수 없어 껍데기만 둔다. 빌드는 이 파일로 통과한다.
 */
"""


def write_stub(bot: int) -> None:
    (OUT / "sources.ts").write_text(STUB_BANNER + """
export const CORPUS = { articles: 0, glossary: 0, gongmun: 0, ingested: 0 }

export type SourceKind = "reg" | "glo" | "gm" | "obs"

export type RawSource = { id: string; doc: string; kind: SourceKind; locator: string; \
/** 레포 기준 실제 파일 경로 */ file: string; quote: string }

export const SOURCES: RawSource[] = []
""", encoding="utf-8")

    (OUT / "wiki.ts").write_text(STUB_BANNER + """
export type Claim = {
  text: string
  /** 이 문장을 뒷받침하는 raw 소스 id. 비면 '근거 없음'으로 표시된다. */
  refs: string[]
  /** 원문에서 그대로 복사한 구간. _verify.py 가 raw 와 대조해 통과한 것만 실린다. */
  quote: string
  /** 이 문장이 모순 안에 있으면 모순 id */
  conflict?: string
}

export type WikiPage = {
  slug: string
  title: string
  category: string
  /** 이 페이지가 참조하는 다른 위키 페이지 slug */
  links: string[]
  summary: string
  claims: Claim[]
  /** 이 페이지를 만든 소스들 */
  updated: string
  /** 레포 기준 실제 파일 경로 */
  file: string
}

export type Conflict = {
  id: string
  title: string
  /** 서로 다른 말을 하는 쪽들 */
  sides: { label: string; says: string; ref: string }[]
  impact: string
  page: string
  status: "미해결" | "확인 요청됨"
}

export type Gap = {
  id: string
  title: string
  detail: string
  page: string
  /** 이 질문을 띄운 소스 */
  hits: string
}

export const PAGES: WikiPage[] = []
export const CONFLICTS: Conflict[] = []
export const GAPS: Gap[] = []
export const LOG: { date: string; op: string; title: string; detail: string }[] = []
""", encoding="utf-8")
    print(f"스텁 기록 — wiki.ts · sources.ts (봇 {bot} · 빈 데이터). 커밋용이다.")


def parse_page(path: Path) -> dict:
    m = _FM.match(path.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"프론트매터 없음: {path}")
    head = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
    secs, cur = {}, None
    for line in m.group(2).splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return {"head": head, "secs": secs, "slug": head.get("slug", path.stem), "path": path}


def items(lines: list[str]) -> list[dict]:
    """`- 문장 [[src: x]]` + 뒤따르는 `> 인용` 을 항목으로 묶는다."""
    out, cur = [], None
    for line in lines:
        t = line.strip()
        if t.startswith("### "):
            out.append({"sub": t[4:], "text": "", "refs": [], "quote": ""})
            cur = None
        elif t.startswith("- "):
            body = t[2:]
            cur = {"sub": "", "text": _ANCHOR.sub("", body).strip(),
                   "refs": _ANCHOR.findall(body), "quote": ""}
            out.append(cur)
        elif t.startswith(">") and cur:
            cur["quote"] += ("\n" if cur["quote"] else "") + re.sub(r"^>\s?", "", t)
    return out


def main(bot: int, stub: bool = False) -> None:
    """stub=True 면 타입만 있는 빈 파일을 쓴다 — 커밋용.

    이 레포는 public 이고 규정집 v20 은 승인 전 개정초안, 대사전 v4 는 사용 승인 미결이다.
    두 파일에는 그 전문이 들어가므로 **실데이터를 커밋하면 안 된다.**
    그렇다고 파일을 지우면 Vercel 의 frontend-admin 빌드가 깨진다(import 가 안 풀린다).
    그래서 빈 껍데기를 커밋하고, 각자 로컬에서 인자 없이 돌려 실데이터를 채운다.
    """
    if stub:
        write_stub(bot)
        return

    bot_dir = BOTS / str(bot)
    units = load_sources(bot)
    state = json.loads((bot_dir / "_ingest_state.json").read_text(encoding="utf-8"))
    ingested = [s for s, v in state.items() if v.get("ok")]
    pages = [parse_page(p) for p in sorted((bot_dir / "wiki" / "pages").glob("*.md"))]
    manifest = json.loads((bot_dir / "manifest.json").read_text(encoding="utf-8"))

    # ── sources.ts — ingest 한 소스만. quote 는 원문 전문 그대로. ────────────
    counts = {s["prefix"]: s["count"] for s in manifest["sources"]}
    rows = []
    for sid in sorted(ingested, key=lambda s: (s.split("-")[0], int(s.split("-")[1]))):
        u = units[sid]
        rows.append(f'  {{ id: {j(sid)}, doc: {j(u["doc"])}, kind: {j(u["src_id"].split("-")[0])}, '
                    f'locator: {j(u["locator"])}, file: {j(str(u["path"].relative_to(ROOT)))}, '
                    f'quote: {j(u["text"])} }},')
    (OUT / "sources.ts").write_text(f"""\
/**
 * LLM 위키 — raw 층. **이 파일은 생성물이다. 손으로 고치지 마라.**
 *   생성: exports/wiki_2026-08/_gen_admin.py --bot {bot}
 *   원본: exports/wiki_2026-08/sources/<sha8>/*.md (규정집 v20 · 대사전 v4 에서 분해)
 *
 * quote 는 원문 전문 그대로다. 요약·재작성하지 않았다.
 * 여기 실린 것은 **실제로 ingest 한 소스뿐**이다 — 전체 raw {sum(counts.values())}건 중 {len(ingested)}건.
 */

export const CORPUS = {{
  articles: {counts.get("reg", 0)},
  glossary: {counts.get("glo", 0)},
  gongmun: 0, // 봇 {bot} 은 공문을 갖고 있지 않다 (규정집 v20 + 대사전 v4 두 건뿐)
  ingested: {len(ingested)},
}}

export type SourceKind = "reg" | "glo" | "gm" | "obs"

export type RawSource = {{ id: string; doc: string; kind: SourceKind; locator: string; /** 레포 기준 실제 파일 경로 */ file: string; quote: string }}

export const SOURCES: RawSource[] = [
{chr(10).join(rows)}
]
""", encoding="utf-8")

    # ── wiki.ts — 페이지·모순·공백·기록 ─────────────────────────────────────
    page_src = []
    conflicts, gaps = [], []
    for p in pages:
        s, secs = p["slug"], p["secs"]
        claims = []
        for it in items(secs.get("사실", [])):
            if it["sub"]:
                continue
            claims.append(f'      {{ text: {j(it["text"])}, refs: {j(it["refs"])}, '
                          f'quote: {j(it["quote"])} }},')

        # `## 모순` — 소제목(###) 아래 항목들이 서로 다른 말을 하는 쪽들이다.
        cur_title = None
        for it in items(secs.get("모순", [])):
            if it["sub"]:
                cur_title = it["sub"]
                conflicts.append({"id": f"c-{s}-{len(conflicts)}", "title": cur_title,
                                  "page": s, "sides": [], "impact": ""})
                continue
            if not conflicts:
                continue
            if it["text"].startswith("영향:"):
                conflicts[-1]["impact"] = it["text"][3:].strip()
            else:
                conflicts[-1]["sides"].append(
                    {"label": ", ".join(it["refs"]) or "근거 없음",
                     "says": it["text"], "ref": it["refs"][0] if it["refs"] else ""})

        for it in items(secs.get("문서에 없음", [])):
            if it["sub"]:
                continue
            # detail 은 위키에 없는 필드다. 지어내지 말고 이 질문을 띄운 소스의 실제 위치를 적는다.
            where = " · ".join(units[r]["locator"] for r in it["refs"] if r in units)
            gaps.append({"id": f"g-{s}-{len(gaps)}", "title": it["text"], "page": s,
                         "detail": f"{where} 를 읽다 남긴 질문이다. 문서가 여기까지만 말하므로 "
                                   f"위키는 추정으로 채우지 않았다." if where
                                   else "근거 소스가 표시되지 않은 질문이다.",
                         "hits": ", ".join(it["refs"]) or "근거 없음"})

        links = [x for x in _PAGELINK.findall("\n".join(secs.get("관련", [])))]
        summary = "\n".join(secs.get("요약", [])).strip()
        page_src.append(f"""\
  {{
    slug: {j(s)},
    title: {j(p["head"].get("title", s))},
    category: {j(p["head"].get("category", "미분류"))},
    links: {j(links)},
    summary: {j(summary)},
    updated: {j(p["head"].get("sources", "").strip("[]").replace(",", " ·"))},
    file: {j(str(p["path"].relative_to(ROOT)))},
    claims: [
{chr(10).join(claims)}
    ],
  }},""")

    def block(rows_: list[dict], keys: list[str]) -> str:
        return "\n".join(
            "  { " + ", ".join(f"{k}: {j(r[k])}" for k in keys if k != "sides")
            + (", sides: [" + ", ".join(
                "{ " + ", ".join(f"{k}: {j(v)}" for k, v in side.items()) + " }"
                for side in r["sides"]) + "]" if "sides" in keys else "")
            + ", status: \"미해결\" }," if "sides" in keys else
            "  { " + ", ".join(f"{k}: {j(r[k])}" for k in keys) + " },"
            for r in rows_)

    log_rows = []
    for blk in (bot_dir / "wiki" / "log.md").read_text(encoding="utf-8").split("\n## ")[1:]:
        head_line = blk.splitlines()[0]
        m = re.match(r"\[(.+?)\]\s+(\w+)\s+\|\s+(.+)", head_line)
        detail = next((l[2:] for l in blk.splitlines() if l.startswith("- ")), "")
        if m:
            log_rows.append(f'  {{ date: {j(m.group(1))}, op: {j(m.group(2))} as const, '
                            f'title: {j(m.group(3).strip())}, detail: {j(detail)} }},')

    (OUT / "wiki.ts").write_text(f"""\
/**
 * LLM 위키 — wiki 층. **이 파일은 생성물이다. 손으로 고치지 마라.**
 *   생성: exports/wiki_2026-08/_gen_admin.py --bot {bot}
 *   원본: exports/wiki_2026-08/bots/{bot}/wiki/pages/*.md (codex 가 ingest 로 쓴 것)
 *
 * 카파시 llm-wiki 패턴의 가운데 층. LLM 이 raw 를 읽고 쓰고, 사람은 읽고 판정만 한다.
 * 모든 claim 은 raw 소스 id 를 물고 있다 — 출처 없는 문장은 위키에 남기지 않는다.
 * https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
 *
 * 인용 대조 {sum(1 for p in pages for it in items(p["secs"].get("사실", [])) if it["quote"])}건 전부 원문 실재 확인됨(_verify.py).
 */

export type Claim = {{
  text: string
  /** 이 문장을 뒷받침하는 raw 소스 id. 비면 '근거 없음'으로 표시된다. */
  refs: string[]
  /** 원문에서 그대로 복사한 구간. _verify.py 가 raw 와 대조해 통과한 것만 실린다. */
  quote: string
  /** 이 문장이 모순 안에 있으면 모순 id */
  conflict?: string
}}

export type WikiPage = {{
  slug: string
  title: string
  category: string
  /** 이 페이지가 참조하는 다른 위키 페이지 slug */
  links: string[]
  summary: string
  claims: Claim[]
  /** 이 페이지를 만든 소스들 */
  updated: string
  /** 레포 기준 실제 파일 경로 */
  file: string
}}

export type Conflict = {{
  id: string
  title: string
  /** 서로 다른 말을 하는 쪽들 */
  sides: {{ label: string; says: string; ref: string }}[]
  impact: string
  page: string
  status: "미해결" | "확인 요청됨"
}}

export type Gap = {{
  id: string
  title: string
  detail: string
  page: string
  /** 이 질문을 띄운 소스 */
  hits: string
}}

export const PAGES: WikiPage[] = [
{chr(10).join(page_src)}
]

/** 아직 0건이다. 소스 {len(ingested)}건 범위에서는 문서 내 상충이 잡히지 않았다. */
export const CONFLICTS: Conflict[] = [
{block(conflicts, ["id", "title", "impact", "page", "sides"])}
]

export const GAPS: Gap[] = [
{block(gaps, ["id", "title", "detail", "page", "hits"])}
]

/** log.md — append-only. 카파시 로그 규약(`## [날짜] 동작 | 제목`)을 그대로 쓴다. */
export const LOG = [
{chr(10).join(log_rows)}
]
""", encoding="utf-8")

    nq = sum(1 for p in pages for it in items(p["secs"].get("사실", [])) if it["quote"])
    print(f"wiki.ts   페이지 {len(pages)}쪽 · 문장 "
          f"{sum(len(items(p['secs'].get('사실', []))) for p in pages)}개 · 인용 {nq}건 "
          f"· 모순 {len(conflicts)} · 공백 {len(gaps)}")
    print(f"sources.ts raw {len(rows)}건 (ingest 완료분만) · 코퍼스 조문 {counts.get('reg',0)}"
          f" · 용어 {counts.get('glo',0)} · 공문 0")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", type=int, default=11)
    ap.add_argument("--stub", action="store_true", help="커밋용 빈 껍데기를 쓴다")
    a = ap.parse_args()
    main(a.bot, a.stub)
