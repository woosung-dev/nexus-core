# 위험도 상·중 + 적절성 1·2점 항목만 추려 인쇄용(밝은 배경) HTML로 만드는 빌드 스크립트
import json
import pathlib

from _build_report import CATEGORIES  # 사유별 분류(수기) 재사용

OUT_DIR = pathlib.Path(__file__).parent
DATA = OUT_DIR / "_data" / "responses.json"
OUT_HTML = OUT_DIR / "3주차_레드팀_CD_인쇄본.html"

GROUP_META = {
    "상": {"label": "위험도 상", "sub": "즉시 차단·수정 검토"},
    "중": {"label": "위험도 중", "sub": "정보 누락·회피·규정 불일치"},
    "저점": {"label": "적절성 1·2점", "sub": "적절성·유용성 최저점"},
}


def build_id_tags():
    """각 응답 id에 붙일 사유 카테고리 태그를 그룹별로 역매핑."""
    id_cats = {}  # id -> [(group_key, cat_name), ...]
    for gkey, group in CATEGORIES.items():
        for cat in group["cats"]:
            for i in cat["ids"]:
                id_cats.setdefault(i, []).append((gkey, cat["name"]))
    return id_cats


def severity_tags(d):
    """위험도/점수 기반의 핵심 태그."""
    tags = []
    if d["risk"] == "상":
        tags.append(("sev sang", "위험도 상"))
    elif d["risk"] == "중":
        tags.append(("sev jung", "위험도 중"))
    sc = d.get("score")
    if sc == 1:
        tags.append(("sc p1", "적절성 1점"))
    elif sc == 2:
        tags.append(("sc p2", "적절성 2점"))
    return tags


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {d["id"]: d for d in data}
    id_cats = build_id_tags()

    # 인쇄 대상 = CATEGORIES에 등장하는 모든 id의 합집합(상∪중∪저점), 중복 제거
    target_ids = sorted(id_cats.keys())

    # 정렬: 위험도(상0·중1·기타2) → 점수 오름차순 → id
    risk_rank = {"상": 0, "중": 1, "하": 2, "없음": 3}
    target_ids.sort(key=lambda i: (
        risk_rank.get(by_id[i]["risk"], 9),
        by_id[i]["score"] if by_id[i]["score"] is not None else 9,
        i,
    ))

    n_sang = sum(1 for i in target_ids if by_id[i]["risk"] == "상")
    n_jung = sum(1 for i in target_ids if by_id[i]["risk"] == "중")
    n_low = sum(1 for i in target_ids if by_id[i]["score"] in (1, 2))

    # ---- 사유별 분류 요약(상/중/저점) ----
    summary_html = ""
    for gkey in ["상", "중", "저점"]:
        group = CATEGORIES[gkey]
        gm = GROUP_META[gkey]
        cats = sorted(group["cats"], key=lambda c: -len(c["ids"]))
        rows = "".join(
            f'<div class="srow"><span class="scnt">{len(c["ids"])}</span>'
            f'<span class="snm">{esc(c["name"])}</span>'
            f'<span class="sin">{esc(c["insight"])}</span></div>'
            for c in cats
        )
        tot = sum(len(c["ids"]) for c in cats)
        summary_html += (
            f'<div class="sgroup g-{gkey}">'
            f'<div class="sgh"><b>{esc(gm["label"])}</b> '
            f'<span class="sgsub">{esc(gm["sub"])} · 총 {tot}건 · {len(cats)}개 범주</span></div>'
            f'{rows}</div>'
        )

    # ---- 항목 상세 ----
    items_html = ""
    for i in target_ids:
        d = by_id[i]
        tags = severity_tags(d)
        # 사유 카테고리 태그(그룹별 색)
        for gkey, name in id_cats.get(i, []):
            tags.append((f"cat c-{gkey}", name))
        tag_html = "".join(f'<span class="tag {cls}">{esc(t)}</span>' for cls, t in tags)
        sc_txt = f'{d["score"]:g}점' if d["score"] is not None else "-"
        items_html += f"""
<article class="item">
  <div class="ihead">
    <span class="qid">#{d["id"]}</span>
    {tag_html}
    <span class="meta">{esc(d["evaluator"])} · 적절성 {sc_txt} · 선호 {esc(d["prefRaw"] or "-")}</span>
  </div>
  <div class="q">{esc(d["question"])}</div>
  <div class="resp C"><h5>챗봇 C 응답</h5><div class="t">{esc(d["respC"]) or "—"}</div></div>
  <div class="resp D"><h5>챗봇 D 응답</h5><div class="t">{esc(d["respD"]) or "—"}</div></div>
  <div class="fb">
    {fb("좋았던 점", d["good"])}
    {fb("아쉬운 점", d["bad"])}
    {fb("보완·제안", d["suggest"])}
    {fb("위험도(원문)", d["riskRaw"])}
    {fb("기타 의견", d["etc"])}
  </div>
</article>"""

    html = TEMPLATE.format(
        n_total=len(target_ids),
        n_sang=n_sang, n_jung=n_jung, n_low=n_low,
        summary=summary_html,
        items=items_html,
    )
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"인쇄 대상 {len(target_ids)}건(상{n_sang}·중{n_jung}·1·2점{n_low}) → {OUT_HTML}")


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fb(k, v):
    return f'<div class="row"><span class="k">{k}</span> <span class="v">{esc(v)}</span></div>' if v else ""


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>3주차 레드팀 · 위험·저점 항목 인쇄본</title>
<style>
:root{{
  --ink:#1c2330; --mut:#5b6573; --line:#d3d9e0; --soft:#f5f7f9;
  --sang:#c0322b; --jung:#b3760b; --p1:#a31616; --p2:#a85410;
  --C:#138a76; --D:#6240c4;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:#fff;color:var(--ink)}}
body{{font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",-apple-system,BlinkMacSystemFont,sans-serif;
  font-size:10.5pt;line-height:1.55}}
.wrap{{max-width:860px;margin:0 auto;padding:22px 26px}}
h1{{font-size:17pt;margin:0 0 3px}}
.lead{{color:var(--mut);font-size:9.5pt;margin:0 0 14px}}
.kpis{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}}
.kpi{{border:1px solid var(--line);border-radius:8px;padding:7px 13px;min-width:96px}}
.kpi .b{{font-size:16pt;font-weight:700;line-height:1.1}}
.kpi .l{{font-size:8.5pt;color:var(--mut)}}
.h2{{font-size:12pt;font-weight:700;margin:20px 0 8px;padding-bottom:4px;border-bottom:2px solid var(--ink)}}
/* 사유 요약 */
.sgroup{{border:1px solid var(--line);border-left-width:4px;border-radius:8px;padding:9px 12px;margin:0 0 9px}}
.sgroup.g-상{{border-left-color:var(--sang)}}
.sgroup.g-중{{border-left-color:var(--jung)}}
.sgroup.g-저점{{border-left-color:var(--p2)}}
.sgh{{font-size:10.5pt;margin-bottom:5px}}
.sgsub{{color:var(--mut);font-size:8.7pt;font-weight:400}}
.srow{{display:flex;gap:8px;align-items:baseline;font-size:9pt;padding:2px 0;border-top:1px dotted #e6eaef}}
.srow:first-of-type{{border-top:none}}
.scnt{{flex:0 0 26px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums}}
.snm{{flex:0 0 168px;font-weight:600}}
.sin{{flex:1;color:#42505f}}
/* 항목 상세 */
.item{{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:0 0 11px}}
.ihead{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
.qid{{font-weight:800;font-size:11pt}}
.meta{{color:var(--mut);font-size:8.7pt;margin-left:auto}}
.tag{{font-size:8pt;padding:1px 7px;border-radius:11px;border:1px solid transparent;white-space:nowrap}}
.tag.sev.sang{{background:#fdeceb;color:var(--sang);border-color:#f0b6b2}}
.tag.sev.jung{{background:#fbf1de;color:var(--jung);border-color:#ecd09a}}
.tag.sc.p1{{background:#fae5e5;color:var(--p1);border-color:#eeb3b3}}
.tag.sc.p2{{background:#fbeadb;color:var(--p2);border-color:#eccaa9}}
.tag.cat{{background:#eef1f6;color:#3a4658;border-color:#d3dae4;font-size:7.8pt}}
.tag.cat.c-상{{background:#fcf0ef}}
.tag.cat.c-중{{background:#fcf6ea}}
.q{{font-weight:600;font-size:10.6pt;margin:7px 0 8px;padding-left:9px;border-left:3px solid var(--ink)}}
.resp{{border:1px solid #e4e8ee;border-left-width:3px;border-radius:6px;background:var(--soft);
  padding:6px 11px;margin:6px 0}}
.resp.C{{border-left-color:var(--C)}}
.resp.D{{border-left-color:var(--D)}}
.resp h5{{margin:0 0 3px;font-size:8.5pt;color:var(--mut);font-weight:700;letter-spacing:.02em}}
.resp.C h5{{color:var(--C)}}
.resp.D h5{{color:var(--D)}}
.resp .t{{white-space:pre-wrap;word-break:break-word;font-size:9.2pt;line-height:1.5;color:#222b38}}
.fb{{margin-top:7px;padding-top:6px;border-top:1px dotted #e0e5eb}}
.fb .row{{font-size:9.3pt;margin:2px 0;white-space:pre-wrap}}
.fb .k{{font-weight:700;color:#3a4250}}
.legend{{font-size:8.7pt;color:var(--mut);margin:4px 0 0}}
@page{{size:A4;margin:13mm 12mm}}
@media print{{
  .wrap{{max-width:none;padding:0}}
  .item{{break-inside:auto}}
  .ihead,.q{{break-inside:avoid;break-after:avoid}}
  .resp h5{{break-after:avoid}}
  .sgroup,.kpi{{break-inside:avoid}}
  a{{color:inherit;text-decoration:none}}
}}
</style>
</head>
<body>
<div class="wrap">
  <h1>3주차 레드팀 · 위험·저점 항목 집중 검토 (인쇄본)</h1>
  <p class="lead">라이브 Neon C(id6)·D(id7) 블라인드 평가 · 위험도 상·중 및 적절성 1·2점 항목만 발췌 · 중복 항목은 태그 다중 표기</p>
  <div class="kpis">
    <div class="kpi"><div class="b">{n_total}</div><div class="l">검토 대상(고유)</div></div>
    <div class="kpi"><div class="b">{n_sang}</div><div class="l">위험도 상</div></div>
    <div class="kpi"><div class="b">{n_jung}</div><div class="l">위험도 중</div></div>
    <div class="kpi"><div class="b">{n_low}</div><div class="l">적절성 1·2점</div></div>
  </div>

  <div class="h2">사유별 분류 요약</div>
  {summary}

  <div class="h2">항목 상세 (위험도 → 점수 순)</div>
  <p class="legend">태그 = 위험도(상·중) · 적절성 점수(1·2점) · 사유 범주. 한 항목이 여러 그룹에 걸치면 태그를 모두 표기.</p>
  {items}
</div>
</body>
</html>"""


if __name__ == "__main__":
    main()
