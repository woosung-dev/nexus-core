# 근거 위반 감사 → 읽는 문서. `audit.json` 하나만 읽는다. API 호출 0.
#
# `_audit.py` 가 낸 판정을 사람이 읽는 형태로 편다 — 팔별 지어냄율(주표·부표),
# 문항별 위반 목록, 그리고 적대 검증이 되살린 주장들.
#
# 사용: python3 exports/wiki_eval/_audit_report.py
import html
import json
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR / "audit.json"
OUT = DIR / "audit_report.html"

# ── _audit.py:70-77 과 같은 것. 그 파일은 import 만 해도 backend 모듈·.env·위키 인덱스를
#    끌고 오므로 여기서는 세 상수와 summarize() 를 복사해 둔다 (숫자를 만드는 규칙은 동일).
ARMS = ["rag", "wiki", "wiki_budget", "wiki_first", "hybrid"]
ARM_LABEL = {
    "rag": "A · file_search",
    "wiki": "B · 위키→원문 24건",
    "wiki_budget": "B′ · 예산 3,000자",
    "wiki_first": "C · 위키 본문",
    "hybrid": "F · A + BM25 원문",
}
# 근거를 무엇으로 주느냐 — 팔 사이에서 다른 것은 이것 하나다 (_golden_report.py:21-30).
ARM_NOTE = {
    "rag": "Gemini file_search 가 스토어(PDF 2건)에서 검색한다. 현재 라이브 경로.",
    "wiki": "BM25 멀티스케일로 페이지를 고르고 그 페이지의 원문 전부를 넣는다(최대 24건).",
    "wiki_budget": "같은 검색기. 원문은 순위 상위 예산분만(3,000자·최대 8건·최소 4건).",
    "wiki_first": "카파시 원안. 위키 페이지 본문으로 답한다. 원문은 따로 넣지 않는다.",
    "hybrid": "file_search 를 그대로 돌리되 BM25 원문을 앞선 턴으로 함께 준다.",
}
LENS = {"a": "코퍼스 전수", "b": "표현 차이", "c": "조문 합성"}

ANSWER_CAP = 1600
TEXT_CAP = 400
QUOTE_CAP = 300
RESCUE_MAX = 8


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def clip(s, cap: int) -> str:
    """자르고 나서 escape 한다 — escape 후에 자르면 실체참조가 반토막 난다."""
    s = str(s if s is not None else "")
    return esc(s[:cap]) + ("…" if len(s) > cap else "")


def ratio(num: int, den: int) -> str:
    """숫자는 분모와 함께 (AGENTS.md §1)."""
    if not den:
        return f"{num}/0 (—)"
    return f"{num}/{den} ({100 * num / den:.1f}%)"


# ────────────────────────────────────────────────────────────── 집계 (_audit.py:663-697)

def summarize(state: dict) -> dict:
    cells = state["cells"]
    by_n = {}
    for cell in cells.values():
        by_n.setdefault(cell["n"], set()).add(cell["arm"])
    complete = {n for n, arms in by_n.items() if set(ARMS) <= arms}

    def agg(keys):
        out = {}
        for arm in ARMS:
            mine = [k for k in keys if cells[k]["arm"] == arm]
            claims = [c for k in mine for c in cells[k].get("claims", []) if "violation" in c]
            viol = [c for c in claims if c["violation"]]
            # 프롬프트 출처는 「규정에 없다」가 맞지만 지어낸 것과 성격이 다르다 — 나눠서 낸다
            fabricated = [c for c in viol if not c.get("in_prompt")]
            n_contra = sum(1 for c in claims if c.get("final") == "모순")
            out[arm] = {
                "cells": len(mine),
                "silent_cells": sum(1 for k in mine if not cells[k].get("claims")),
                "claims": len(claims),
                "violations": len(viol),
                "fabricated": len(fabricated),
                "from_prompt": len(viol) - len(fabricated),
                "contradictions": n_contra,
                "rate": round(100 * len(viol) / len(claims), 1) if claims else None,
                "fab_rate": round(100 * len(fabricated) / len(claims), 1) if claims else None,
                "per_cell": round(len(fabricated) / len(mine), 2) if mine else None,
            }
        return out

    return {
        "complete_questions": sorted(complete),
        "primary": agg([k for k, c in cells.items() if c["n"] in complete]),
        "all": agg(list(cells)),
    }


