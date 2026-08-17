# 블레싱 나 응답을 per-user 데이터셋에 병합 → 평가용 dataset_{user}.json 갱신
import json
from pathlib import Path

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
USERS = ["조화연", "신은비", "김소영"]

ans = {r["qid"]: r for r in json.load(open(DIR / "blessing_answers.json"))["results"]}
for u in USERS:
    p = DIR / f"dataset_{u}.json"
    ds = json.load(open(p))
    miss = 0
    for it in ds["items"]:
        a = ans.get(it["qid"])
        if a:
            it["blessing_answer"] = a["answer"]
            it["blessing_citations"] = a["citations"]
        else:
            miss += 1
    json.dump(ds, open(p, "w"), ensure_ascii=False, indent=1)
    errs = sum(1 for it in ds["items"] if (it["blessing_answer"] or "").startswith("[ERROR]"))
    print(f"{u}: 병합 {len(ds['items'])-miss}/{len(ds['items'])} (미존재 {miss}, ERROR응답 {errs})")
print("병합 완료")
