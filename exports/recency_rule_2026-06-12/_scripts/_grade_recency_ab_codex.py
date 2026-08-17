# 프로브_결과_raw.json의 규칙 전(base)/후(rule) 응답을 codex CLI로 A/B 비교 채점 → 채점_AB.json + 통과 판정
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = Path("/Users/woosung/project/agy-project/nexus-core")
IN = ROOT / "프로브_결과_raw.json"
OUT = ROOT / "채점_AB.json"
REASONING = "medium"

INSTRUCTION = (
    "너는 가정연합 축복 안내 챗봇의 프롬프트 변경을 검증하는 엄격한 평가자다.\n"
    "<stdin> JSON 배열의 각 항목에는 같은 질문에 대한 A(변경 전)와 B(변경 후: '문서 제목의 연도가 최신인 문서 우선' 규칙 추가) 응답이 있다.\n"
    "설명·서론 없이 입력과 같은 개수·순서로 JSON 배열만 출력하라. 각 원소 필드:\n"
    "qid(그대로), verdict(B_better|same|B_worse), latest_priority(true/false/null: B가 제목 연도가 최신인 문서 기준으로 답했는가 — C문항만, 판단 불가면 null), "
    "change_noted(true/false/null: 기준 변경이 있는 주제에서 B가 '변경되었다'를 명시했는가 — 해당 없으면 null), "
    "source_cited(true/false: B가 근거 문서명 또는 연도를 표기했는가), "
    "regression(true/false: B가 A보다 사실 정확성·공감 톤·자연스러움에서 나빠졌는가), "
    "reason(한 줄 한국어).\n"
    "판정 원칙: C(충돌) 문항은 최신 문서 기준 채택·변경 명시·출처 표기가 됐으면 B_better, 그대로면 same, 사실이 틀어지거나 어색해졌으면 B_worse. "
    "G(일반) 문항은 B가 A와 동등하면 same이고, 규칙 추가로 공감 톤이 죽거나 불필요한 연도 나열로 어색해졌으면 B_worse다. "
    "retrieved_titles는 모델이 본 문서 목록 참고용이다."
)


def extract_json_array(text):
    t = re.sub(r"^```(?:json)?", "", text.strip()).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    return json.loads(t[i:j + 1])


def codex_grade(items):
    p = subprocess.run(
        ["codex", "exec", INSTRUCTION, "-s", "read-only",
         "-c", f'model_reasoning_effort="{REASONING}"'],
        input=json.dumps(items, ensure_ascii=False),
        capture_output=True, text=True, cwd=str(REPO), timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-300:]}")
    return extract_json_array(p.stdout)


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    by_bot = defaultdict(dict)
    for r in data["results"]:
        e = by_bot[r["bot_id"]].setdefault(r["qid"], {"qid": r["qid"], "qtype": r["qtype"], "q": r["q"]})
        e[f"{r['variant']}_answer"] = r["answer"]
        e[f"{r['variant']}_titles"] = r["titles"]

    graded, summary = {}, {}
    for bot_id, qmap in sorted(by_bot.items()):
        items = [
            {"qid": q["qid"], "qtype": q["qtype"], "question": q["q"],
             "A_변경전": q.get("base_answer", ""), "B_변경후": q.get("rule_answer", ""),
             "retrieved_titles_B": q.get("rule_titles", [])}
            for q in sorted(qmap.values(), key=lambda x: x["qid"])
        ]
        print(f"bot{bot_id} — codex 채점 {len(items)}문항…")
        res = codex_grade(items)
        graded[str(bot_id)] = res
        c = [r for r, it in zip(res, items) if it["qid"].startswith("C")]
        g = [r for r, it in zip(res, items) if it["qid"].startswith("G")]
        s = {
            "C_better": sum(1 for r in c if r["verdict"] == "B_better"),
            "C_same": sum(1 for r in c if r["verdict"] == "same"),
            "C_worse": sum(1 for r in c if r["verdict"] == "B_worse"),
            "G_worse": sum(1 for r in g if r["verdict"] == "B_worse"),
            "source_cited": sum(1 for r in res if r.get("source_cited")),
            "regression": sum(1 for r in res if r.get("regression")),
        }
        s["pass"] = s["G_worse"] <= 1 and s["C_better"] >= s["C_worse"]
        summary[str(bot_id)] = s
        print(f"  → C: better {s['C_better']} / same {s['C_same']} / worse {s['C_worse']} · "
              f"G_worse {s['G_worse']} · 출처표기 {s['source_cited']}/15 · PASS={s['pass']}")

    OUT.write_text(json.dumps({"meta": {"grader": "codex CLI", "reasoning": REASONING, "date": "2026-06-12"},
                               "summary": summary, "graded": graded},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장: {OUT.name} · 종합 PASS = {all(s['pass'] for s in summary.values())}")


if __name__ == "__main__":
    main()