# ────────────────────────────────────────────────────────────── 표

def ranked(agg: dict) -> list:
    """지어냄율 오름차순. 잴 수 없는 팔(주장 0)은 끝으로."""
    return sorted(ARMS, key=lambda a: (agg[a]["fab_rate"] is None, agg[a]["fab_rate"] or 0))


def arm_table(agg: dict, caption: str = "") -> str:
    order = ranked(agg)
    best = order[0] if agg[order[0]]["fab_rate"] is not None else None
    worst = order[-1] if agg[order[-1]]["fab_rate"] is not None else None
    rows = []
    for arm in order:
        r = agg[arm]
        klass = "top" if arm == best else ("bad" if arm == worst else "")
        rate = ratio(r["fabricated"], r["claims"]) if r["claims"] else "—"
        rows.append(
            f'<tr class="{klass}"><th>{esc(ARM_LABEL[arm])}</th>'
            f'<td>{r["cells"]}</td>'
            f'<td>{ratio(r["silent_cells"], r["cells"])}</td>'
            f'<td>{r["claims"]}</td>'
            f'<td class=num>{r["fabricated"]}</td>'
            f'<td>{r["from_prompt"]}</td>'
            f'<td class="{"warn" if r["contradictions"] else ""}">{r["contradictions"]}</td>'
            f'<td class=num>{rate}</td>'
            f'<td>{r["per_cell"] if r["per_cell"] is not None else "—"}</td></tr>'
        )
    cap = f"<caption>{caption}</caption>" if caption else ""
    return f"""<div class=scroller><table class=rank>{cap}
<thead><tr><th>팔</th><th>셀</th><th>무주장셀</th><th>주장</th><th>지어냄</th>
<th>프롬프트출처</th><th>모순</th><th>지어냄율</th><th>셀당</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def conclusion_line(s: dict) -> str:
    """결론 한 줄 — 데이터에서 계산한다. 손으로 쓴 숫자는 하나도 없다."""
    agg = s["primary"]
    order = [a for a in ranked(agg) if agg[a]["fab_rate"] is not None]
    if not order:
        return "지어냄율을 잴 수 있는 팔이 없다 — 주장이 하나도 수집되지 않았다."
    lo, hi = order[0], order[-1]
    nq = len(s["complete_questions"])
    return (
        f"5팔 완비 {nq}문항에서 지어냄이 가장 적은 팔은 <b>{esc(ARM_LABEL[lo])} "
        f"{ratio(agg[lo]['fabricated'], agg[lo]['claims'])}</b>, 가장 많은 팔은 "
        f"<b>{esc(ARM_LABEL[hi])} {ratio(agg[hi]['fabricated'], agg[hi]['claims'])}</b> 다. "
        f"다만 그 최저 팔은 {ratio(agg[lo]['silent_cells'], agg[lo]['cells'])} 셀에서 "
        f"아무 사실 주장도 하지 않았고, 주장 총수도 {agg[lo]['claims']}건으로 "
        f"{esc(ARM_LABEL[hi])}({agg[hi]['claims']}건)보다 적다 — "
        f"<b>말을 적게 하면 지어낼 것도 적다.</b>"
    )


# ────────────────────────────────────────────────────────────── 문항별 위반

def why_of(c: dict):
    """판정 사유. ③ 대조가 사유를 비워 둔 경우 적대 검증 소견으로 대신한다."""
    r = (c.get("reason") or "").strip()
    if r:
        return "판정 사유", r
    for lens in ("a", "b", "c"):
        rr = (c.get("adv", {}).get(lens, {}) or {}).get("reason", "").strip()
        if rr:
            return f"적대검증 {LENS[lens]} 소견", rr
    return None


def claim_item(arm: str, c: dict) -> str:
    contra = c.get("final") == "모순"
    votes = c.get("adv_votes", 0)
    tags = [f'<span class="fin {"contra" if contra else "unsup"}">{esc(c.get("final"))}</span>',
            f"<span class=armtag>{esc(ARM_LABEL[arm])}</span>"]
    if c.get("in_prompt"):
        tags.append("<span class=src>프롬프트 출처</span>")
    tags.append(f"<span class=votes>적대검증 {votes}/3</span>")

    w = why_of(c)
    why = (f'<p class=why><span>{esc(w[0])}</span>{clip(w[1], TEXT_CAP)}</p>' if w else "")
    quote = ""
    if contra and (c.get("snap_text") or c.get("quote")):
        quote = (f'<p class=quote><span class=lbl>원문 {esc(c.get("snap_src") or c.get("src_id"))}</span>'
                 f'{clip(c.get("snap_text") or c.get("quote"), QUOTE_CAP)}</p>')
    return (f'<li class="claim{" contra" if contra else ""}">'
            f'<div class=cl-head>{"".join(tags)}</div>'
            f'<p class=cl-text>{clip(c["text"], TEXT_CAP)}</p>{quote}{why}</li>')


def question_block(n: int, question: str, items: list, cells: dict) -> str:
    contra = [(arm, c) for arm, c in items if c.get("final") == "모순"]
    rest = [(arm, c) for arm, c in items if c.get("final") != "모순"]

    blocks = []
    if contra:
        blocks.append(
            "<div class=contra-block><h4>모순 — 원문이 다르게 말한다</h4>"
            f'<ul class=claims>{"".join(claim_item(a, c) for a, c in contra)}</ul></div>'
        )
    for arm in ARMS:
        mine = [c for a, c in rest if a == arm]
        if not mine:
            continue
        cell = cells.get(f"{n}:{arm}", {})
        ans = clip(cell.get("answer"), ANSWER_CAP) or "<i>빈 응답</i>"
        blocks.append(
            f'<div class=arm-block><h4>{esc(ARM_LABEL[arm])} '
            f'<em>위반 {len(mine)}/{len(cell.get("claims", []))} 주장</em></h4>'
            f'<ul class=claims>{"".join(claim_item(arm, c) for c in mine)}</ul>'
            f"<details><summary>답변 전문</summary><div class=ans>{ans}</div></details></div>"
        )
    return f"""<section class=q id="q{n}">
  <header class=qhead><div class=qtitle><span class=badge>#{n}</span>
    <h3>{esc(question)}</h3></div>
    <p class=tags><span>위반 {len(items)}건</span>
      <span>{'모순 %d건' % len(contra) if contra else '모순 없음'}</span></p>
  </header>
  <div class=qbody>{''.join(blocks)}</div>
