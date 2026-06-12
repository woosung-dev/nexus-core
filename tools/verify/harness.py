# 프롬프트 변경 검증 1명령 하네스 — 프로브(멀티샘플)→codex 채점→분산 분류→베이스라인 비교
"""
사용법 (레포 루트에서):
  uv run --project backend python tools/verify/harness.py run --questions crisis --samples 3 --bots 5,3 \
      --rule-file 규칙.md --label rule-v4
  uv run --project backend python tools/verify/harness.py grade --raw <raw.json> --questions crisis
  uv run --project backend python tools/verify/harness.py compare --a <runDirA> --b <runDirB>
  uv run --project backend python tools/verify/harness.py list [--questions crisis]

설계:
- --rule-file 있으면 A/B 모드(variants=base,rule), 없으면 단순 평가 모드(variant=current).
- 문항당 samples 회 반복 생성 → codex 채점은 (bot, sample)당 1콜 → 샘플 간 verdict 일치도로 분산 분류.
- 분산 3단: stable(만장일치)/mixed(불일치·worse없음)/unstable(불일치·worse포함). 품질 게이트는 stable+mixed만,
  치명 게이트(flag)는 전 샘플. unstable 이 max_unstable 초과면 INCONCLUSIVE.
- dev DB(localhost) 읽기 전용으로 봇 프롬프트만 로드. Neon 접근 금지(가드).
- 채점은 codex CLI(구독) — OpenAI API 과금 경로 없음.
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
QSET_DIR = HERE / "questionsets"
ARTIFACT_ROOT = REPO / "exports" / "verify"
BACKEND = REPO / "backend"

BOT_LABELS = {5: "블레싱 가", 3: "블레싱 나"}
MODEL = "gemini-3.1-flash-lite"
SLEEP_BETWEEN_CALLS = 2.5
CODEX_REASONING = "medium"


# ---------------------------------------------------------------- 환경/DB

def _db_url_localhost() -> str:
    """backend/.env 의 활성 DATABASE_URL 을 localhost 로 강제해 반환 (Neon 차단)."""
    for line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#") or not s.startswith("DATABASE_URL"):
            continue
        v = s.split("=", 1)[1].strip().strip('"').strip("'")
        if "neon" in v.lower():
            continue
        v = re.sub(r"@[^:/]+", "@localhost", v, count=1)  # 호스트만 localhost 로
        assert "neon" not in v.lower(), "Neon 라이브 접근 금지 — dev localhost 만 허용"
        return v
    raise RuntimeError("backend/.env 에서 localhost DATABASE_URL 을 찾지 못함")


def _inject_env() -> None:
    """app.core.config(get_settings) 가 cwd 와 무관하게 동작하도록 .env 값을 환경에 주입."""
    for line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if "neon" in v.lower():
            continue
        os.environ.setdefault(k, v)


def _app_imports():
    sys.path.insert(0, str(BACKEND))
    _inject_env()
    from app.core.config import get_settings
    from app.services.llm.gemini import _get_genai_client

    return get_settings, _get_genai_client


async def _load_prompts(bots: list[int]) -> dict[int, str]:
    import asyncpg

    url = _db_url_localhost().replace("+asyncpg", "")
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            "SELECT id, system_prompt FROM bots WHERE id = ANY($1::int[])", bots
        )
        return {r["id"]: r["system_prompt"] for r in rows}
    finally:
        await conn.close()


# ---------------------------------------------------------------- 프로브

async def _find_store(client, name):
    async for s in await client.aio.file_search_stores.list():
        if s.display_name == name:
            return s.name
    raise RuntimeError(f"file_search store '{name}' 없음")


async def _call(client, store, bot_id, system_prompt, question, settings, types):
    cfg = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1500,
        system_instruction=system_prompt,
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store],
                    metadata_filter=f"bot_id={bot_id}",
                    top_k=settings.RAG_TOP_K,
                )
            )
        ],
    )
    for attempt in range(6):
        try:
            r = await client.aio.models.generate_content(
                model=MODEL, contents=question, config=cfg
            )
            titles: list[str] = []
            try:
                for c in r.candidates[0].grounding_metadata.grounding_chunks or []:
                    if c.retrieved_context and c.retrieved_context.title not in titles:
                        titles.append(c.retrieved_context.title)
            except Exception:
                pass
            return {"answer": r.text or "[빈 응답]", "titles": titles}
        except Exception as e:
            msg = str(e)
            if any(k in msg for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500")):
                wait = 15 * (attempt + 1)
                print(f"    쿼터/일시 오류 — {wait}s 대기 ({attempt + 1}/6)", flush=True)
                await asyncio.sleep(wait)
                continue
            return {"answer": f"[ERROR] {msg[:300]}", "titles": []}
    return {"answer": "[ERROR] 재시도 소진", "titles": []}


async def _probe(qset, bots, samples, rule_text, raw_path, meta):
    from google.genai import types

    get_settings, _get_genai_client = _app_imports()
    settings = get_settings()
    client = _get_genai_client()
    store = await _find_store(client, settings.FILE_SEARCH_STORE_NAME)
    prompts = await _load_prompts(bots)
    meta["store"] = store
    meta["top_k"] = settings.RAG_TOP_K
    meta["prompt_chars"] = {str(b): len(prompts[b]) for b in bots}
    print(f"store={store} / 프롬프트: " + ", ".join(f"id{b} {len(prompts[b])}자" for b in bots))

    variants = [("base", ""), ("rule", rule_text)] if rule_text is not None else [("current", "")]
    results = []
    total = len(bots) * len(variants) * len(qset["questions"]) * samples
    n = 0
    for bot_id in bots:
        for vname, vtext in variants:
            sp = prompts[bot_id] + (vtext or "")
            for q in qset["questions"]:
                for s in range(samples):
                    n += 1
                    print(f"[{n}/{total}] bot{bot_id} {vname} {q['qid']} s{s}", flush=True)
                    r = await _call(client, store, bot_id, sp, q["question"], settings, types)
                    results.append(
                        {
                            "bot_id": bot_id,
                            "variant": vname,
                            "qid": q["qid"],
                            "qtype": q["qtype"],
                            "q": q["question"],
                            "expect": q.get("expect", ""),
                            "sample": s,
                            **r,
                        }
                    )
                    await asyncio.sleep(SLEEP_BETWEEN_CALLS)
        # 봇 단위 중간 저장 (크래시 대비 부분 보존)
        raw_path.write_text(
            json.dumps({"meta": meta, "rule": (rule_text.strip() if rule_text else None), "results": results},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    return results


# ---------------------------------------------------------------- 채점 (codex)

def _extract_json_array(text):
    t = re.sub(r"^```(?:json)?", "", text.strip()).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    return json.loads(t[i : j + 1])


def _codex(instruction, items):
    p = subprocess.run(
        ["codex", "exec", instruction, "-s", "read-only",
         "-c", f'model_reasoning_effort="{CODEX_REASONING}"'],
        input=json.dumps(items, ensure_ascii=False),
        capture_output=True, text=True, cwd=str(REPO), timeout=600,
    )
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-300:]}")
    return _extract_json_array(p.stdout)


def _detect_mode(raw):
    if raw.get("meta", {}).get("mode"):
        return raw["meta"]["mode"]
    return "ab" if any(r["variant"] == "rule" for r in raw["results"]) else "single"


def _grade(raw, qset):
    """raw → graded[bot][sample] = [채점 원소]. mode 도 함께 반환. 레거시 raw(sample 없음)는 sample=0."""
    mode = _detect_mode(raw)
    key = "instruction_ab" if mode == "ab" else "instruction_single"
    instruction = "\n".join(qset["grader"][key])

    grouped: dict = defaultdict(lambda: defaultdict(dict))  # [bot][sample][qid]
    for r in raw["results"]:
        s = r.get("sample", 0)
        cell = grouped[r["bot_id"]][s].setdefault(
            r["qid"], {"qid": r["qid"], "qtype": r["qtype"], "q": r["q"], "expect": r.get("expect", "")}
        )
        cell[r["variant"]] = {"answer": r["answer"], "titles": r.get("titles", [])}

    graded: dict = defaultdict(dict)
    for bot in sorted(grouped):
        for s in sorted(grouped[bot]):
            qmap = grouped[bot][s]
            ordered = sorted(qmap.values(), key=lambda x: x["qid"])
            if mode == "ab":
                items = [
                    {"qid": q["qid"], "qtype": q["qtype"], "question": q["q"], "expect": q["expect"],
                     "A_변경전": q.get("base", {}).get("answer", ""),
                     "B_변경후": q.get("rule", {}).get("answer", ""),
                     "retrieved_titles_B": q.get("rule", {}).get("titles", [])}
                    for q in ordered
                ]
            else:
                items = [
                    {"qid": q["qid"], "qtype": q["qtype"], "question": q["q"], "expect": q["expect"],
                     "현행응답": q.get("current", {}).get("answer", "")}
                    for q in ordered
                ]
            print(f"bot{bot} s{s} — codex 채점 {len(items)}문항…", flush=True)
            graded[bot][s] = _codex(instruction, items)
    return graded, mode


# ---------------------------------------------------------------- 집계

def _is_worse(v):
    return v in ("B_worse", "fail")


def _is_better(v):
    return v == "B_better"


def _aggregate(graded, qset, mode):
    flag_fields = qset["grader"]["flag_fields"]
    gates = qset["grader"]["gates"]
    qtype_by_qid = {q["qid"]: q["qtype"] for q in qset["questions"]}

    bots_summary = {}
    overall_pass = True
    for bot, samples in graded.items():
        verdicts = defaultdict(list)
        flags_total = {f: 0 for f in flag_fields}
        expect_a = expect_b = expect_single = 0
        for _s, elems in sorted(samples.items()):
            for e in elems:
                verdicts[e["qid"]].append(e.get("verdict"))
                for f in flag_fields:
                    if e.get(f) is True:
                        flags_total[f] += 1
                if mode == "ab":
                    expect_a += 1 if e.get("expect_met_A") else 0
                    expect_b += 1 if e.get("expect_met_B") else 0
                else:
                    expect_single += 1 if e.get("expect_met") else 0

        per_qid, unstable, mixed = {}, {}, {}
        for qid, vs in verdicts.items():
            if len(set(vs)) == 1:
                stability = "stable"
            elif any(_is_worse(v) for v in vs):
                stability = "unstable"
            else:
                stability = "mixed"
            agg = Counter(vs).most_common(1)[0][0]
            per_qid[qid] = {"qtype": qtype_by_qid.get(qid), "samples": vs, "agg": agg, "stability": stability}
            if stability == "unstable":
                unstable[qid] = vs
            elif stability == "mixed":
                mixed[qid] = vs

        # 품질 게이트는 stable+mixed(=unstable 제외)의 대표 verdict 로만 평가
        scored = {q: i for q, i in per_qid.items() if i["stability"] != "unstable"}
        worse_qids = [q for q, i in scored.items() if _is_worse(i["agg"])]
        better_qids = [q for q, i in scored.items() if _is_better(i["agg"])]

        violations = []
        if gates.get("max_worse_total") is not None and len(worse_qids) > gates["max_worse_total"]:
            violations.append(f"worse_total {len(worse_qids)}>{gates['max_worse_total']}")
        for qt, mx in (gates.get("max_worse_by_qtype") or {}).items():
            c = sum(1 for q in worse_qids if qtype_by_qid.get(q) == qt)
            if c > mx:
                violations.append(f"worse[{qt}] {c}>{mx}")
        for qt in gates.get("require_better_gte_worse_qtypes") or []:
            b = sum(1 for q in better_qids if qtype_by_qid.get(q) == qt)
            w = sum(1 for q in worse_qids if qtype_by_qid.get(q) == qt)
            if b < w:
                violations.append(f"better<worse[{qt}] {b}<{w}")
        if gates.get("expect_b_gte_a") and mode == "ab" and expect_b < expect_a:
            violations.append(f"expect_B<A {expect_b}<{expect_a}")
        for f in gates.get("zero_flags_any_sample") or []:
            if flags_total.get(f, 0) > 0:
                violations.append(f"flag {f}={flags_total[f]}")

        max_unstable = gates.get("max_unstable")
        inconclusive = max_unstable is not None and len(unstable) > max_unstable
        gate_pass = (not violations) and (not inconclusive)
        if not gate_pass:
            overall_pass = False

        neutral = sum(1 for q, i in scored.items() if not _is_worse(i["agg"]) and not _is_better(i["agg"]))
        bots_summary[str(bot)] = {
            "label": BOT_LABELS.get(bot, str(bot)),
            "gate": {"pass": gate_pass, "inconclusive": inconclusive, "violations": violations},
            "agg_verdicts": {"better": len(better_qids), "neutral": neutral, "worse": len(worse_qids)},
            "expect": ({"A": expect_a, "B": expect_b} if mode == "ab" else {"single": expect_single}),
            "flags_total": flags_total,
            "unstable": unstable,
            "mixed": mixed,
            "per_qid": per_qid,
        }
    return {"bots": bots_summary, "overall_pass": overall_pass}


# ---------------------------------------------------------------- 비교 리포트

def _gate_word(info):
    g = info.get("gate", {})
    if g.get("pass"):
        return "PASS"
    return "INCONCLUSIVE" if g.get("inconclusive") else "FAIL"


def _compare_md(curr, prev, qs_name, curr_label, prev_label):
    out = [f"# {qs_name}: {curr_label}  vs  {prev_label or '(직전 없음)'}", ""]
    for bot, cinfo in sorted(curr["bots"].items()):
        pinfo = (prev or {}).get("bots", {}).get(bot)
        pg = _gate_word(pinfo) if pinfo else "—"
        out.append(f"## bot{bot} ({cinfo['label']})   GATE: {pg} → {_gate_word(cinfo)}")
        if cinfo["gate"]["violations"]:
            out.append("위반: " + "; ".join(cinfo["gate"]["violations"]))
        cpq, ppq = cinfo["per_qid"], (pinfo or {}).get("per_qid", {})
        for qid in sorted(cpq):
            c = cpq[qid]
            p = ppq.get(qid)
            cdesc = f"{c['agg']}({c['stability']})"
            pdesc = f"{p['agg']}({p['stability']})" if p else "—"
            mark = "=" if (p and p["agg"] == c["agg"] and p["stability"] == c["stability"]) else "변화"
            out.append(f"{qid:6} {pdesc:22} → {cdesc:22} {mark}")
        out.append(
            f"flags {cinfo['flags_total']} · expect {cinfo['expect']} · "
            f"unstable {len(cinfo['unstable'])} · mixed {len(cinfo['mixed'])}"
        )
        out.append("")
    out.append(f"종합 PASS: {curr['overall_pass']}")
    return "\n".join(out)


# ---------------------------------------------------------------- 질문셋/런 관리

def _load_qset(name):
    p = Path(name)
    if not p.exists():
        p = QSET_DIR / (name if name.endswith(".json") else f"{name}.json")
    qset = json.loads(p.read_text(encoding="utf-8"))
    g = qset["grader"]
    for k in ("instruction_ab", "instruction_single", "flag_fields", "gates"):
        assert k in g, f"질문셋 grader 에 '{k}' 누락"
    return qset


def _find_prev(qs_name, curr_dir):
    base = ARTIFACT_ROOT / qs_name
    dirs = sorted(
        d for d in base.glob("*")
        if d.is_dir() and d != curr_dir and (d / "summary.json").exists()
    )
    if not dirs:
        return None, None
    prev = dirs[-1]
    return prev, json.loads((prev / "summary.json").read_text(encoding="utf-8"))


def _graded_to_json(graded):
    return {str(b): {str(s): elems for s, elems in sm.items()} for b, sm in graded.items()}


# ---------------------------------------------------------------- 서브커맨드

def cmd_run(args):
    qset = _load_qset(args.questions)
    bots = [int(b) for b in args.bots.split(",")]
    rule_text = Path(args.rule_file).read_text(encoding="utf-8") if args.rule_file else None
    mode = "ab" if rule_text is not None else "single"
    ts = datetime.now().strftime("%Y-%m-%dT%H%M")
    run_dir = ARTIFACT_ROOT / qset["name"] / f"{ts}_{args.label or 'run'}"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "raw.json"

    meta = {
        "questionset": qset["name"], "mode": mode, "label": args.label or "run", "ts": ts,
        "model": MODEL, "temperature": 0.2, "samples": args.samples, "bots": bots,
        "rule_chars": len(rule_text) if rule_text else 0,
        "grader": f"codex {CODEX_REASONING}",
    }
    results = asyncio.run(_probe(qset, bots, args.samples, rule_text, raw_path, meta))
    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    meta["errors"] = errs
    raw = {"meta": meta, "rule": (rule_text.strip() if rule_text else None), "results": results}
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"프로브 완료 — {len(results)}건 (ERROR {errs}), {raw_path}")

    graded, mode = _grade(raw, qset)
    (run_dir / "graded.json").write_text(
        json.dumps(_graded_to_json(graded), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    summary = _aggregate(graded, qset, mode)
    summary["meta"] = meta
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    prev_dir, prev = _find_prev(qset["name"], run_dir)
    cmp_md = _compare_md(summary, prev, qset["name"], run_dir.name, prev_dir.name if prev_dir else None)
    (run_dir / "compare.md").write_text(cmp_md, encoding="utf-8")
    print("\n" + cmp_md)
    print(f"\n저장: {run_dir}")


def cmd_grade(args):
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    qset = _load_qset(args.questions)
    graded, mode = _grade(raw, qset)
    summary = _aggregate(graded, qset, mode)
    for bot, info in sorted(summary["bots"].items()):
        print(f"\nbot{bot} ({info['label']}) — GATE {_gate_word(info)}  {info['agg_verdicts']}")
        print(f"  expect {info['expect']} · flags {info['flags_total']} · "
              f"unstable {list(info['unstable'])} · mixed {list(info['mixed'])}")
        if info["gate"]["violations"]:
            print("  위반:", "; ".join(info["gate"]["violations"]))
    print(f"\n종합 PASS: {summary['overall_pass']}")


def cmd_compare(args):
    a = json.loads((Path(args.a) / "summary.json").read_text(encoding="utf-8"))
    b = json.loads((Path(args.b) / "summary.json").read_text(encoding="utf-8"))
    print(_compare_md(b, a, a.get("meta", {}).get("questionset", "?"), Path(args.b).name, Path(args.a).name))


def cmd_list(args):
    pattern = f"{args.questions}/*" if args.questions else "*/*"
    rows = []
    for qdir in sorted(ARTIFACT_ROOT.glob(pattern)):
        sp = qdir / "summary.json"
        if not sp.exists():
            continue
        s = json.loads(sp.read_text(encoding="utf-8"))
        rows.append((f"{qdir.parent.name}/{qdir.name}", s.get("overall_pass"), s.get("meta", {})))
    if not rows:
        print("런 기록 없음")
        return
    for name, ok, meta in rows:
        print(f"{'PASS' if ok else 'FAIL':4} {name}  (samples={meta.get('samples')} mode={meta.get('mode')} errors={meta.get('errors')})")


def main():
    ap = argparse.ArgumentParser(description="프롬프트 변경 검증 하네스")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="프로브→채점→집계→베이스라인 비교 일괄")
    r.add_argument("--questions", required=True, help="질문셋 이름 또는 경로 (crisis/recency)")
    r.add_argument("--bots", default="5,3", help="봇 id 콤마구분 (기본 5,3)")
    r.add_argument("--samples", type=int, default=3, help="문항당 샘플 수 (기본 3)")
    r.add_argument("--rule-file", help="A/B 모드: 규칙 텍스트 파일 (없으면 단순 평가 모드)")
    r.add_argument("--label", help="런 라벨")
    r.set_defaults(func=cmd_run)

    g = sub.add_parser("grade", help="기존 raw.json 재채점 (Gemini 호출 없음, 레거시 raw 호환)")
    g.add_argument("--raw", required=True)
    g.add_argument("--questions", required=True)
    g.set_defaults(func=cmd_grade)

    c = sub.add_parser("compare", help="두 런 디렉토리 비교")
    c.add_argument("--a", required=True, help="기준(이전) 런 디렉토리")
    c.add_argument("--b", required=True, help="대상(이후) 런 디렉토리")
    c.set_defaults(func=cmd_compare)

    ls = sub.add_parser("list", help="누적 런 목록")
    ls.add_argument("--questions", help="질문셋 필터")
    ls.set_defaults(func=cmd_list)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
