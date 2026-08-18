import json
from pathlib import Path
DIR=Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
RECS=json.load(open("/Users/woosung/project/agy-project/nexus-core/exports/_redteam_v2_data.json"))["records"]
USERS=["조화연","신은비","김소영"]
AGENT={"조화연":"redteam-johwayeon","신은비":"redteam-shineunbi","김소영":"redteam-kimsoyoung"}
ans={r["qid"]:r for r in json.load(open(DIR/"answers_나_v3.json"))["results"]}
for u in USERS:
    rs=[r for r in RECS if r["user"]==u]; items=[]
    for i,r in enumerate(rs,1):
        qid=f"{u}-{i:02d}"; a=ans.get(qid)
        items.append({"qid":qid,"user":u,"qtype":r["qtype"],"q":(r["q"] or "").strip(),
            "ansA_통합":r["ansA"],"ansB_원리":r["ansB"],"ansC_정밀":r["ansC"],
            "tester_choice":r["choice"],"tester_win":r["win"],"tester_feedback":r["feedback"],
            "blessing_answer":a["answer"] if a else None,"blessing_citations":a["citations"] if a else None})
    json.dump({"user":u,"agent":AGENT[u],"count":len(items),"items":items},
              open(DIR/f"dataset_나_{u}_v3.json","w"),ensure_ascii=False,indent=1)
    print(f"  나 {u}: {len(items)} (ERROR {sum(1 for it in items if (it['blessing_answer'] or '').startswith('[ERROR]'))})")
print("나 v3 병합 완료")