</section>"""


def violation_sections(cells: dict) -> tuple:
    by_n, qtext = {}, {}
    for k, cell in cells.items():
        qtext[cell["n"]] = cell["question"]
        for c in cell.get("claims", []):
            if c.get("violation"):
                by_n.setdefault(cell["n"], []).append((cell["arm"], c))
    blocks = "".join(question_block(n, qtext[n], by_n[n], cells) for n in sorted(by_n))
    return blocks, len(by_n), sum(len(v) for v in by_n.values())


# ────────────────────────────────────────────────────────────── 적대 검증이 구제한 것

def rescue_panel(cells: dict) -> str:
    rescued, pending = [], 0
    for k, cell in cells.items():
        for c in cell.get("claims", []):
            if c.get("final") == "기각(적대검증)":
                rescued.append((cell["n"], cell["arm"], c))
                pending += 1
            elif c.get("violation"):
                pending += 1
    lens_hits = {L: sum(1 for _, _, c in rescued
                        if (c.get("adv", {}).get(L, {}) or {}).get("grounded")) for L in LENS}

    # 인용을 실제로 붙인 것(스냅 통과)부터 보인다 — 구제가 말뿐이 아니었음을 보이는 게 요점이다
    picks = sorted(rescued, key=lambda t: (
        -t[2].get("adv_votes", 0),
        -max((len((t[2].get("adv", {}).get(L, {}) or {}).get("quote", "")) for L in LENS), default=0),
    ))[:RESCUE_MAX]

    cards = []
    for n, arm, c in picks:
        lenses = []
        for L in LENS:
            a = (c.get("adv", {}) or {}).get(L) or {}
            if not a.get("grounded"):
                continue
            body = (a.get("quote") or "").strip() or (a.get("reason") or "").strip()
            srcs = ", ".join(a.get("src_ids") or []) or "—"
            lenses.append(f'<li><span class="lens l{L}">{esc(LENS[L])}</span>'
                          f'<span class=lsrc>{esc(srcs)}</span>'
                          f'<span class=lq>{clip(body, QUOTE_CAP)}</span></li>')
        cards.append(
            f"<article class=rescue><header><a href=\"#q{n}\">#{n}</a>"
            f"<span class=armtag>{esc(ARM_LABEL[arm])}</span>"
            f'<span class=votes>{c.get("adv_votes", 0)}/3 뒤집음</span></header>'
            f'<p class=cl-text>{clip(c["text"], TEXT_CAP)}</p>'
            f'<ul class=lenses>{"".join(lenses)}</ul></article>')

    hits = " · ".join(f"{LENS[L]} {ratio(lens_hits[L], len(rescued))}" for L in LENS)
    return f"""<div class=panel>
  <h2>적대 검증이 구제한 것<span>③ 대조가 「근거 없음」으로 본 뒤 ④ 세 시선이 원문을 다시 뒤져 되살린 주장</span></h2>
  <p>④ 로 넘어간 {pending}건 중 <b>{ratio(len(rescued), pending)}</b> 이 뒤집혔다.
  자가 BM25 가 놓친 것을 위반으로 세지 않았다는 뜻이다 — 이 수치가 0 에 가까웠다면
  이 문서의 위반율은 「검색 실패율」의 다른 이름일 뿐이었다.
  시선별로 뒤집은 수는 {esc(hits)} (한 주장을 여럿이 함께 뒤집으므로 합은 100%를 넘는다).</p>
  <div class=rescues>{''.join(cards)}</div>
