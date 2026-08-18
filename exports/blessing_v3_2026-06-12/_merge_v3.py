# v3 응답을 per-bot per-user 데이터셋으로 (dataset_{bot}_{user}_v3.json) — A/B/C/tester + blessing v3
import json
from pathlib import Path
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
RECS = json.load(open("/Users/woosung/project/agy-project/nexus-core/exports/_redteam_v2_data.json"))["records"]
JOBS = [("나", ["조화연","신은비","김소영"], DIR/"answers_나_v3.json"),
        ("가", ["미야자키시호","김소영","조화연"], DIR/"answers_가_v3.json")]
AGENT = {"조화연":"redteam-johwayeon","신은비":"redteam-shineunbi","김소영":"redteam-kimsoyoung","미야자키시호":"redteam-miyazakishiho"}
for bot, users, ansf in JOBS:
    ans = {r["qid"]: r for r in json.load(open(ansf))["results"]}
    for u in users:
        rs = [r for r in RECS if r["user"]==u]
        items=[]
        for i,r in enumerate(rs,1):
            qid=f"{u}-{i:02d}"; a=ans.get(qid)
            items.append({"qid":qid,"user":u,"qtype":r["qtype"],"q":(r["q"] or "").strip(),
                "ansA_통합":r["ansA"],"ansB_원리":r["ansB"],"ansC_정밀":r["ansC"],
                "tester_choice":r["choice"],"tester_win":r["win"],"tester_feedback":r["feedback"],
                "blessing_answer":a["answer"] if a else None,
                "blessing_citations":a["citations"] if a else None})
        json.dump({"user":u,"agent":AGENT[u],"count":len(items),"items":items},
                  open(DIR/f"dataset_{bot}_{u}_v3.json","w"), ensure_ascii=False, indent=1)
        errs=sum(1 for it in items if (it["blessing_answer"] or "").startswith("[ERROR]"))
        print(f"  {bot} {u}: dataset_{bot}_{u}_v3.json ({len(items)}, ERROR {errs})")
print("v3 병합 완료")
