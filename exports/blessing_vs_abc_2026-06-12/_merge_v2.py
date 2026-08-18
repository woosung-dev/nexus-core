# 블레싱 나 v2 응답을 per-user 데이터셋으로 (dataset_{user}_v2.json)
import json
from pathlib import Path
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
USERS = ["조화연", "신은비", "김소영"]
ans = {r["qid"]: r for r in json.load(open(DIR / "blessing_answers_v2.json"))["results"]}
for u in USERS:
    ds = json.load(open(DIR / f"dataset_{u}.json"))
    for it in ds["items"]:
        a = ans.get(it["qid"])
        it["blessing_answer"] = a["answer"] if a else None
        it["blessing_citations"] = a["citations"] if a else None
    ds["version"] = "v2"
    json.dump(ds, open(DIR / f"dataset_{u}_v2.json", "w"), ensure_ascii=False, indent=1)
    errs = sum(1 for it in ds["items"] if (it["blessing_answer"] or "").startswith("[ERROR]"))
    print(f"{u}: dataset_{u}_v2.json ({len(ds['items'])}문항, ERROR {errs})")
print("v2 병합 완료")
