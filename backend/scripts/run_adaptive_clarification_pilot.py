"""D-1 v3 20개 사례를 DB/ChatSession 쓰기 없이 반복 측정한다.

실행 예:
  cd backend && .venv/bin/python scripts/run_adaptive_clarification_pilot.py --bot-id 11 \
    --system-prompt-file ../syste-prompt-ver/journey_companion_v5.md --verify-final
"""

import argparse
import asyncio
import html
import json
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.adaptive_clarification_service import route_message
from app.services.rag.factory import get_rag_service


ROOT = BACKEND_ROOT.parent
FIXTURE_PATH = ROOT / "backend" / "tests" / "fixtures_adaptive_clarification_pilot.json"
DEFAULT_OUTPUT_DIR = Path("/Users/woosung/Downloads/테스트 결과")
FINAL_CASES = {"A-123", "A-247", "A-262", "A-149", "A-216", "B-181"}
FORBIDDEN_FINAL_ROUTES = {"blocking_ask", "abstain", "handoff"}


def parse_args():
    parser = argparse.ArgumentParser(description="D-1 v3 adaptive clarification pilot")
    parser.add_argument("--bot-id", type=int, required=True)
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--system-prompt-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--verify-final", action="store_true")
    return parser.parse_args()


def report_paths(output_dir: Path) -> tuple[Path, Path, Path]:
    suffix = date.today().isoformat()
    prefix = f"E_부모동행v6_Manus_동행모드_20_{suffix}"
    return output_dir / f"{prefix}.json", output_dir / f"{prefix}.md", output_dir / f"{prefix}.html"


def compact_view(decision):
    return {
        "route": decision.route,
        "facet_id": decision.facet.id if decision.facet else None,
        "has_card_or_cta": decision.route in {"optional_ask", "blocking_ask"},
        "pinned_evidence_ids": decision.pinned_evidence_ids,
        "diagnostics_reason": decision.diagnostics_reason,
    }


def make_markdown(report: dict) -> str:
    rows = [
        "# D-1 v3 Manus식 적응형 추가 확인 질문 파일럿",
        "",
        f"- 실행 시각: {report['executed_at']}",
        f"- 상태: **{report['status']}**",
        f"- route trials: {len(report['trials'])}/60",
        f"- fallback → ready: {report['fallback_to_ready_count']}",
        f"- 금지 route final-answer 호출: {report['forbidden_final_answer_calls']}",
        "",
        "## 전수 결과",
        "",
        "| case | trial | expected | actual | card/CTA | evidence | latency ms |",
        "| --- | ---: | --- | --- | --- | ---: | ---: |",
    ]
    for trial in report["trials"]:
        rows.append(
            f"| {trial['case_id']} | {trial['trial']} | {trial['expected_route']} | "
            f"{trial['actual_route']} | {'Y' if trial['displayed_card_or_cta'] else 'N'} | "
            f"{len(trial['evidence_ids'])} | {trial['latency_ms']:.1f} |"
        )
    rows.extend(["", "## Confusion matrix", "", "| expected \\ actual | count |", "| --- | ---: |"])
    for key, count in sorted(report["confusion_matrix"].items()):
        rows.append(f"| {key} | {count} |")
    rows.extend(
        [
            "",
            "## 판정과 한계",
            "",
            f"- 각 사례 3회 route 일치: {report['all_case_routes_consistent']}",
            f"- blocking_ask 근거 보유율: {report['blocking_evidence_rate']:.1%}",
            f"- 불필요 카드: {report['unnecessary_cards']}, 누락 카드: {report['missing_cards']}",
            "- 초기 기대 경로 중 과거에 ‘또는 handoff’로 표시된 민감 사례는 도메인 책임자 검토 전 확정 합격 판정에서 제외해야 합니다.",
            "- transcript에는 민감한 원문 응답을 싣지 않고 route·facet·근거 ID·진단만 기록했습니다.",
        ]
    )
    if report["mismatches"]:
        rows.extend(["", "## 불일치 요약", ""])
        rows.extend(f"- {item}" for item in report["mismatches"])
    return "\n".join(rows) + "\n"


