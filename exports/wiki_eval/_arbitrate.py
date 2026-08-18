# 팔 G′ — 중재. 팔 A 와 팔 C 의 답을 세 번째 호출로 정리해 하나로 만든다. Gemini 호출 0.
#
# **왜 이 팔이 있나.** 두 답을 그냥 이어 붙였더니(사후결합) 유해가 3건 → 5건으로 늘었다.
# 망가진 지점이 전부 충돌이었다.
#
#   #16  A "만20세, 부모동의 시 만18세"(만점) + C "만16세 영인축복식 기준"(무관)  → 합치니 -2
#   #44  A 등록 절차 정확히 안내(만점)       + C "규정에 관련 내용이 없습니다"     → 합치니 -2
#   #13  각각은 유해 아님                    + 붙이니 연령 안내가 상충            → -2
#
# 이어 붙이기는 셋 다 통과시킨다. 중재는 걸러야 한다. 그게 되는지만 본다.
#
# **이 팔은 공정 비교가 아니다.** 두 가지가 다르다.
#   ① 호출을 3회 쓴다 (A·C 병렬 + 중재). 다른 팔은 1회다.
#   ② 중재자가 codex 다. 하루 생성 상한이 소진돼 같은 모델을 못 썼다.
#      **더 센 모델이 정리하는 것이라 결과를 과대평가한다.**
# 그래서 이 팔이 답하는 것은 "프로덕션에서 몇 점인가"가 아니라
# **"두 답에 흩어진 정보가 회수 가능한가"** 하나다. 음성이면 믿을 만하고, 양성이면 재측정해야 한다.
#
# 사용: uv run python ../exports/wiki_eval/_arbitrate.py
import json
import re
import subprocess
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
ANSWERS = DIR / "answers.json"
KEY = "arb_ac"
SRC = ("rag", "wiki_first")

# 충돌 해소 규칙이 이 팔의 전부다. 규칙 5·6 이 위 세 실패를 각각 겨냥한다.
PROMPT = """너는 종교단체 행정 규정 챗봇의 초안 답변 두 개를 하나로 정리한다.

**자료는 아래 초안 두 개뿐이다.** 네 배경지식·인터넷 지식을 쓰지 마라. 검색하지 마라.
링크·전화번호·기관명도 초안에 있는 것만 쓴다. 이 규칙을 어기면 측정이 무의미해진다.

규칙
1. 두 초안에 없는 사실을 새로 만들지 마라. 정리만 한다. 없는 절차·숫자를 지어내면 실패다.
2. 질문과 무관한 내용은 버려라. 초안에 있다는 이유만으로 싣지 마라.
3. 두 초안이 같은 말을 하면 한 번만 쓴다.
4. 한쪽에만 있고 다른 쪽과 어긋나지 않으면 싣는다.
5. 두 초안이 서로 어긋나면:
   - 한쪽이 조문·공문 같은 구체적 근거를 대고 다른 쪽은 "확인되지 않는다"고만 하면,
     근거를 댄 쪽을 택한다. 근거 없는 침묵은 검색 실패일 수 있다.
   - 둘 다 구체적인데 숫자·자격·절차가 서로 다르면, 어느 쪽도 단정하지 말고
     확인이 필요하다고 쓴 뒤 담당 부서 안내로 넘긴다.
6. 완성한 답변을 다시 읽고 **앞뒤가 어긋나는 문장을 지워라.** 한 답변 안에서
   "이렇습니다"와 "확인되지 않습니다"가 같이 있으면 안 된다.

출력은 최종 답변 본문만. 머리말·설명·표시 없이 답변만 쓴다."""


def squash(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s or "").casefold().split())


def score_keywords(answer: str, keywords: list[str]) -> dict:
    body = squash(answer)
    exact, partials, detail = [], [], []
    for kw in keywords:
        if not squash(kw):
            continue
        tokens = [t for t in re.split(r"[\s,/·()]+", kw) if len(squash(t)) >= 2]
        found = [t for t in tokens if squash(t) in body]
        frac = len(found) / len(tokens) if tokens else 0.0
        partials.append(frac)
        if squash(kw) in body:
            exact.append(kw)
        detail.append({"kw": kw, "frac": round(frac, 2), "found": found})
    return {
        "kw_pct": round(100 * sum(partials) / len(partials)) if partials else None,
        "kw_exact": len(exact),
        "kw_total": len(keywords),
        "kw_detail": detail,
    }


