# fresh 심판용 데이터 팩 — 사용자별 질문 + A/B/C + 봇별 전 버전 답변을 한 JSON으로
import json
from pathlib import Path

NA = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
V3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
GA = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_ga_2026-06-12")
OUT = V3 / "judge_packs"
OUT.mkdir(exist_ok=True)

# bot -> (versions: name->dataset path pattern)
NA_USERS = ["조화연", "신은비", "김소영"]
GA_USERS = ["미야자키시호", "김소영", "조화연"]


def load_items(p):
    return {it["qid"]: it for it in json.load(open(p))["items"]}


def build_bot_pack(user, bot):
    if bot == "나":
        vers = {
            "나v1": NA / f"dataset_{user}.json",
            "나v2": NA / f"dataset_{user}_v2.json",
            "나v3": V3 / f"dataset_나_{user}_v3.json",
            "나v5": V3 / f"dataset_나_{user}_v5.json",
        }
    else:
        vers = {
            "가원본": GA / f"dataset_{user}.json",
            "가v3": V3 / f"dataset_가_{user}_v3.json",
            "가v5": V3 / f"dataset_가_{user}_v5.json",
        }
    loaded = {v: load_items(p) for v, p in vers.items() if p.exists()}
    base_ver = list(loaded)[0]
    items = []
    for qid, base in loaded[base_ver].items():
        row = {
            "qid": qid, "qtype": base.get("qtype"), "q": base.get("q"),
            "A_통합": base.get("ansA_통합"), "B_원리": base.get("ansB_원리"), "C_정밀": base.get("ansC_정밀"),
            "tester_choice": base.get("tester_win") or base.get("tester_choice"),
        }
        for v, m in loaded.items():
            it = m.get(qid, {})
            ans = it.get("blessing_answer")
            row[v] = ans if (ans and not str(ans).startswith("[ERROR]")) else None
        items.append(row)
    return {"user": user, "bot": bot, "versions": list(loaded), "count": len(items), "items": items}


JOBS = [("조화연", ["나", "가"]), ("신은비", ["나"]), ("김소영", ["나", "가"]), ("미야자키시호", ["가"])]
for user, bots in JOBS:
    for bot in bots:
        pack = build_bot_pack(user, bot)
        f = OUT / f"pack_{bot}_{user}.json"
        f.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        # 결손(버전별 None 수) 리포트
        miss = {v: sum(1 for it in pack["items"] if it.get(v) is None) for v in pack["versions"]}
        print(f"{f.name}: {pack['count']}문항 · 버전 {pack['versions']} · 결손 {miss} · {f.stat().st_size//1024}KB")
