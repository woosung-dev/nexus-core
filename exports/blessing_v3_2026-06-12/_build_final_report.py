# 3주차 마무리 통합 리포트 — 가·나 전 버전 × 12렌즈 별점 매트릭스(탭 없음) + 문항별 점수 그리드(탭 없음)
import html
import json
from datetime import date
from pathlib import Path

NA = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
GA = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_ga_2026-06-12")
V3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_3주차_통합추천_가나_{date.today()}.html"

NA_USERS = ["조화연", "신은비", "김소영"]
GA_USERS = ["미야자키시호", "김소영", "조화연"]
NA_VERS = ["A_통합", "B_원리", "C_정밀", "나v1", "나v2", "나v3", "나v5"]
GA_VERS = ["A_통합", "B_원리", "C_정밀", "가원본", "가v3", "가v5"]


def esc(s):
    return html.escape(str(s if s is not None else ""))


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


# ── 1. 심판(별점) 수집: persona+fable(workflow 결과 저장본) + codex 4
judges = []  # {judge_type, judge, user, bot, ratings{ver:stars}, axes{ver:{...}}, rank1, rank2, rationale}
jm = load(V3 / "judge_matrix_result.json") or {}
for jtype in ("persona", "fable"):
    for entry in jm.get(jtype, []) or []:
        if not entry:
            continue
        for b in entry.get("bots", []):
            judges.append({
                "judge_type": jtype, "judge": entry.get("judge"), "user": entry.get("user"),
                "bot": b["bot"],
                "ratings": {r["version"]: r["stars"] for r in b.get("ratings", [])},
                "axes": {r["version"]: r.get("axes", {}) for r in b.get("ratings", [])},
                "notes": {r["version"]: r.get("note", "") for r in b.get("ratings", [])},
                "rank1": b.get("rank1"), "rank2": b.get("rank2"), "rationale": b.get("rationale", ""),
            })
for u in ["조화연", "신은비", "김소영", "미야자키시호"]:
    d = load(V3 / f"judge_codex_{u}.json")
    if not d:
        continue
    for b in d.get("bots", []):
        judges.append({
            "judge_type": "codex", "judge": "codex", "user": u, "bot": b["bot"],
            "ratings": {r["version"]: r["stars"] for r in b.get("ratings", [])},
            "axes": {r["version"]: r.get("axes", {}) for r in b.get("ratings", [])},
            "notes": {r["version"]: r.get("note", "") for r in b.get("ratings", [])},
            "rank1": b.get("rank1"), "rank2": b.get("rank2"), "rationale": b.get("rationale", ""),
        })


AXES = ["안전", "사실안내", "상담공감"]
JT_LABEL = {"persona": "페르소나", "codex": "codex", "fable": "Fable"}


def _sorted_lenses(bot):
    order = {"persona": 0, "codex": 1, "fable": 2}
    rows = [j for j in judges if j["bot"] == bot]
    rows.sort(key=lambda j: (order.get(j["judge_type"], 9), j["user"]))
    return rows


def axis_avg_table(bot, vers):
    rows = [j for j in judges if j["bot"] == bot]
    if not rows:
        return "<p class='muted'>(데이터 없음)</p>"
    groups = [
        ("전체 평균", rows),
        ("페르소나", [j for j in rows if j["judge_type"] == "persona"]),
        ("codex", [j for j in rows if j["judge_type"] == "codex"]),
        ("Fable", [j for j in rows if j["judge_type"] == "fable"]),
    ]
    head = "".join(f"<th>{html.escape(v)}</th>" for v in vers)
    body = ""
    for ax in AXES:
        for gname, gjs in groups:
            vals = {}
            for v in vers:
                xs = [j["axes"].get(v, {}).get(ax) for j in gjs if isinstance(j["axes"].get(v, {}).get(ax), (int, float))]
                vals[v] = (sum(xs) / len(xs)) if xs else None
            mx = max([x for x in vals.values() if x is not None], default=None)
            cells = ""
            for v in vers:
                a = vals[v]
                hi = " avgc" if (a is not None and mx is not None and abs(a - mx) < 1e-6) else ""
                cells += f'<td class="sc{hi}">{f"{a:.2f}" if a is not None else "-"}</td>'
            label = (f'<b>{ax}</b> · 전체' if gname == "전체 평균"
                     else f'<span class="dim">{ax} · {gname}</span>')
            rc = ' class="grprow"' if gname == "전체 평균" else (' class="codexrow"' if gname == "codex" else "")
            body += f'<tr{rc}><td class="psname">{label}</td>{cells}</tr>'
    return f'<table class="jm"><tr><th>축 · 측정자</th>{head}</tr>{body}</table>'


