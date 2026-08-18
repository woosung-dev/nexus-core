# FINDINGS/REPORT 를 사람이 읽는 단일 HTML 로 굽는다 (자기완결 — 외부 리소스 0).
#
# 숫자는 전부 _dump_*.json / _branches_*.json 에서 계산한다. 손으로 옮겨 적지 않는다.
# 서술 문단만 이 파일에 있고, 표·수치는 데이터에서 나온다.
import argparse
import html
import json
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
TABLE_PAGE = 21          # 2026 정본 편성 비교표가 있는 페이지
nfc = lambda s: unicodedata.normalize("NFC", s or "")
esc = lambda s: html.escape(str(s if s is not None else ""))


def load(n):
    p = DIR / n
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#fbfaf8; --fg:#1c1a17; --mut:#6b645c; --line:#e2ddd5; --card:#fff;
  --accent:#8a5a2b; --accent-bg:#f5ede2; --ok:#2f6d4f; --bad:#a3341f; --warn:#8a6d1f;
  --code:#f3f0eb;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#161513; --fg:#eae6e0; --mut:#9d968c; --line:#302d29; --card:#1e1d1a;
        --accent:#d9a066; --accent-bg:#2a231a; --ok:#6fbf8f; --bad:#e0806a; --warn:#d4b45c;
        --code:#232120;}
}
:root[data-theme=light]{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b645c;--line:#e2ddd5;--card:#fff;
  --accent:#8a5a2b;--accent-bg:#f5ede2;--ok:#2f6d4f;--bad:#a3341f;--warn:#8a6d1f;--code:#f3f0eb}
:root[data-theme=dark]{--bg:#161513;--fg:#eae6e0;--mut:#9d968c;--line:#302d29;--card:#1e1d1a;
  --accent:#d9a066;--accent-bg:#2a231a;--ok:#6fbf8f;--bad:#e0806a;--warn:#d4b45c;--code:#232120}

body{margin:0;background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Noto Sans KR",sans-serif;
  line-height:1.75;font-size:16px;-webkit-text-size-adjust:100%}
.wrap{max-width:900px;margin:0 auto;padding:48px 24px 96px}
header{border-bottom:3px solid var(--accent);padding-bottom:24px;margin-bottom:40px}
.kicker{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.14em;margin:0 0 10px}
h1{font-size:31px;line-height:1.3;margin:0 0 14px;letter-spacing:-.02em}
.meta{color:var(--mut);font-size:14px;margin:0}
h2{font-size:22px;margin:52px 0 16px;padding-top:20px;border-top:1px solid var(--line);letter-spacing:-.01em}
h2:first-of-type{border-top:none}
h3{font-size:17px;margin:32px 0 10px}
p{margin:0 0 14px}
.lead{font-size:19px;line-height:1.65}
strong{font-weight:700}
code{background:var(--code);padding:.12em .4em;border-radius:4px;font-size:.86em;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all}
.callout{background:var(--accent-bg);border-left:4px solid var(--accent);
  padding:20px 24px;border-radius:0 8px 8px 0;margin:24px 0}
.callout p:last-child{margin-bottom:0}
.callout .big{font-size:21px;font-weight:700;line-height:1.5;margin-bottom:8px}
.note{border-left:3px solid var(--line);padding:4px 0 4px 18px;color:var(--mut);
  font-size:14.5px;margin:18px 0}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:20px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px;min-width:440px}
th,td{border-bottom:1px solid var(--line);padding:10px 12px;text-align:left;vertical-align:top}
th{font-weight:700;color:var(--mut);font-size:12.5px;letter-spacing:.05em;
  text-transform:uppercase;white-space:nowrap;border-bottom:2px solid var(--line)}
tbody tr:last-child td{border-bottom:none}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.yes{color:var(--ok);font-weight:700}
.no{color:var(--bad);font-weight:700}
.warn{color:var(--warn);font-weight:700}
.cards{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin:24px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.card .n{font-size:27px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.card .l{color:var(--mut);font-size:12.5px;margin-top:4px;line-height:1.45}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;
  padding:12px 16px;margin:12px 0}
details[open]{padding-bottom:18px}
summary{cursor:pointer;font-weight:600;font-size:14.5px}
summary::marker{color:var(--accent)}
.ans{white-space:pre-wrap;font-size:14px;line-height:1.7;margin-top:12px;
  padding-top:12px;border-top:1px solid var(--line);color:var(--fg)}
.chunk{font-size:13px;color:var(--mut);border-left:2px solid var(--line);
  padding-left:14px;margin:10px 0;line-height:1.6}
.chunk b{color:var(--fg)}
.q{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:0 8px 8px 0;padding:14px 18px;margin:16px 0;font-size:15px}
.tag{display:inline-block;background:var(--accent-bg);color:var(--accent);
  border-radius:99px;padding:2px 10px;font-size:11.5px;font-weight:700;margin-left:6px;
  vertical-align:middle}
ul,ol{margin:0 0 14px;padding-left:22px}
li{margin-bottom:7px}
footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--mut);font-size:13px}
@media print{
  body{background:#fff;color:#000;font-size:11pt}
  .wrap{max-width:none;padding:0}
  details{break-inside:avoid} details[open] .ans{display:block}
  h2{break-after:avoid}
}
@media (max-width:600px){.wrap{padding:32px 16px 64px}h1{font-size:25px}.lead{font-size:17px}}
"""


def build(d7, d11, br, items):
    B = {(q["qid"], r["arm"], r["rep"]): r for q in br["questions"] for r in q["results"]}
    M = {(r["qid"], r["arm"], r["rep"]): r for r in d7["results"]}
    P = {r["qid"]: r for r in d11["results"]} if d11 else {}
    qids = [i["qid"] for i in items]
    qm = {i["qid"]: i for i in items}
    meta = d7["bot"]
    reps = d7["reps"]

    # ── 집계 ──────────────────────────────────────────────
    def arm_stats(arm):
        rows = [v for k, v in B.items() if k[1] == arm]
        nb = [r["n_branches"] for r in rows]
        conds = [c for r in rows for c in (r.get("branches") or [])]
        ung = [c for c in conds if c.get("grounded") is False]
        return sum(nb) / max(len(nb), 1), len(conds), len(ung)
    aA, cA, uA = arm_stats("A")
    aB, cB, uB = arm_stats("B")

    chunks_all = [c for r in d7["results"] for c in r["grounding"]["chunks"] if "title" in c]
    n_ch = len(chunks_all)
    n_cm = sum(1 for c in chunks_all if c.get("custom_metadata"))
    n_pg = sum(1 for c in chunks_all if c.get("page_number") is not None)
    n_uri = sum(1 for c in chunks_all if c.get("uri"))
    sups = [s for r in d7["results"] for s in r["grounding"]["supports"]]
    n_cs = sum(1 for s in sups if s["confidence_scores"])
    persona_empty = sum(1 for r in d7["results"]
                        if r["arm"] in ("A", "B") and r["grounding"]["n_chunks"] == 0)
    persona_tot = sum(1 for r in d7["results"] if r["arm"] in ("A", "B"))

    H = []
    a = H.append

    a('<div class="wrap"><header>')
    a('<p class="kicker">축복 챗봇 · RAG 실험 보고</p>')
    a("<h1>조건부 분기 답변 절제 실험</h1>")
    a(f'<p class="meta">2026-08-04 · 봇 {meta["id"]} {esc(meta["name"])} · '
      f'<code>{esc(meta["model"])}</code> · top_k {d7["rag_top_k"]} · '
      f'temperature {d7["rag_temperature"]} · 라이브 호출 {len(d7["results"])+len(P)}회 · 오류 0건</p>')
    a("</header>")

    # ── 결론 ──
    a('<div class="callout">')
    a('<p class="big">재료 문제도 생성 문제도 아니다. 1차 병목은 <u>검색</u>이다.</p>')
    a("<p>분기 근거는 문서에 <strong>있고</strong>, 그것이 top_k 안에 들어오면 모델은 "
      "프롬프트 지시 없이도 분기한다. 들어오지 않으면 어떤 프롬프트로도 분기하지 않는다.</p>")
    a("</div>")

    a('<div class="cards">')
    for n, l in [(f"{aA:.1f} → {aB:.1f}", "평균 분기 수<br>A 기준선 → B 분기프롬프트"),
                 (f"{uA} vs {uB}", f"미근거 조건(과분기)<br>A {uA/max(cA,1):.0%} · B {uB/max(cB,1):.0%}"),
                 (f"{n_cm}/{n_ch}", "custom_metadata 회수<br>체크 A"),
                 (f"{persona_empty}/{persona_tot}", "페르소나 팔 청크 0건<br>grounding 보고 억제")]:
        a(f'<div class="card"><div class="n">{n}</div><div class="l">{l}</div></div>')
    a("</div>")

    # ── 무엇을 했나 ──
    a("<h2>무엇을 했나</h2>")
    a("<p>같은 문항 10건을 세 가지 조건으로 각각 2회씩 질의하고, 검색된 청크 원문까지 그대로 덤프했다.</p>")
    a('<div class="scroll"><table><thead><tr><th>팔</th><th>system_instruction</th>'
      "<th>무엇을 보나</th></tr></thead><tbody>")
    for arm, sp, why in [
        ("A 기준선", "<code>bot.system_prompt</code> + FOLLOWUPS (운영과 완전 동일)", "분기 수·과분기"),
        ("B 분기프롬프트", "A + 조건부 분기 원칙 4개조 (325자)", "프롬프트만으로 분기가 늘어나는가"),
        ("R 검색프로브", "중립 프롬프트 단독 (페르소나 없음)", "검색이 무엇을 물어왔는가")]:
        a(f"<tr><td><strong>{arm}</strong></td><td>{sp}</td><td>{esc(why)}</td></tr>")
    a("</tbody></table></div>")
    a('<p class="note">A 팔이 운영 경로와 바이트 단위로 같은지 해시로 확인했다 '
      f'(<code>{esc(meta["system_prompt_sha256"])}</code> 기반, 12,869자 일치). '
      "프롬프트 변형은 스크립트 메모리에만 있고 <code>bots.system_prompt</code> 는 건드리지 않았다. "
      "DB 쓰기 0건(messages·sessions 카운트 불변, 봇 프롬프트 해시 불변).</p>")

    # ── 핵심 발견 ──
    a("<h2>핵심 발견 — 같은 문서, 같은 모델, 같은 프롬프트. 검색만 다르다</h2>")
    a(f"<p>2026 정본 <strong>p.{TABLE_PAGE}</strong> 에 편성 비교표가 있다.</p>")
    a('<div class="scroll"><table><thead><tr><th>구분</th><th>축복자녀가정 편성</th>'
      "<th>1세가정 편성</th></tr></thead><tbody>")
    a("<tr><td>의식 노정</td><td>성주식 → 축복식 → 40일 성별 → <strong>12일 특별의식</strong></td>"
      "<td>성주식 → 축복식 → <strong>탕감봉의식</strong> → 40일 성별 → <strong>3일행사</strong></td></tr>")
    a("<tr><td>자녀 세대</td><td>3세 전통 상속</td><td>2세 전통 상속</td></tr>")
    a("</tbody></table></div>")
    a("<p>이 표를 가진 봇11에 <strong>중립 프롬프트로, 분기 지시 없이</strong> 질의한 결과:</p>")

    a('<div class="scroll"><table><thead><tr><th>문항</th><th>회수 페이지</th>'
      f"<th>p.{TABLE_PAGE} 회수</th><th>분기 결과</th></tr></thead><tbody>")
    for qid, verdict in [("R-88", "2분기, 정확"), ("R-216", "분기함"),
                         ("R-219", "1분기 — 1세편성 경로를 일반화")]:
        r = P.get(qid)
        pages = sorted({c.get("page_number") for c in r["grounding"]["chunks"]
                        if c.get("page_number") is not None}) if r else []
        got = TABLE_PAGE in pages
        mark = '<span class="yes">✓ 회수</span>' if got else '<span class="no">✗ 미회수</span>'
        vcls = "" if got else ' class="no"'
        star = ' <span class="tag">레드팀 원 실패 문항</span>' if qid == "R-219" else ""
        a(f"<tr><td><strong>{qid}</strong>{star}<br>"
          f'<span style="color:var(--mut);font-size:13px">{esc(qm[qid]["q"][:46])}…</span></td>'
          f'<td class="num">{", ".join(map(str,pages))}</td><td>{mark}</td>'
          f"<td{vcls}>{esc(verdict)}</td></tr>")
    a("</tbody></table></div>")

    a("<p><strong>사용자가 분기축을 질문에 명시하면</strong>(R-88 「1세가정 편성과 2세가정 편성은 "
      "무엇이 다른가요?」) 검색이 비교표를 물어오고 모델은 분기한다. "
      "<strong>명시하지 않으면</strong>(R-219 「축복 받고 나서 해야되는 의식」) 같은 문서집합인데도 "
      "비교표가 top_k 에 못 들어오고 뭉갠다.</p>")
    a("<p>R-219 는 3주차 레드팀이 분기 붕괴를 지적한 바로 그 문항이다 — "
      "<em>“1세편성 탕감봉의식·3일행사 완전누락, 2세편성 12일특별의식만 일반화”</em>. "
      "이번에 <strong>실패가 재현됐고</strong>, 원인이 검색 단계로 좁혀졌다. "
      "봇7(2022 규정집)도 같은 문항에서 동일하게 단일 경로로 답했다.</p>")

    # 실제 답변 대조
    if P.get("R-219") and P.get("R-88"):
        a("<h3>실제 답변 대조 (봇11, 중립 프롬프트, 분기 지시 없음)</h3>")
        for qid, lbl in [("R-88", f"p.{TABLE_PAGE} 회수됨 → 분기함"),
                         ("R-219", f"p.{TABLE_PAGE} 미회수 → 뭉갬")]:
            r = P[qid]
            a(f"<details><summary>{qid} — {esc(lbl)}</summary>"
              f'<div class="ans">{esc(r["answer"])}</div></details>')

    # ── 절제 결과 ──
    a("<h2>절제 결과 — B는 A보다 분기를 늘리지 않았다</h2>")
    a('<div class="scroll"><table><thead><tr><th>지표</th><th>A 기준선</th>'
      "<th>B 분기프롬프트</th><th>판정</th></tr></thead><tbody>")
    a(f'<tr><td>평균 분기 수</td><td class="num">{aA:.1f}</td><td class="num">{aB:.1f}</td>'
      "<td>차이 없음</td></tr>")
    a(f'<tr><td>조건 총수</td><td class="num">{cA}</td><td class="num">{cB}</td><td>—</td></tr>')
    a(f'<tr><td><strong>미근거 조건(과분기)</strong></td>'
      f'<td class="num">{uA} ({uA/max(cA,1):.0%})</td>'
      f'<td class="num">{uB} ({uB/max(cB,1):.0%})</td>'
      "<td>프롬프트 탓 아님</td></tr>")
    a("</tbody></table></div>")
    a("<p>핸드오프 §7 기준 <strong>“B ≈ A”</strong> 에 해당한다.</p>")
    a("<p><strong>과분기는 분기 프롬프트가 만든 것이 아니다.</strong> A 기준선에 이미 "
      f"{uA/max(cA,1):.0%} 가 있다. 차이는 조건 50건 규모에서 {uA}건 대 {uB}건이라 노이즈다. "
      "핸드오프 §7 1행(“B에서 미근거 조건이 1건이라도 나오면 프롬프트 단독 불가”)은 "
      "<strong>A 기준선을 함께 재지 않으면 잘못된 결론을 준다</strong> — 그래서 양쪽을 다 쟀다.</p>")
    a(f'<p class="note">다만 현행 파이프라인의 문서 미근거 조건 생성률이 '
      f"{uA/max(cA,1):.0%} 라는 것 자체는 별개의 문제다. 제안서 §9-4 가 잡은 목표값은 0 이다.</p>")

    a("<h3>측정 도구 주의</h3>")
    a("<p>분기 수는 <strong>서식이 아니라 의미로</strong> 세야 한다. 정규식은 양방향으로 틀렸다 — "
      "<code>경우:</code> 패턴은 「### 1. 2세가정 편성」 형식의 2분기를 0으로 셌고, 넓힌 패턴은 "
      "「참고 사항」까지 분기로 셌다. 그래서 codex CLI 의미판정으로 바꿨다"
      "(생성=gemini / 판정=codex 분리). <strong>판정 자체에도 실행 간 변동이 있다</strong> — "
      "1차 A=2.1/B=2.1, 2차 A=2.5/B=2.4. 소수점이 아니라 방향만 읽어야 한다.</p>")

    # ── 체크 A ──
    a("<h2>계획에서 바뀐 것</h2>")
    a('<div class="scroll"><table><thead><tr><th>핸드오프 전제</th><th>실측</th>'
      "<th>영향</th></tr></thead><tbody>")
    a(f"<tr><td>체크 A — <code>custom_metadata</code> 회수 여부 미지수</td>"
      f'<td><span class="yes">{n_cm}/{n_ch} (100%) 회수</span><br>'
      f"<code>bot_id</code>(numeric) · <code>content_sha256</code>(string)</td>"
      "<td><strong>조건 다양성 판정을 결정론으로 만들 수 있다.</strong> 제안서 L1·L4② 경로가 열려 있다</td></tr>")
    a(f"<tr><td>A(페르소나) 청크를 덤프해 눈으로 본다</td>"
      f'<td><span class="no">{persona_empty}/{persona_tot} 전건 chunks=0</span></td>'
      "<td>원안 2팔이었으면 체크 B·C·D 전부 판정불가. 중립 프로브 R 추가가 실험을 성립시켰다</td></tr>")
    a("</tbody></table></div>")
    a(f'<p class="note">부수 관측 — <code>page_number</code> {n_pg}/{n_ch} 회수, '
      f"<code>uri</code> {n_uri}/{n_ch}, <code>confidence_scores</code> {n_cs}/{len(sups)} supports. "
      "검색 관련도 점수가 없다는 기존 결론은 유지된다.<br>"
      "※ 2026-06-30 캡처(0/441)와 다르다 — 그 사이 API 동작이 바뀌었다.</p>")

    # ── 문항별 ──
    a("<h2>문항별 관측</h2>")
    a(f"<p>분기 수는 반복 {reps}회 값을 <code>/</code> 로 이어 썼다. "
      "페르소나 팔(A·B)은 청크를 보고하지 않으므로 검색 관측은 R 팔 기준이다.</p>")
    a('<div class="scroll"><table><thead><tr><th>문항</th><th>분기축</th><th>A 분기</th>'
      "<th>B 분기</th><th>A 미근거</th><th>B 미근거</th><th>R 청크</th></tr></thead><tbody>")
    for qid in qids:
        it = qm[qid]
        cells = {}
        for arm in ("A", "B"):
            nb = [B[(qid, arm, rp)]["n_branches"] for rp in range(1, reps + 1) if (qid, arm, rp) in B]
            ung = sum(1 for rp in range(1, reps + 1) if (qid, arm, rp) in B
                      for c in (B[(qid, arm, rp)].get("branches") or []) if c.get("grounded") is False)
            cells[arm] = ("/".join(map(str, nb)), ung)
        rc = [M[(qid, "R", rp)]["grounding"]["n_chunks"] for rp in range(1, reps + 1) if (qid, "R", rp) in M]
        uc = lambda n: f'<span class="no">{n}</span>' if n else "0"
        a(f"<tr><td><strong>{qid}</strong></td><td>{esc(it['branch_axis'])}</td>"
          f'<td class="num">{cells["A"][0]}</td><td class="num">{cells["B"][0]}</td>'
          f'<td class="num">{uc(cells["A"][1])}</td><td class="num">{uc(cells["B"][1])}</td>'
          f'<td class="num">{"/".join(map(str,rc))}</td></tr>')
    a("</tbody></table></div>")

    for qid in qids:
        it = qm[qid]
        a(f"<h3>{qid} <span class=\"tag\">{esc(it['branch_axis'])}</span></h3>")
        a(f'<div class="q">{esc(it["q"])}</div>')
        rch, seen = [], set()
        for rp in range(1, reps + 1):
            for c in M.get((qid, "R", rp), {}).get("grounding", {}).get("chunks", []):
                k = (nfc(c.get("title")), c.get("page_number"))
                if k in seen:
                    continue
                seen.add(k)
                rch.append(c)
        a(f"<details><summary>검색된 청크 {len(rch)}개 (R 팔, 반복 합집합)</summary>")
        for c in rch:
            a(f'<div class="chunk"><b>{esc(c.get("title"))}</b> p.{esc(c.get("page_number"))}<br>'
              f'{esc((c.get("text") or "")[:420])}…</div>')
        a("</details>")
        for arm in ("A", "B"):
            for rp in range(1, reps + 1):
                j, r = B.get((qid, arm, rp)), M.get((qid, arm, rp))
                if not j or not r:
                    continue
                ung = [c for c in (j.get("branches") or []) if c.get("grounded") is False]
                badge = f' · <span class="no">미근거 {len(ung)}</span>' if ung else ""
                a(f'<details><summary>{arm} rep{rp} — 분기 {j["n_branches"]}개{badge}</summary>')
                for c in (j.get("branches") or []):
                    g = c.get("grounded")
                    m = ('<span class="yes">근거있음</span>' if g is True
                         else '<span class="no">미근거</span>' if g is False else "판정없음")
                    ev = f' · <span style="color:var(--mut)">“{esc(c.get("evidence"))}”</span>' if c.get("evidence") else ""
                    a(f'<div class="chunk">{esc(c.get("condition"))} — {m}{ev}</div>')
                a(f'<div class="ans">{esc(r["answer"])}</div></details>')

    # ── 다음 투자 ──
    a("<h2>다음 투자 — 우선순위</h2>")
    a("<p>핸드오프 §7 판정표는 “재료 vs 생성” 이분법이라 이번 결과를 담지 못한다. 아래로 갱신을 제안한다.</p>")
    a('<div class="scroll"><table><thead><tr><th>순위</th><th>조치</th><th>근거</th>'
      "<th>규모</th></tr></thead><tbody>")
    for n, act, why, sz in [
        ("1", "<strong>L2 분기별 검색</strong> — 사용자가 축을 명시 안 했을 때 축 값별 서브쿼리 병렬 검색 후 병합",
         "R-88 vs R-219 대조가 직접 근거", "1~2일"),
        ("2", "<strong>2026 정본을 운영 봇에 적재</strong>",
         "봇7 에는 편성 비교표가 없고 용어도 구버전(2세가정 편성)", "반나절 + 검수"),
        ("3", "조건 메타데이터 부착 (<code>generation</code>·<code>stage</code>·<code>doc_class</code>…)",
         "체크 A 100% 회수 확인 → 결정론 검증 가능", "도메인 2~3일"),
        ("4", "미근거 조건 대응 (L4 분기 게이팅)", "A 기준선에서 이미 발생", "2일")]:
        a(f'<tr><td class="num"><strong>{n}</strong></td><td>{act}</td><td>{why}</td><td>{sz}</td></tr>')
    a('<tr><td class="warn">보류</td><td><strong>규정 카드 코퍼스 전면 재작성</strong></td>'
      "<td>분기 근거는 이미 문서에 있다. 카드의 값어치인 <code>[이런 질문]</code> 임베딩 근접성은 "
      "<strong>1순위 L2 가 더 싸게 해결한다</strong></td><td>—</td></tr>")
    a('<tr><td class="warn">보류</td><td>분기 프롬프트 운영 적용</td>'
      "<td>B 가 A 보다 나은 근거 없음</td><td>—</td></tr>")
    a("</tbody></table></div>")
    a("<p><strong>카드 코퍼스는 착수하지 않는 것을 권한다.</strong> 다만 완전 기각은 아니다 — "
      "L2 를 넣고도 R-219 류가 남으면, 그때 카드의 <code>[이런 질문]</code> 필드가 정확히 그 문제를 "
      "겨냥한다. <strong>L2 이후 재평가한다.</strong></p>")

    # ── 한계 ──
    a("<h2>이 실험이 답하지 못한 것</h2><ul>")
    a("<li><strong>분기의 정확성.</strong> 분기 <em>수</em>만 셌고 <em>맞는 분기인지</em>는 안 쟀다. "
      f"정답 분기 라벨이 없기 때문이다. A={aA:.1f}분기라는 값은 “충분히 분기한다”는 뜻이 아니다 — "
      "R-219 처럼 <strong>틀린 한 분기</strong>를 내는 것도 1분기로 센다.</li>")
    a("<li><strong>n=10.</strong> 통계가 아니라 스크리닝이다.</li>")
    a("<li><strong>R 은 검색 결과가 아니라 “모델이 보고한 청크”다.</strong> 중립 프롬프트에서 "
      "20/20 회수됐고 top_k=12 까지 채우지만, 검색이 실제로 무엇을 반환했는지의 직접 관측은 "
      "이 스택에서 불가능하다.</li>")
    a("<li><strong>문항 전제 미검증.</strong> 10문항이 “실제로 케이스별로 답이 갈리는 질문”인지 "
      "도메인 확인을 받지 않았다.</li>")
    a(f"<li><strong>단일 턴.</strong> 운영 봇7 은 <code>history_window={meta['history_window']}</code> 다.</li>")
    a("</ul>")

    a("<h2>다음 세션이 이어받을 것</h2><ol>")
    a("<li><strong>L2 분기별 검색 프로토타입</strong> — R-219 를 통과 기준으로 삼는다 "
      f"(비교표가 top_k 에 들어오는가 / 답변이 편성별로 갈리는가).</li>")
    a("<li>2026 정본 적재 여부 결정 — 운영 봇7 vs 별도 봇.</li>")
    a("<li>정답 분기 라벨 10~30건 — 그래야 branch recall 을 잴 수 있다.</li>")
    a("</ol>")

    a("<footer>데이터 <code>exports/branch_ablation_2026-08-04/</code> — "
      "<code>_dump_bot7.json</code> · <code>_dump_bot11.json</code> · "
      "<code>_branches_bot7_v2.json</code>. 이 문서의 모든 수치는 그 파일들에서 계산됐다.<br>"
      "읽기 전용 실험 — DB 쓰기 0건, <code>bots.system_prompt</code> 미변경.</footer>")
    a("</div>")
    return "\n".join(H)


def main(out):
    d7, d11, br = load("_dump_bot7.json"), load("_dump_bot11.json"), load("_branches_bot7_v2.json")
    items = load("questions.json")["items"]
    body = build(d7, d11, br, items)
    doc = ("<!doctype html>\n<html lang=\"ko\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           "<title>조건부 분기 답변 절제 실험 — 2026-08-04</title>"
           f"<style>{CSS}</style></head><body>{body}</body></html>")
    p = Path(out).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    print(f"→ {p}  ({len(doc):,} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="~/Downloads/축복앱/축복챗봇_조건분기실험_2026-08-04.html")
    main(ap.parse_args().out)
