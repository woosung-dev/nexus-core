# `_gate_probe.json` 을 읽어 **사람이 판정해야 하는 것만** 꺼낸다.
#
# 수치는 `_gate_probe.py` 가 이미 낸다. 여기서 하는 일은 하나다 —
# **마커가 없는 답변의 전문을 보여 준다.** go/no-go 는 이 글을 읽어야 정해진다.
#
#   정당한 차단   사실 주장이 없다 (인사·연결처 안내·거절) → 막아도 손해 0
#   과잉 거절     사실을 말하면서 마커만 빠졌다 → 게이트가 멀쩡한 답을 죽인다
#
# 사용: python3 exports/wiki_eval/_gate_read.py [--arm forced] [--all]
import argparse
import json
from pathlib import Path

DIR = Path(__file__).parent


def main(arm: str, show_all: bool) -> None:
    rows = json.loads((DIR / "_gate_probe.json").read_text(encoding="utf-8"))

    hits = []
    for r in rows:
        for run, c in enumerate(r.get(arm, [])):
            if c.get("error"):
                continue
            if show_all or (not c["empty"] and not c["ids_all"]):
                hits.append((r, run, c))

    ooc = sum(1 for r, _, _ in hits if str(r["category"]).startswith("코퍼스밖"))
    print(f"{arm} 팔 · 마커 없는 답변 {len(hits)}건 (코퍼스 밖 {ooc}건 포함)\n")

    for r, run, c in hits:
        print("=" * 78)
        print(f"#{r['n']}  [{r.get('risk') or '-'}] {r['category']}  {run + 1}회차")
        print(f"질문: {r['question']}")
        print(f"검색 1단: {c['stage1']}   주입 id {len(c['inprompt'])}건")
        print("-" * 78)
        print(c["answer"] or "(빈 답변)")
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="forced", choices=["forced", "current"])
    ap.add_argument("--all", action="store_true", help="마커 있는 것까지 전부")
    a = ap.parse_args()
    main(a.arm, a.all)
