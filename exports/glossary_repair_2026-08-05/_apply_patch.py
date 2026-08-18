# _glossary_terms.json + _patch.json → _glossary_terms_v2.json
#
# 원본 ETL 산출물은 건드리지 않는다. ETL 은 PDF 를 정확히 옮겼고(ERRATA.md), 틀린 것은 PDF 다.
# 그래서 v1 을 증거로 보존하고 수리는 별도 레이어에 둔다.
#
# 안전장치:
#   · 패치의 `old` 가 현재 값과 다르면 중단한다 (엉뚱한 판을 고치는 것을 막는다)
#   · 패치에 적힌 필드 말고는 못 바꾼다 — 적용 후 v1↔v2 를 전 필드 비교해 증명한다
#   · `--check` 로 쓰기 없이 diff 만 볼 수 있다
import argparse
import copy
import json
from pathlib import Path

DIR = Path(__file__).parent
SRC = DIR.parent / "branch_ablation_2026-08-04" / "_glossary_terms.json"
PATCH = DIR / "_patch.json"
OUT = DIR / "_glossary_terms_v2.json"

FIELDS = ("no", "term", "aliases", "definition", "category",
          "source_articles", "admin_note", "review_status")


def diff_all(v1, v2):
    """전 항목 · 전 필드 비교. (no, field, old, new) 목록."""
    a = {t["no"]: t for t in v1}
    b = {t["no"]: t for t in v2}
    out = []
    for no in sorted(set(a) | set(b)):
        if no not in a:
            out.append((no, "*추가*", None, b[no]["term"]))
            continue
        if no not in b:
            out.append((no, "*삭제*", a[no]["term"], None))
            continue
        for f in FIELDS:
            if a[no].get(f) != b[no].get(f):
                out.append((no, f, a[no].get(f), b[no].get(f)))
    return out


def main(check_only):
    src = json.loads(SRC.read_text(encoding="utf-8"))
    patch = json.loads(PATCH.read_text(encoding="utf-8"))
    v1 = src["terms"]
    v2 = copy.deepcopy(v1)
    by_no = {t["no"]: t for t in v2}

    for e in patch["edits"]:
        t = by_no.get(e["no"])
        if t is None:
            raise SystemExit(f"⚠ no={e['no']} 없음")
        if t["term"] != e["term"]:
            raise SystemExit(f"⚠ no={e['no']} 용어 불일치: {t['term']!r} != {e['term']!r}")
        if t[e["field"]] != e["old"]:
            raise SystemExit(
                f"⚠ no={e['no']} {e['field']} 현재값이 패치의 old 와 다르다\n"
                f"   현재 {t[e['field']]!r}\n   패치 {e['old']!r}\n"
                f"   이미 적용됐거나 다른 판이다. 덮어쓰지 않고 중단한다.")
        t[e["field"]] = e["new"]

    for a in patch["adds"]:
        if a["no"] in by_no:
            raise SystemExit(f"⚠ no={a['no']} 이미 있다")
        v2.append({f: a.get(f) for f in FIELDS})
    v2.sort(key=lambda t: t["no"])

    changes = diff_all(v1, v2)
    expect = {(e["no"], e["field"]) for e in patch["edits"]} | \
             {(a["no"], "*추가*") for a in patch["adds"]}
    got = {(no, f) for no, f, _, _ in changes}

    print(f"v1 {len(v1)}개 → v2 {len(v2)}개")
    print(f"패치 지시: 수정 {len(patch['edits'])}건 · 추가 {len(patch['adds'])}건\n")
    print(f"실제 변경 {len(changes)}건")
    for no, f, old, new in changes:
        print(f"  no={no:>3} {f:<16} {old!r} → {new!r}")

    unexpected = got - expect
    missing = expect - got
    if unexpected:
        raise SystemExit(f"\n⚠ 패치에 없는 변경 {sorted(unexpected)} — 쓰지 않고 중단한다.")
    if missing:
        raise SystemExit(f"\n⚠ 패치가 지시했는데 안 바뀐 것 {sorted(missing)} — 중단한다.")
    print("\n패치 지시와 실제 변경이 정확히 일치. 그 외 필드 변경 0건.")

    if check_only:
        print("(--check 이므로 쓰지 않음)")
        return

    OUT.write_text(json.dumps({
        **{k: v for k, v in src.items() if k != "terms"},
        "count": len(v2),
        "patched_from": SRC.name,
        "patch": PATCH.name,
        "terms": v2,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="쓰지 않고 diff 만")
    main(ap.parse_args().check)