</div>"""


CSS = """
:root{
  --paper:#f4f6f7; --card:#fff; --sunk:#eceff1;
  --ink:#15181c; --mid:#4d555e; --mute:#79828c; --line:#d9dee3;
  --accent:#2c4a72; --accent-soft:#e3eaf3;
  --good:#1a6f48; --good-bg:#e2f1e9;
  --bad:#a8332a; --bad-bg:#fae7e5;
  --defer:#8a6a17; --defer-bg:#f7eed6;
  --sans:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",Roboto,"Noto Sans KR",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0e1115; --card:#161a1f; --sunk:#1c2127;
  --ink:#e4e8ec; --mid:#aab3bd; --mute:#7d8791; --line:#282f37;
  --accent:#8fb0dd; --accent-soft:#1c2836;
  --good:#5cc48d; --good-bg:#12291f;
  --bad:#ef8177; --bad-bg:#2e1a18;
  --defer:#d7ae44; --defer-bg:#2b2312;
}}
:root[data-theme="dark"]{
  --paper:#0e1115; --card:#161a1f; --sunk:#1c2127;
  --ink:#e4e8ec; --mid:#aab3bd; --mute:#7d8791; --line:#282f37;
  --accent:#8fb0dd; --accent-soft:#1c2836;
  --good:#5cc48d; --good-bg:#12291f;
  --bad:#ef8177; --bad-bg:#2e1a18;
  --defer:#d7ae44; --defer-bg:#2b2312;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.7 var(--sans);
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 96px;display:flex;flex-direction:column;gap:30px}
.scroller{overflow-x:auto}

header.top{padding:46px 0 0;display:flex;flex-direction:column;gap:10px}
h1{margin:0;font-size:31px;line-height:1.22;letter-spacing:-.022em;font-weight:700;text-wrap:balance}
.kicker{font:600 11px/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}
.cond{margin:0;color:var(--mid);font-size:13.5px;max-width:72ch}
.cond code{font:500 12.5px/1 var(--mono);background:var(--sunk);padding:2px 5px;border-radius:4px}

.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px 24px;
  display:flex;flex-direction:column;gap:14px}
.panel h2{margin:0;font-size:16px;letter-spacing:-.012em}
.panel h2 span{display:block;font-weight:400;font-size:12.5px;color:var(--mute);margin-top:3px;
  letter-spacing:0}