def usable(row: dict, arm: str) -> bool:
    return arm in row and not row[arm].get("error") and bool(row[arm].get("answer"))


def arbitrate(row: dict) -> str | None:
    a, c = row[SRC[0]]["answer"].strip(), row[SRC[1]]["answer"].strip()
    body = f"{PROMPT}\n\n# 질문\n{row['question']}\n\n# 초안 1\n{a}\n\n# 초안 2\n{c}"
    proc = subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", body],
        capture_output=True, text=True, timeout=600,
    )
    # `codex exec` 는 stdout 에 최종 메시지만 낸다. 문단으로 자르면 답이 잘린다 — 한 번 잘랐다.
    return proc.stdout.strip() or None


_URL = re.compile(r"https?://\S+")


def leaked(merged: str, row: dict) -> list[str]:
    """중재자가 초안 밖 내용을 끌어왔는지 본다.

    codex 는 자기 지식으로 답할 수 있다 — 실제로 예비 테스트에서 초안에 없는 URL 을 넣었다.
    중재자가 정보를 보태면 "두 답에 흩어진 정보가 회수되는가"가 아니라
    "더 센 모델이 아는가"를 재게 된다. 새 URL 과 새 전화번호만이라도 잡아 둔다.
    """
    src = row[SRC[0]]["answer"] + row[SRC[1]]["answer"]
    out = []
    out += [u for u in _URL.findall(merged) if u not in src]
    out += [t for t in re.findall(r"\d{2,4}-\d{3,4}-\d{4}", merged) if t not in src]
    return out


def main() -> None:
    rows = json.loads(ANSWERS.read_text(encoding="utf-8"))
    targets = [r for r in rows if all(usable(r, s) for s in SRC)]
    print(f"중재 대상 {len(targets)}/{len(rows)}문항 "
          f"(정답 있는 문항 {sum(1 for r in targets if r.get('golden'))}건)\n")

    for i, row in enumerate(targets, 1):
        merged = arbitrate(row)
        if not merged:
            print(f"[{i:2d}/{len(targets)}] #{row['n']:<3} 실패")
            continue
        cell = {
            "answer": merged,
            "citations": (row[SRC[0]].get("citations") or []) + (row[SRC[1]].get("citations") or []),
            # A·C 는 병렬로 부를 수 있다. 거기에 중재 1회가 더 붙는다.
            "elapsed_s": round(max(row[SRC[0]]["elapsed_s"], row[SRC[1]]["elapsed_s"]), 2),
            "error": None,
            "arbiter": "codex",
        }
        cell.update(score_keywords(merged, row["keywords"]))
        bad = leaked(merged, row)
        if bad:
            cell["leaked"] = bad
        row[KEY] = cell
        ANSWERS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

        base = row[SRC[0]]["kw_pct"]
        print(f"[{i:2d}/{len(targets)}] #{row['n']:<3} A {base:3d}% → G′ {cell['kw_pct']:3d}% "
              f"({cell['kw_pct'] - base:+d}pp) {len(merged):4d}자  {row['question'][:30]}"
              + (f"  ⚠유출 {bad}" if bad else ""))

    done = [r for r in rows if KEY in r]
    if done:
        a = sum(r[SRC[0]]["kw_pct"] for r in done) / len(done)
        g = sum(r[KEY]["kw_pct"] for r in done) / len(done)
        n_leak = sum(1 for r in done if r[KEY].get("leaked"))
        print(f"\n{len(done)}문항 · 팔 A {a:.1f}% → 팔 G′ {g:.1f}% ({g - a:+.1f}pp)")
        if n_leak:
            print(f"  ⚠ 초안 밖 내용이 섞인 문항 {n_leak}건 — 중재자 오염. 해당 문항은 결과에서 뺄 것")
    print(f"→ {ANSWERS} ({len(rows)}행)")


if __name__ == "__main__":
    main()