def lens_detail(bot, vers):
    rows = _sorted_lenses(bot)
    if not rows:
        return "<p class='muted'>(데이터 없음)</p>"
    head = "".join(f"<th>{html.escape(v)}</th>" for v in vers)
    out = ""
    for j in rows:
        body = ""
        for ax in AXES + ["⭐ 종합별점"]:
            cells = ""
            for v in vers:
                if ax == "⭐ 종합별점":
                    val = j["ratings"].get(v)
                    txt = f"{val:.1f}" if isinstance(val, (int, float)) else "-"
                    cls = "sc" + (" r1" if v == j.get("rank1") else (" r2" if v == j.get("rank2") else ""))
                else:
                    val = j["axes"].get(v, {}).get(ax)
                    txt = f"{val:.1f}" if isinstance(val, (int, float)) else "-"
                    cls = "sc"
                cells += f'<td class="{cls}">{txt}</td>'
            rowcls = ' class="avgr"' if ax == "⭐ 종합별점" else ""
            body += f'<tr{rowcls}><td class="jt">{ax}</td>{cells}</tr>'
        notes = "".join(f'<div class="ln"><b>{html.escape(v)}</b> {html.escape(j["notes"].get(v, ""))}</div>'
                        for v in vers if j["notes"].get(v))
        out += (f'<details class="lens" open><summary><span class="jt {j["judge_type"]}">{JT_LABEL[j["judge_type"]]}</span> '
                f'· {html.escape(j["user"])} → 봇 {html.escape(j["bot"])} · 🥇{html.escape(str(j.get("rank1")))} 🥈{html.escape(str(j.get("rank2")))}</summary>'
                f'<table class="jm"><tr><th>축 \\ 버전</th>{head}</tr>{body}</table>'
                f'<div class="lnotes">{notes}</div></details>')
    return out


def perspective_table(bot, vers):
    """무엇을 중요하게 보느냐(가중 관점)에 따라 1위가 어떻게 갈리는지."""
    rows = [j for j in judges if j["bot"] == bot]
    if not rows:
        return "<p class='muted'>(데이터 없음)</p>"
    persona = [j for j in rows if j["judge_type"] == "persona"]
    codexj = [j for j in rows if j["judge_type"] == "codex"]
    fablej = [j for j in rows if j["judge_type"] == "fable"]

    def avg_stars(js, v):
        xs = [j["ratings"].get(v) for j in js if isinstance(j["ratings"].get(v), (int, float))]
        return sum(xs) / len(xs) if xs else None

    def avg_axis(js, v, ax):
        xs = [j["axes"].get(v, {}).get(ax) for j in js if isinstance(j["axes"].get(v, {}).get(ax), (int, float))]
        return sum(xs) / len(xs) if xs else None

    agents = sorted(set(j["user"] for j in persona))
    schemes = [
        ("⚖️ 종합 균형 (전 렌즈 별점 평균)", {v: avg_stars(rows, v) for v in vers}, "all"),
        ("페르소나 그룹 (도메인 전문가)", {v: avg_stars(persona, v) for v in vers}, "grp"),
        ("codex 그룹 (독립 LLM)", {v: avg_stars(codexj, v) for v in vers}, "grp"),
        ("Fable 그룹 (무페르소나 중립)", {v: avg_stars(fablej, v) for v in vers}, "grp"),
    ]
    for a in agents:
        ja = [j for j in persona if j["user"] == a]
        schemes.append((f"└ 에이전트: {a}", {v: avg_stars(ja, v) for v in vers}, "agent"))
    schemes += [
        ("🛡️ 안전 최우선", {v: avg_axis(rows, v, "안전") for v in vers}, "axis"),
        ("📑 사실안내 최우선", {v: avg_axis(rows, v, "사실안내") for v in vers}, "axis"),
        ("💬 상담공감 최우선", {v: avg_axis(rows, v, "상담공감") for v in vers}, "axis"),
    ]
    head = "".join(f"<th>{html.escape(v)}</th>" for v in vers)
    body = ""
    for name, sc, kind in schemes:
        ranked = sorted([v for v in vers if sc[v] is not None], key=lambda v: -sc[v])
        r1 = ranked[0] if ranked else None
        r2 = ranked[1] if len(ranked) > 1 else None
        cells = ""
        for v in vers:
            s = sc[v]
            hi = " r1" if v == r1 else (" r2" if v == r2 else "")
            cells += f'<td class="sc{hi}">{f"{s:.2f}" if s is not None else "-"}</td>'
        rc = ' class="grprow"' if kind in ("all", "grp") else (' class="axisrow"' if kind == "axis" else "")
        body += f'<tr{rc}><td class="psname">{html.escape(name)}</td>{cells}<td class="rk2">🥇 {html.escape(str(r1))}<br>🥈 {html.escape(str(r2))}</td></tr>'
    return f'<table class="jm pt"><tr><th>측정 관점 (이걸 중요시하면)</th>{head}<th>1·2위</th></tr>{body}</table>'


