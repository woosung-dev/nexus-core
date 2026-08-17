import json
from pathlib import Path
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_ga_2026-06-12")
USERS = ["미야자키시호", "김소영", "조화연"]
ans = {r["qid"]: r for r in json.load(open(DIR / "blessing_ga_answers.json"))["results"]}
for u in USERS:
    ds = json.load(open(DIR / f"dataset_{u}.json"))
    for it in ds["items"]:
        a = ans.get(it["qid"])
        it["blessing_answer"] = a["answer"] if a else None
        it["blessing_citations"] = a["citations"] if a else None
    json.dump(ds, open(DIR / f"dataset_{u}.json", "w"), ensure_ascii=False, indent=1)
    errs = sum(1 for it in ds["items"] if (it["blessing_answer"] or "").startswith("[ERROR]"))
    print(f"{u}: 병합 {len(ds['items'])} (ERROR {errs})")
print("병합 완료")
