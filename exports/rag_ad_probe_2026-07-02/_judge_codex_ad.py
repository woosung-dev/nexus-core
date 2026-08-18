# D 귀속의 문장↔청크 정렬 표본을 codex CLI(구독·무과금)로 심판해 임계값을 보정 → _judge_d.json
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DIR = Path(__file__).parent
CAPS = json.loads((DIR / "captures.json").read_text())
ATTR = json.loads((DIR / "attribution.json").read_text())
OUT = DIR / "_judge_d.json"
REASONING = "medium"
PER_BIN = 8  # 점수 구간별 표본 수

INSTRUCTION = (
    "너는 RAG 인용 정합성 평가자다. <stdin>으로 JSON 배열이 들어온다. "
    "각 항목은 챗봇 답변의 한 문장(sentence)과 그 문장의 출처로 제안된 문서 청크(chunk)다.\n"
    "설명 없이 오직 JSON 배열 하나만, 입력과 같은 개수·순서·pid로 출력하라.\n"
    "각 원소 필드: pid, support(full|partial|none: chunk가 sentence의 사실 주장을 뒷받침하는 정도. "
    "sentence가 공감·인사 등 사실 주장이 없으면 none), reason(한 줄 한국어)."
)


def extract_json_array(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError("JSON 배열 못 찾음")
    return json.loads(t[i:j + 1])


def main():
    # 점수 구간별 표본 추출
    bins = {"0.70-0.75": [], "0.75-0.80": [], "0.80-0.85": [], "0.85+": []}
    for qid, r in ATTR.items():
        chunks = (CAPS[qid].get("PF") or {}).get("chunks") or []
        # dedupe 순서가 attribution 과 동일해야 함 — _attribute_d.py 와 같은 로직 재적용
        seen, dchunks = set(), []
        for ch in chunks:
            k = (ch.get("title") or "") + "|" + (ch.get("text") or "")[:200]
            if k in seen or not ch.get("text"):
                continue
            seen.add(k)
            dchunks.append(ch)
        for row in r["sentences"]:
            sc = row["score"]
            key = "0.85+" if sc >= 0.85 else "0.80-0.85" if sc >= 0.80 else "0.75-0.80" if sc >= 0.75 else "0.70-0.75" if sc >= 0.70 else None
            if key is None or row["best_chunk"] >= len(dchunks):
                continue
            bins[key].append({
                "qid": qid, "score": sc, "sentence": row["sentence"],
                "chunk_title": row["best_title"],
                "chunk_text": dchunks[row["best_chunk"]]["text"][:900],
            })

    items = []
    for key, rows in bins.items():
        rows.sort(key=lambda r: r["score"])
        step = max(1, len(rows) // PER_BIN)
        for r in rows[::step][:PER_BIN]:
            items.append(r)
    for i, it in enumerate(items):
        it["pid"] = i
    print(f"표본 {len(items)}쌍 (구간별 {[f'{k}:{len(v)}' for k, v in bins.items()]})")

    payload = json.dumps(
        [{"pid": it["pid"], "sentence": it["sentence"],
          "chunk": {"title": it["chunk_title"], "text": it["chunk_text"]}} for it in items],
        ensure_ascii=False)
    p = subprocess.run(
        ["codex", "exec", INSTRUCTION, "-s", "read-only",
         "-c", f'model_reasoning_effort="{REASONING}"'],
        input=payload, capture_output=True, text=True, cwd=str(ROOT), timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"codex exit {p.returncode}: {p.stderr[-300:]}")
    res = extract_json_array(p.stdout)
    jmap = {int(g["pid"]): g for g in res}

    judged = []
    for it in items:
        g = jmap.get(it["pid"], {"support": "none", "reason": "[codex 누락]"})
        judged.append({**it, "support": g.get("support"), "judge_reason": g.get("reason")})

    # 구간별 정밀도 요약
    prec = {}
    for key in bins:
        rows = [j for j in judged if (
            key == "0.85+" and j["score"] >= 0.85) or (
            key == "0.80-0.85" and 0.80 <= j["score"] < 0.85) or (
            key == "0.75-0.80" and 0.75 <= j["score"] < 0.80) or (
            key == "0.70-0.75" and 0.70 <= j["score"] < 0.75)]
        if rows:
            ok = sum(1 for r in rows if r["support"] in ("full", "partial"))
            prec[key] = {"n": len(rows), "support_rate": round(ok / len(rows), 2)}
    OUT.write_text(json.dumps({"precision_by_bin": prec, "judged": judged},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(prec, ensure_ascii=False, indent=2))
    print(f"→ {OUT.name}")


main()