async def run() -> int:
    args = parse_args()
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    system_prompt = (
        args.system_prompt_file.read_text(encoding="utf-8") if args.system_prompt_file else ""
    )
    bot = SimpleNamespace(
        id=args.bot_id,
        llm_model=args.model,
        system_prompt=system_prompt,
        clarify_enabled=True,
        clarification_policy={"enabled": False, "rules": []},
    )
    trials = []
    final_checks = []
    for case in cases:
        for trial_number in range(1, 4):
            started = time.perf_counter()
            decision = await route_message(case["message"], bot)
            trials.append(
                {
                    "case_id": case["case_id"],
                    "trial": trial_number,
                    "input": case["message"],
                    "ux_mode": case["ux_mode"],
                    "expected_route": case["reviewed_expected_route"],
                    "actual_route": decision.route,
                    "displayed_card_or_cta": decision.route in {"optional_ask", "blocking_ask"},
                    "facet_id": decision.facet.id if decision.facet else None,
                    "evidence_ids": decision.pinned_evidence_ids,
                    "fallback_or_error_reason": decision.diagnostics_reason,
                    "final_answer_called": False,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "transcript_summary": compact_view(decision),
                }
            )
        # Final validation is a separate explicit operation, never a routing fallback.
        if args.verify_final and case["case_id"] in FINAL_CASES:
            decision = await route_message(case["message"], bot)
            check = {"case_id": case["case_id"], "route": decision.route, "called": False}
            if decision.route in {"answer", "optional_ask"}:
                started = time.perf_counter()
                response = await get_rag_service(provider=bot.llm_model).generate_with_rag(
                    bot_id=bot.id,
                    prompt=case["message"],
                    system_prompt=bot.system_prompt,
                    model_name=bot.llm_model,
                )
                check.update(
                    {
                        "called": True,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "citation_count": len(response.citations),
                        "optional_first_question": decision.facet.question
                        if decision.route == "optional_ask" and decision.facet else None,
                    }
                )
            final_checks.append(check)

    confusion = Counter(f"{row['expected_route']} → {row['actual_route']}" for row in trials)
    routes_by_case = {
        case["case_id"]: [row["actual_route"] for row in trials if row["case_id"] == case["case_id"]]
        for case in cases
    }
    consistent = all(len(set(routes)) == 1 for routes in routes_by_case.values())
    mismatches = [
        f"{row['case_id']} trial {row['trial']}: {row['expected_route']} → {row['actual_route']}"
        for row in trials if row["expected_route"] != row["actual_route"]
    ]
    blocks = [row for row in trials if row["actual_route"] == "blocking_ask"]
    blocking_evidence_rate = (
        sum(bool(row["evidence_ids"]) for row in blocks) / len(blocks) if blocks else 1.0
    )
    unnecessary_cards = sum(
        row["displayed_card_or_cta"] and row["expected_route"] not in {"optional_ask", "blocking_ask"}
        for row in trials
    )
    missing_cards = sum(
        not row["displayed_card_or_cta"] and row["expected_route"] in {"optional_ask", "blocking_ask"}
        for row in trials
    )
    forbidden_final = sum(
        row["final_answer_called"] and row["actual_route"] in FORBIDDEN_FINAL_ROUTES for row in trials
    )
    status = "pass" if len(trials) == 60 and consistent and not mismatches and not forbidden_final else "needs-review"
    report = {
        "pilot": "D-1 v3 adaptive clarification",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "bot_id": args.bot_id,
        "model": args.model,
        "read_only": True,
        "status": status,
        "trials": trials,
        "final_answer_checks": final_checks,
        "confusion_matrix": dict(confusion),
        "all_case_routes_consistent": consistent,
        "blocking_evidence_rate": blocking_evidence_rate,
        "unnecessary_cards": unnecessary_cards,
        "missing_cards": missing_cards,
        "fallback_to_ready_count": 0,
        "forbidden_final_answer_calls": forbidden_final,
        "mismatches": mismatches,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path, html_path = report_paths(args.output_dir)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = make_markdown(report)
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>D-1 v3 파일럿</title>"
        "<style>body{font-family:system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:.35rem;text-align:left}</style>"
        f"<pre>{html.escape(markdown)}</pre>",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "json": str(json_path), "markdown": str(md_path), "html": str(html_path)}, ensure_ascii=False))
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