def stars_html(v):
    if v is None:
        return '<span class="muted">-</span>'
    full = int(v)
    half = 1 if (v - full) >= 0.5 else 0
    return f'<span class="st">{"★"*full}{"⯨"*half}{"☆"*(5-full-half)}</span> <span class="sn">{v:.1f}</span>'


def judge_matrix_table(bot, vers):
    rows = [j for j in judges if j["bot"] == bot]
    if not rows:
        return "<p class='muted'>(심판 데이터 없음)</p>", {}
    # 평균
    avg = {}
    for v in vers:
        xs = [j["ratings"].get(v) for j in rows if isinstance(j["ratings"].get(v), (int, float))]
        avg[v] = sum(xs) / len(xs) if xs else None
    order = {"persona": 0, "codex": 1, "fable": 2}
    rows.sort(key=lambda j: (order.get(j["judge_type"], 9), j["user"]))
    JT = {"persona": "페르소나", "codex": "codex", "fable": "Fable"}
    body = ""
    for j in rows:
        cells = ""
        for v in vers:
            s = j["ratings"].get(v)
            hi = ""
            if v == j.get("rank1"):
                hi = " r1"
            elif v == j.get("rank2"):
                hi = " r2"
            cells += f'<td class="sc{hi}">{f"{s:.1f}" if isinstance(s,(int,float)) else "-"}</td>'
        body += (f'<tr><td class="jt {j["judge_type"]}">{JT[j["judge_type"]]}</td>'
                 f'<td>{esc(j["user"])}</td>{cells}'
                 f'<td class="rk">🥇{esc(j.get("rank1"))} · 🥈{esc(j.get("rank2"))}</td></tr>')
    # 평균 행
    avg_cells = "".join(f'<td class="sc avgc">{f"{avg[v]:.2f}" if avg[v] is not None else "-"}</td>' for v in vers)
    best = sorted([v for v in vers if avg[v] is not None], key=lambda v: -avg[v])[:2]
    body += f'<tr class="avgr"><td colspan="2"><b>평균</b></td>{avg_cells}<td class="rk">🥇{esc(best[0]) if best else "-"} · 🥈{esc(best[1]) if len(best)>1 else "-"}</td></tr>'
    head = "".join(f"<th>{esc(v)}</th>" for v in vers)
    return (f'<table class="jm"><tr><th>렌즈</th><th>테스터</th>{head}<th>1·2위</th></tr>{body}</table>', avg)


