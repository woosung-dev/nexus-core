# A/B 블라인드 codex 심판: OLD vs NEW 답변 품질(승/무/패) + NEW 인용 무결성. 무과금 codex CLI.
import os
import sys
import json
import re
import random
import subprocess
from collections import defaultdict

SC = "/private/tmp/claude-501/-Users-woosung-project-agy-project-nexus-core/cf88eb6c-aabb-40e6-84d0-e477d46c9272/scratchpad"
REPO = "/Users/woosung/project/agy-project/nexus-core"
_SUF = sys.argv[1] if len(sys.argv) > 1 else ""
IN = f"{SC}/_ab{_SUF}_captures.json"
OUT = f"{SC}/_ab{_SUF}_judge.json"
REASONING = "medium"
random.seed(42)

AB_INSTRUCTION = (
    "너는 가정연합 축복 상담 챗봇 답변을 평가하는 엄격·공정한 심판이다. <stdin> JSON 배열의 각 항목은 "
    "한 질문에 대한 두 답변(answer_A, answer_B)이다(어느 쪽이 어떤 시스템인지 모른다=블라인드). "
    "골든(golden=모범답안 요지)·anchors(문서전용 사실)를 기준으로 비교하라.\n"
    "설명·서론·코드 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·qid 로 출력한다.\n"
    "각 원소 필드: qid, winner(A|B|tie: 전반 답변품질 우위), "
    "A:{accuracy(정확|부분오류|오류), safe(bool: 위험·범위밖 안전처리, 해당없으면 true), "
    "markup_leak(bool: '<followups>'·'§'·'하나님' 등 내부표기 노출), routing_ok(bool: 담당자/상담 연결 등 적절), "
    "persona_tone_ok(bool: 따뜻한 상담가 어조 유지)}, B:{동일 필드}, reason(한 줄 한국어).\n"
    "상담형 문항은 단정 대신 공감·확인·담당자 연결이면 accuracy=정확. 코퍼스外(golden 비어있음) 질문은 "
    "'문서에 없음/담당자 확인'이면 정확. 사실형은 anchors/golden 충족도로 판단한다."
)

CITE_INSTRUCTION = (
    "너는 RAG 인용 무결성을 검증한다. <stdin> JSON 배열의 각 항목은 답변(answer)과 그 답변이 제시한 "
    "인용 출처(citations:[{title,content}])다. 오직 JSON 배열 하나만, 같은 개수·순서·qid 로 출력.\n"
    "각 원소: qid, citation_support(full|partial|none: 인용 출처가 답변 핵심 주장을 실제로 뒷받침하는 정도), "
    "hallucinated(bool: 인용·일반상식 어디에도 없는 사실 단정), reason(한 줄)."
)


def extract_json_array(text):
    t = re.sub(r"```$", "", re.sub(r"^```(?:json)?", "", text.strip()).strip()).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError("JSON 배열 못 찾음")
    return json.loads(t[i:j + 1])


def codex(instruction, items, timeout=600):
    p = subprocess.run(["codex", "exec", instruction, "-s", "read-only",
                        "-c", f'model_reasoning_effort="{REASONING}"'],
                       input=json.dumps(items, ensure_ascii=False), capture_output=True,
                       text=True, cwd=REPO, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-200:]}")
    return extract_json_array(p.stdout)


def main():
    caps = json.load(open(IN, encoding="utf-8"))
    by_bot = defaultdict(list)
    for c in caps:
        by_bot[c["bot_id"]].append(c)

    ab_results = []      # {qid, bot_id, winner_system(OLD|NEW|tie), A_is, judge}
    cite_results = []
    for bid, rows in by_bot.items():
        # --- 블라인드 A/B ---
        items, mapping = [], {}
        for r in rows:
            old_is_a = random.random() < 0.5
            mapping[r["qid"]] = "OLD" if old_is_a else "NEW"  # A 가 무엇인지
            a, b = (r["OLD"], r["NEW"]) if old_is_a else (r["NEW"], r["OLD"])
            items.append({"qid": r["qid"], "question": r["question"],
                          "golden": (r.get("golden") or "")[:1200], "anchors": r.get("anchors", []),
                          "answer_A": (a["answer"] or "")[:2200], "answer_B": (b["answer"] or "")[:2200]})
        print(f"  codex A/B 심판: 봇 {bid} ({len(items)}문항)...", flush=True)
        res = {str(g.get("qid")): g for g in codex(AB_INSTRUCTION, items)}
        for r in rows:
            g = res.get(str(r["qid"])) or {}
            a_is = mapping[r["qid"]]
            w = g.get("winner")
            winner_system = "tie" if w == "tie" else (a_is if w == "A" else ("NEW" if a_is == "OLD" else "OLD"))
            ab_results.append({"qid": r["qid"], "bot_id": bid, "A_is": a_is,
                               "winner_system": winner_system, "judge": g})

        # --- NEW 인용 무결성(인용 있는 행만) ---
        cite_items = [{"qid": r["qid"], "answer": (r["NEW"]["answer"] or "")[:2200],
                       "citations": [{"title": c.get("title"), "content": (c.get("content") or "")[:500]}
                                     for c in r["NEW"].get("citations_full", [])]}
                      for r in rows if r["NEW"].get("citations_full")]
        if cite_items:
            print(f"  codex 인용무결성: 봇 {bid} ({len(cite_items)}건)...", flush=True)
            cres = {str(g.get("qid")): g for g in codex(CITE_INSTRUCTION, cite_items)}
            for it in cite_items:
                g = cres.get(str(it["qid"])) or {}
                cite_results.append({"qid": it["qid"], "bot_id": bid, "judge": g})

    json.dump({"ab": ab_results, "cite": cite_results}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n심판 저장 → {OUT} (A/B {len(ab_results)}, cite {len(cite_results)})")


if __name__ == "__main__":
    main()