.panel p{margin:0;color:var(--mid);font-size:13.5px;max-width:80ch}
.panel p b{color:var(--ink)}
.panel.lead{border-color:var(--accent);border-width:1px 1px 1px 4px}
.panel.lead p{font-size:16px;line-height:1.72;color:var(--ink);max-width:74ch}
.panel.lead .kicker{margin-bottom:-4px}

.finding{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.finding div{background:var(--sunk);border-radius:9px;padding:13px 15px}
.finding b{display:block;font-size:13px;margin-bottom:3px}
.finding span{color:var(--mid);font-size:12.5px;line-height:1.6;display:block}

table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{text-align:right;padding:8px 10px;font-size:13px;border-bottom:1px solid var(--line);
  white-space:nowrap}
thead th{font:600 11px/1.35 var(--mono);color:var(--mute);letter-spacing:.03em;
  text-transform:uppercase;vertical-align:bottom}
tbody th{text-align:left;font-weight:600}
.rank td.num{font:600 13px/1 var(--mono)}
.rank tr.top th,.rank tr.top td{background:var(--good-bg)}
.rank tr.top td.num{color:var(--good)}
.rank tr.bad th,.rank tr.bad td{background:var(--bad-bg)}
.rank tr.bad td.num{color:var(--bad)}
.rank td.warn{color:var(--bad);font-weight:700}
caption{caption-side:bottom;text-align:left;color:var(--mute);font-size:12px;padding-top:9px}

section.q{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;
  scroll-margin-top:16px}
.qhead{padding:18px 22px 14px;border-bottom:1px solid var(--line);display:flex;
  flex-direction:column;gap:8px}
.qtitle{display:flex;gap:11px;align-items:baseline}
.badge{flex:none;font:700 11px/1 var(--mono);color:var(--accent);background:var(--accent-soft);
  padding:5px 8px;border-radius:5px}
.qhead h3{margin:0;font-size:16.5px;line-height:1.5;font-weight:650;letter-spacing:-.011em;
  text-wrap:balance}
.tags{margin:0;display:flex;gap:6px;flex-wrap:wrap}
.tags span{font-size:11px;color:var(--mute);border:1px solid var(--line);border-radius:99px;
  padding:1px 9px}
.qbody{display:flex;flex-direction:column}
.contra-block,.arm-block{padding:15px 22px 17px;border-bottom:1px solid var(--line)}
.qbody>:last-child{border-bottom:0}
.contra-block{background:var(--bad-bg);
  box-shadow:inset 3px 0 0 var(--bad)}
.contra-block h4,.arm-block h4{margin:0 0 9px;font-size:13px;font-weight:600;color:var(--mid)}
.contra-block h4{color:var(--bad);font-weight:700}
.arm-block h4 em{font-style:normal;color:var(--mute);font-weight:400;margin-left:6px;
  font:400 11.5px/1 var(--mono)}
ul.claims{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
.claim{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:11px 13px;
  display:flex;flex-direction:column;gap:6px}
.claim.contra{border-color:var(--bad)}
.cl-head{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.cl-head span{font-size:10.5px;border-radius:4px;padding:2px 7px;line-height:1.5}
.fin{font-weight:700;font-family:var(--mono)}
.fin.contra{background:var(--bad);color:var(--paper)}
.fin.unsup{background:var(--defer-bg);color:var(--defer)}
.armtag{color:var(--mid);border:1px solid var(--line)}
.src{background:var(--accent-soft);color:var(--accent)}
.votes{color:var(--mute);border:1px solid var(--line);font-family:var(--mono)}
.cl-text{margin:0;font-size:13.5px;line-height:1.68;color:var(--ink)}
.quote{margin:0;font-size:12.5px;line-height:1.65;color:var(--mid);background:var(--sunk);
  border-radius:7px;padding:9px 11px;white-space:pre-wrap}
.lbl{font:600 10.5px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--mute);
  display:block;margin-bottom:4px}
.why{margin:0;font-size:12.5px;line-height:1.62;color:var(--mid)}
.why span{font:600 10px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--mute);margin-right:7px}
details{margin-top:11px}
summary{cursor:pointer;font-size:12px;color:var(--accent);font-weight:600}
.ans{margin-top:8px;font-size:12.5px;line-height:1.72;white-space:pre-wrap;color:var(--mid);
  border-left:2px solid var(--line);padding-left:11px}

.rescues{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}
article.rescue{background:var(--sunk);border-radius:10px;padding:12px 14px;display:flex;
  flex-direction:column;gap:7px}
.rescue header{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.rescue header a{font:700 12px/1 var(--mono);color:var(--accent);text-decoration:none}
.rescue header span{font-size:10.5px;border-radius:4px;padding:2px 7px}
ul.lenses{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
ul.lenses li{display:flex;flex-direction:column;gap:3px;font-size:12px;line-height:1.6;
  color:var(--mid);border-left:2px solid var(--good);padding-left:9px}
.lens{font:700 10px/1 var(--mono);letter-spacing:.06em;color:var(--good)}
.lsrc{font:500 10.5px/1 var(--mono);color:var(--mute)}
.lq{white-space:pre-wrap}

.legend{display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--mute)}
.legend b{color:var(--ink);font-weight:600;font-family:var(--mono)}
footer{color:var(--mute);font-size:12.5px;line-height:1.75;border-top:1px solid var(--line);
  padding-top:18px}
footer code{font:500 12px/1 var(--mono)}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
@media (max-width:720px){h1{font-size:25px}.wrap{padding:0 15px 64px}
  .panel.lead p{font-size:14.5px}}
"""


def main() -> None:
    state = json.loads(SRC.read_text(encoding="utf-8"))
    cells = state["cells"]
    s = summarize(state)
    blocks, n_q, n_v = violation_sections(cells)
    n_claims = sum(len(c.get("claims", [])) for c in cells.values())

    legend = "".join(f"<span><b>{esc(ARM_LABEL[a])}</b> — {esc(ARM_NOTE[a])}</span>" for a in ARMS)
    all_ns = sorted({c["n"] for c in cells.values()})
    per_arm_n = " · ".join(f"{ARM_LABEL[a]} {s['all'][a]['cells']}셀" for a in ARMS)

    OUT.write_text(f"""<title>근거 위반 감사 — 5팔 지어냄율</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class=wrap>
<header class=top>
  <span class=kicker>봇 11 · 테스트 봇 D-1 ver2 · 2026-08-09</span>
  <h1>정답지 없이 잰 것 — 이 답의 주장이 규정 원문에 있는가</h1>
  <p class=cond>대상 {len(cells)}셀 · 문항 {len(all_ns)}개 · 사실 주장 {n_claims}건.
  Gemini 호출 0회, 판정은 전부 <code>codex</code>. 원자료 <code>audit.json</code>.
  팔 사이에서 다른 것은 <b>근거를 무엇으로 주느냐</b> 하나다.</p>
</header>

<div class="panel lead">
  <span class=kicker>결론</span>
  <p>{conclusion_line(s)}</p>
</div>

<div class=panel>
  <h2>주표 — 5팔 완비 {len(s['complete_questions'])}문항<span>다섯 팔이 모두 답한 문항만. 팔 사이 비교는 이 표로만 한다</span></h2>
  {arm_table(s['primary'])}
  <p><b>지어냄</b> = 규정 원문에도 시스템 프롬프트에도 없는 주장.
  <b>프롬프트출처</b> = 규정에는 없지만 시스템 프롬프트가 준 것(연락처·안내 문구)이라 성격이 다르다.
  <b>모순</b> = 원문이 그 주장과 다르게 말한다. <b>셀당</b> = 지어냄 ÷ 셀.
  지어냄율만 보면 안 되는 이유는 바로 옆의 <b>무주장셀·주장</b> 수에 있다.</p>
  <div class=legend>{legend}</div>
</div>

<div class=panel>
  <h2>부표 — 성공셀 전체<span>일부 팔만 답한 문항까지 포함. 팔마다 분모가 다르므로 순위로만 읽는다</span></h2>
  {arm_table(s['all'], caption=f"팔마다 문항 수(n)가 다르다 — {esc(per_arm_n)}. "
                               "호출 실패·빈 응답으로 빠진 셀이 팔마다 달라서 생긴 차이다.")}
  <p>같은 문항 집합 위가 아니다.
  <b>이 표의 지어냄율은 서로 다른 문항 집합 위에서 계산된 값</b>이라 주표를 대신할 수 없다.
  두 표의 순위가 같다는 것만 확인용으로 쓴다.</p>
</div>

<div class=panel>
  <h2>방법과 한계<span>정답지가 없어도 잴 수 있는 것 하나 — 「이 주장이 원문에 있는가」</span></h2>
  <div class=finding>
    <div><b>① 분해</b><span>답변 → 원자적 사실 주장. 인사말·의견·안내 문구·되묻는 질문은 제외한다.</span></div>
    <div><b>② 후보</b><span>주장마다 BM25 로 원문 상위 후보를 뽑는다. 로컬 계산이라 API 0회.</span></div>
    <div><b>③ 대조</b><span>codex 가 지지 / 미지지 / 모순을 판정하고 원문 인용을 함께 낸다.</span></div>
    <div><b>③′ 인용 검증</b><span><code>snap_to_source</code> 로 그 인용이 원문에 실재하는지 본다.
      못 붙이면 「지지」를 무효로 내리고 ④ 로 넘긴다.</span></div>
    <div><b>④ 적대 검증</b><span>미지지·모순만 세 시선(코퍼스 전수·표현 차이·조문 합성)이 반박한다.
      둘 이상이 뒤집으면 위반에서 기각.</span></div>
  </div>
  <p><b>지어냄의 정의.</b> 규정 원문(규정집·대사전)에도 시스템 프롬프트에도 근거가 없는 주장이다.
  「틀렸다」가 아니라 「이 봇이 가진 자료로는 뒷받침되지 않는다」는 뜻이다.
  프롬프트에서 온 것은 따로 세어 섞지 않는다.</p>
  <p><b>가장 큰 한계 — 말을 적게 하는 팔은 지어낼 것도 적다.</b>
  지어냄율의 분모는 그 팔이 내놓은 주장 수다. 아무 주장도 하지 않은 셀이 많고 주장 총수가 적은 팔은
  같은 실력으로도 율이 낮게 나온다. 그래서 이 문서는 율 옆에 <b>무주장셀</b>과 <b>주장</b> 수를 항상 함께 둔다.
  낮은 지어냄율을 「더 정확하다」로 읽지 말고 <b>「덜 말했다」와 구분되지 않는다</b>로 읽어야 한다.</p>
  <p><b>그 밖에.</b> 판정자는 codex 한 종이고 ③ 은 비교식이 아니라 절대식이지만 여전히 모델 판정이다.
  코퍼스는 이 봇이 가진 원문이 전부이므로, 규정 밖의 사실(운영 관행·공문)은 옳더라도 「지어냄」으로 잡힌다.
  팔 A 는 무엇을 검색했는지 알 수 없어(grounding 보고 부실) 주입 근거가 아니라 코퍼스 전체에 대고 대조했다.</p>
</div>

<div class=panel>
  <h2>문항별 위반 목록<span>위반이 하나라도 있는 {n_q}문항 · 위반 {n_v}건. 모순을 맨 앞에 둔다</span></h2>
  <p>각 문항 안에서 <b>모순</b>을 먼저 놓았다 — 원문에 없는 것(미지지)보다 원문이 다르게 말하는 것이
  훨씬 나쁘다. 적대검증 <b>n/3</b> 은 세 시선 중 몇이 「그래도 근거가 있다」고 봤는지다.
  2 이상이면 위반에서 빠졌으므로 여기 남은 것은 전부 0 또는 1 이다.</p>
</div>

{blocks}

{rescue_panel(cells)}

<footer>
  생성 <code>exports/wiki_eval/_audit_report.py</code> ·
  원자료 <code>audit.json</code> · 집계 <code>audit_summary.json</code> ·
  탐지기 <code>exports/wiki_eval/_audit.py</code><br>
  정답 10건 채점 비교는 <code>golden_report.html</code>, 45문항 키워드 자 비교는
  <code>report.html</code>, 배경과 함정은
  <code>docs/architecture/handoff-wiki-retrieval-2026-08-08.md</code>.
</footer>
</div>
""", encoding="utf-8")
    print(f"→ {OUT}  ({len(cells)}셀 · 주장 {n_claims}건 · 위반 {n_v}건 / {n_q}문항)")


if __name__ == "__main__":
    main()