# ── 2. 문항별 점수 그리드 (기존 per-question 평가, 페르소나·codex 평균)
def eval_maps(bot):
    # ver -> (agent_map, codex_map)
    if bot == "나":
        src = {
            "나v1": (NA / "agent_eval.json", NA, "codex_eval_", ""),
            "나v2": (NA / "agent_eval_v2.json", NA, "codex_eval_v2_", ""),
            "나v3": (V3 / "agent_eval_나_v3.json", V3, "codex_나_", "_v3"),
            "나v5": (V3 / "agent_eval_나_v5.json", V3, "codex_나_", "_v5"),
        }
        users = NA_USERS
    else:
        src = {
            "가원본": (GA / "agent_eval.json", GA, "codex_eval_", ""),
            "가v3": (V3 / "agent_eval_가_v3.json", V3, "codex_가_", "_v3"),
            "가v5": (V3 / "agent_eval_가_v5.json", V3, "codex_가_", "_v5"),
        }
        users = GA_USERS
    out = {}
    for ver, (ap, folder, pre, suf) in src.items():
        araw = load(ap) or []
        ag = {e["user"]: {r["qid"]: r for r in e["eval"]["results"]} for e in araw if e and e.get("eval")}
        cx = {}
        for u in users:
            ce = load(folder / f"{pre}{u}{suf}.json")
            cx[u] = {r["qid"]: r for r in ce.get("results", [])} if ce else {}
        out[ver] = (ag, cx)
    return out, users


def cell_class(v):
    if v is None:
        return "miss"
    if v >= 4:
        return "g4"
    if v >= 3:
        return "g3"
    if v >= 2:
        return "g2"
    return "g1"


def question_grid(bot):
    maps, users = eval_maps(bot)
    bot_vers = [v for v in (NA_VERS if bot == "나" else GA_VERS) if not v.startswith(("A_", "B_", "C_"))]
    # A/B/C 점수는 최신(v5) 평가 기준
    last = bot_vers[-1]
    sections = ""
    for u in users:
        # qid 목록은 첫 버전 기준
        first_ag = maps[bot_vers[0]][0].get(u, {})
        qids = sorted(first_ag.keys(), key=lambda q: q.split("-")[-1])
        head = "<th>A</th><th>B</th><th>C</th>" + "".join(f"<th>{esc(v)}</th>" for v in bot_vers)
        body = ""
        for qid in qids:
            ag5 = maps[last][0].get(u, {}).get(qid, {})
            cx5 = maps[last][1].get(u, {}).get(qid, {})
            def abc(k):
                xs = [m.get("scores", {}).get(k) for m in (ag5, cx5)]
                xs = [x for x in xs if isinstance(x, (int, float))]
                return sum(xs) / len(xs) if xs else None
            cells = "".join(f'<td class="{cell_class(abc(k))}">{f"{abc(k):.1f}" if abc(k) is not None else "-"}</td>' for k in ("A", "B", "C"))
            for ver in bot_vers:
                ag, cx = maps[ver]
                xs = [m.get(u, {}).get(qid, {}).get("scores", {}).get("blessing") for m in (ag, cx)]
                xs = [x for x in xs if isinstance(x, (int, float))]
                v = sum(xs) / len(xs) if xs else None
                cells += f'<td class="{cell_class(v)}">{f"{v:.1f}" if v is not None else "-"}</td>'
            qtext = ""  # 질문 줄임
            body += f'<tr><td class="qid2">{esc(qid)}</td>{cells}</tr>'
        sections += (f'<h4>{esc(u)} — 30문항 (셀=페르소나·codex 평균 점수, A/B/C는 {esc(last)} 평가 기준)</h4>'
                     f'<table class="qg"><tr><th>문항</th>{head}</tr>{body}</table>')
    return sections


# ── 3. HTML
na_table, na_avg = judge_matrix_table("나", NA_VERS)
ga_table, ga_avg = judge_matrix_table("가", GA_VERS)


def podium(avg, vers):
    ranked = sorted([v for v in vers if avg.get(v) is not None], key=lambda v: -avg[v])
    if not ranked:
        return "<p class='muted'>(집계 대기)</p>"
    out = ""
    for i, v in enumerate(ranked[:3]):
        medal = ["🥇", "🥈", "🥉"][i]
        out += f'<div class="pod"><div class="pm">{medal} {esc(v)}</div><div class="ps">{stars_html(avg[v])}</div></div>'
    return f'<div class="podium">{out}</div>'


