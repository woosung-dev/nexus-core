# 요청3(정책 결정 에스컬레이션) 문서를 카드에서 생성한다 — API 호출 0, 읽기 전용.
#
# 무엇을 올리나
#   coverage != '충분' 인 문항. 즉 규정집 v20 · 공문 4종 · 대사전 v4 를 다 뒤져도
#   문서만으로는 답이 확정되지 않는 것들이다. 이건 코드로 못 고친다.
#
# 함께 싣는 교차 검증
#   관리자가 붙인 보완레벨(0 보완불필요 / 1 실무보완 / 2 가정국 정책결정 / 3 초과합의)과
#   우리가 문서에서 잰 coverage 를 맞대 본다. 둘이 어긋나면 둘 중 하나가 틀린 것이고,
#   그 자체가 질의 항목이 된다 — 값싸고 강력한 검증이라 반드시 표에 넣는다.
import asyncio
import json
import os
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import asyncpg  # type: ignore[import-not-found]  # noqa: E402

LEVEL_NAME: dict[object, str] = {
    0: "보완불필요", 1: "실무보완", 2: "가정국 정책결정", 3: "가정국 초과 합의", None: "미분류"}
RISK_RANK: dict[object, int] = {"상": 0, "중": 1}
OUT = DIR / "요청3_정책결정_에스컬레이션.md"


async def fetch(gids):
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
    c = await asyncpg.connect(url, ssl="require")
    rows = await c.fetch(
        "select id, question, risk, level, category, assignee, model_answer "
        "from redteam_question_groups where id = any($1::int[])", gids)
    await c.close()
    return {r["id"]: dict(r) for r in rows}


def main():
    cards = {int(k): v for k, v in json.loads((DIR / "_cards.json").read_text(encoding="utf-8")).items()}
    verify = {int(k): v for k, v in json.loads((DIR / "_verify.json").read_text(encoding="utf-8")).items()}
    ok = {g for g, v in verify.items() if v.get("ok")}

    meta = asyncio.run(fetch(sorted(cards)))
    esc = sorted(
        (g for g in cards if g in ok and cards[g].get("coverage") != "충분"),
        key=lambda g: (RISK_RANK.get(meta.get(g, {}).get("risk"), 9), g))

    # 레벨 ↔ coverage 교차표 — 어긋난 칸이 질의 대상이다.
    cross = {}
    for g in ok:
        lv = meta.get(g, {}).get("level")
        cov = cards[g].get("coverage")
        cross[(lv, cov)] = cross.get((lv, cov), 0) + 1

    # 관리자는 "정책결정 필요"(레벨 2·3)라 했는데 문서엔 근거가 있는 경우, 그리고 그 반대
    lv_hi_doc_ok = [g for g in ok if meta.get(g, {}).get("level") in (2, 3)
                    and cards[g].get("coverage") == "충분"]
    lv_lo_doc_gap = [g for g in ok if meta.get(g, {}).get("level") in (0, 1)
                     and cards[g].get("coverage") == "근거없음"]

    L = ["<!-- 문서만으로 답이 확정되지 않는 문항 — 가정행복국 결정 요청 -->",
         "# 정책 결정 요청 — 문서에 근거가 없는 문항 (2026-08-05)", "",
         "## 요약", "",
         f"레드팀 3주차 위험 상·중 **{len(ok)}문항**에 대해 규정집 v20 · 공문 4종 · "
         "대사전 v4 전문을 근거로 정답지를 만들었습니다.",
         f"그중 **{len(esc)}문항**은 문서를 다 뒤져도 답이 확정되지 않습니다. "
         "챗봇 개선으로는 풀리지 않고 **가정행복국의 판단**이 필요합니다.", "",
         "각 항목에 저희가 문서에서 확인한 데까지와, 무엇을 정해 주셔야 하는지를 적었습니다.", "",
         "---", "", "## 교차 확인 — 관리자 분류와 문서 실측이 맞는가", "",
         "관리자께서 붙이신 **보완레벨**과, 저희가 문서에서 잰 **근거 충분도**를 맞대 봤습니다.",
         "칸이 어긋나면 둘 중 하나가 틀린 것이라 그 자체가 확인 대상입니다.", "",
         "| 보완레벨 | 문서근거 충분 | 부분 | 근거없음 |", "|---|---|---|---|"]

    for lv in (0, 1, 2, 3, None):
        name = LEVEL_NAME[lv]
        cells = [cross.get((lv, c), 0) for c in ("충분", "부분", "근거없음")]
        if any(cells):
            L.append(f"| {lv if lv is not None else '—'} {name} | {cells[0]} | {cells[1]} | {cells[2]} |")

    L += ["", "**어긋난 칸**", ""]
    if lv_hi_doc_ok:
        L.append(f"- 레벨 2·3(정책결정)인데 문서에 근거가 있는 문항 **{len(lv_hi_doc_ok)}건** "
                 f"— 이미 문서로 풀렸을 수 있습니다: {', '.join(f'#{g}' for g in sorted(lv_hi_doc_ok))}")
    if lv_lo_doc_gap:
        L.append(f"- 레벨 0·1(실무선)인데 문서에 근거가 없는 문항 **{len(lv_lo_doc_gap)}건** "
                 f"— 실무 판단만으로는 못 정할 수 있습니다: {', '.join(f'#{g}' for g in sorted(lv_lo_doc_gap))}")
    if not (lv_hi_doc_ok or lv_lo_doc_gap):
        L.append("- 어긋난 칸 없음. 관리자 분류와 문서 실측이 일치합니다.")

    L += ["", "---", "", "## 결정 요청 항목", ""]

    for i, g in enumerate(esc, 1):
        m = meta.get(g, {})
        c = cards[g]
        L += [f"### {i}. {m.get('question', '')}", "",
              f"`#{g}` · 위험 **{m.get('risk') or '—'}** · "
              f"보완레벨 **{m.get('level') if m.get('level') is not None else '미분류'} "
              f"{LEVEL_NAME.get(m.get('level'), '미분류')}** · "
              f"문서근거 **{c.get('coverage')}** · 담당 {m.get('assignee') or '—'}", ""]

        if c.get("evidence"):
            L += ["**문서에서 확인된 데까지**", ""]
            for e in c["evidence"]:
                L.append(f"> [{e['doc']} {e['locator']}] {e['quote']}")
                L.append("")
        else:
            L += ["**문서에서 확인된 것이 없습니다.**", ""]

        if c.get("open_question"):
            L += ["**정해 주셔야 하는 것**", "", c["open_question"], ""]

        memo = (m.get("model_answer") or "").strip()
        if memo:
            L += [f"**레드팀·검토자 메모(참고)** — {memo[:400]}", ""]

        L += ["**회신란**", "", "```", "", "```", "", "---", ""]

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"에스컬레이션 {len(esc)}건 → {OUT.name}")
    print(f"  교차 불일치: 레벨2·3인데 근거있음 {len(lv_hi_doc_ok)}건 · "
          f"레벨0·1인데 근거없음 {len(lv_lo_doc_gap)}건")


if __name__ == "__main__":
    main()