# 결측 주석
note_missing = ""
ga_v5 = load(V3 / "answers_가_v5.json")
if ga_v5:
    miss = [r["qid"] for r in ga_v5["results"] if r["answer"].startswith("[ERROR]")]
    if miss:
        note_missing = f'<div class="warn">⚠️ 가 v5는 쿼터 소진으로 {len(miss)}문항(가-조화연) 결측 상태의 잠정판입니다. 쿼터 리셋 후 보충하여 최종판으로 갱신 예정.</div>'

HTML = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 3주차 통합 추천 — 가·나 전 버전 × 12렌즈 ({date.today()})</title><style>
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;}}
*{{box-sizing:border-box;}}body{{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.55;}}
.wrap{{max-width:1180px;margin:0 auto;padding:36px 22px 90px;}}
header{{border-bottom:3px solid var(--accent);padding-bottom:16px;}}.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;}}
h1{{margin:6px 0 4px;font-size:25px;}}h2{{font-size:19px;margin:34px 0 10px;border-left:4px solid var(--accent);padding-left:10px;}}
h3{{font-size:16px;margin:22px 0 8px;}}h4{{font-size:13.5px;margin:18px 0 6px;color:var(--sub);}}
.meta{{color:var(--sub);font-size:13.5px;}}
.warn{{margin:14px 0;padding:12px 16px;border-radius:10px;background:#FFFBEB;border:1px solid #FDE68A;color:#92400E;font-size:13px;}}
.podium{{display:flex;gap:14px;margin:10px 0 6px;flex-wrap:wrap;}}
.pod{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 22px;text-align:center;}}
.pm{{font-weight:800;font-size:17px;}}.ps{{margin-top:4px;}}
.st{{color:#F59E0B;font-size:15px;letter-spacing:1px;}}.sn{{font-weight:800;font-size:14px;}}
table.jm,table.qg{{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:8px;}}
table.jm th,table.jm td,table.qg th,table.qg td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:center;}}
table.jm th,table.qg th{{background:#F1F3F8;color:var(--sub);font-size:11.5px;}}
table.jm td.jt{{font-weight:700;font-size:11.5px;}}td.jt.persona{{color:#6B21A8;}}td.jt.codex{{color:#1E40AF;}}td.jt.fable{{color:#0F766E;}}
td.sc{{font-weight:700;}}td.sc.r1{{background:#FEF3C7;outline:2px solid #F59E0B;outline-offset:-2px;}}td.sc.r2{{background:#F1F5F9;outline:2px dashed #94A3B8;outline-offset:-2px;}}
tr.avgr{{background:#FAF5FF;}}td.avgc{{font-weight:800;color:var(--accent);}}
td.rk{{font-size:11px;text-align:left;}}
td.qid2{{font-weight:700;font-size:11px;color:var(--accent);text-align:left;}}
td.g4{{background:#DCFCE7;color:#166534;font-weight:700;}}td.g3{{background:#FEF9C3;color:#854D0E;}}td.g2{{background:#FFEDD5;color:#9A3412;}}td.g1{{background:#FEE2E2;color:#991B1B;font-weight:700;}}td.miss{{background:#F8FAFC;color:#CBD5E1;}}
.legend{{font-size:12px;color:var(--sub);margin:6px 0 14px;}}
.note{{font-size:12.5px;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:18px;}}
.rat{{font-size:12.5px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:6px 0;}}
.rat b{{color:var(--accent);}}
details.lens{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:7px 0;padding:4px 10px;}}
details.lens summary{{cursor:pointer;font-size:13px;padding:6px 2px;list-style:none;}}
details.lens summary::-webkit-details-marker{{display:none;}}
.lnotes{{margin:6px 0 8px;}}.ln{{font-size:11.5px;color:var(--sub);margin:2px 0;}}.ln b{{color:var(--ink);}}
table.pt td.psname,table.jm td.psname{{text-align:left;font-weight:600;}}table.pt tr.grprow,table.jm tr.grprow{{background:#FAF5FF;}}table.pt tr.axisrow{{background:#F0FDFA;}}
table.pt td.rk2{{font-size:11px;text-align:left;line-height:1.4;}}
table.jm tr.codexrow{{background:#EFF6FF;}}table.jm tr.codexrow td.psname{{color:#1E40AF;}}
.dim{{opacity:.72;font-weight:500;}}
</style></head><body><div class="wrap">
<header><div class="eyebrow">REDTEAM 3주차 마무리 · 통합 추천</div>
<h1>블레싱 가·나 — 전 버전 × 12렌즈 추천도</h1>
<div class="meta">측정자: 페르소나 4(조화연·신은비·김소영·미야자키시호) + codex 4 + Fable 4 — 전부 빈 컨텍스트 fresh 측정 · 축: 안전/사실안내/상담공감 · {date.today()}</div></header>
{note_missing}

<h2>🏆 블레싱 나 — 종합 추천 (12렌즈 평균)</h2>
{podium(na_avg, NA_VERS)}
<h3>🎯 관점별 추천 — 무엇을 중요시하느냐에 따라 1위가 갈린다</h3>
<div class="legend">행=가중 관점, 셀=그 관점 기준 점수, 노랑=그 관점의 1위·점선=2위. 같은 봇이라도 '안전 우선'과 'codex(직접성)'에서 1위가 달라질 수 있다.</div>
{perspective_table("나", NA_VERS)}
<h3>별점 매트릭스 (행=개별 렌즈, 노랑=그 렌즈의 1위, 점선=2위)</h3>
{na_table}
<h3>축별 평균 (안전·사실안내·상담공감)</h3>
{axis_avg_table("나", NA_VERS)}
<h3>측정자별 상세 채점 — 각 렌즈 × 버전 × 축 (전부 펼침)</h3>
{lens_detail("나", NA_VERS)}

<h2>🏆 블레싱 가 — 종합 추천 (12렌즈 평균)</h2>
{podium(ga_avg, GA_VERS)}
<h3>🎯 관점별 추천 — 무엇을 중요시하느냐에 따라 1위가 갈린다</h3>
<div class="legend">가 v5는 16문항 결측이라 점수가 과소평가될 수 있음(잠정).</div>
{perspective_table("가", GA_VERS)}
<h3>별점 매트릭스</h3>
{ga_table}
<h3>축별 평균 (안전·사실안내·상담공감)</h3>
{axis_avg_table("가", GA_VERS)}
<h3>측정자별 상세 채점 — 각 렌즈 × 버전 × 축 (전부 펼침)</h3>
{lens_detail("가", GA_VERS)}

<h2>📋 심판별 종합 의견</h2>
{"".join(f'<div class="rat"><b>[{j["judge_type"]}·{esc(j["user"])} → 봇 {esc(j["bot"])}]</b> 🥇{esc(j.get("rank1"))} 🥈{esc(j.get("rank2"))} — {esc(j.get("rationale"))}</div>' for j in judges)}

<h2>🔢 문항별 점수 그리드 — 블레싱 나</h2>
<div class="legend">셀 = 해당 버전 답변에 대한 (페르소나+codex) 평균점(1~5). 초록≥4 · 노랑≥3 · 주황≥2 · 빨강&lt;2 · 회색=결측.</div>
{question_grid("나")}

<h2>🔢 문항별 점수 그리드 — 블레싱 가</h2>
{question_grid("가")}

<div class="note"><b>방법</b> · 별점 매트릭스 = 12렌즈가 빈 컨텍스트에서 사용자별 팩(질문+A/B/C+버전별 답변 원문)만 읽고 독립 채점(0.5~5.0). 문항별 그리드 = 버전별 문항 평가(페르소나+codex)의 블레싱 점수 평균, A/B/C 열은 최신 버전 평가 기준. 모든 표는 탭 없이 펼쳐져 있음. 가-조화연 v5 결측은 잠정 — 보충 후 갱신.</div>
</div></body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"저장: {OUT}")
print("나 평균:", {k: round(v, 2) for k, v in na_avg.items() if v})
print("가 평균:", {k: round(v, 2) for k, v in ga_avg.items() if v})
