# FAQ 자동응답이 발동한 3주차 질문에 입력관리 그룹 태그('FAQ 자동응답')를 부여하는 스크립트
"""
faq_tagged.json(라이브 C/D 테스트에서 FAQ 발동으로 식별된 건)을 읽어,
question_norm 기준으로 redteam_question_groups를 찾아 tags에 'FAQ 자동응답'을 추가한다.

- 정확 일치(question_norm) 우선, 없으면 유사도 >= MATCH_THRESHOLD 최상위 그룹에 매칭.
- 재적재 시 tags는 question_norm 기준으로 보존되므로 이 태그도 유지된다.
- 기본은 dry-run. 실제 반영은 --apply 플래그.

Usage:
    backend/.venv/bin/python scripts/tag_faq_autorespond.py          # dry-run
    backend/.venv/bin/python scripts/tag_faq_autorespond.py --apply  # DB 반영
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.database import async_session  # noqa: E402
from app.models.redteam import RedteamQuestionGroup  # noqa: E402
from app.services.redteam_matching import normalize_question, similarity  # noqa: E402

TAG = "FAQ 자동응답"
MATCH_THRESHOLD = 0.72
TAGGED_JSON = (
    ROOT.parent / "exports" / "round3_live_CD_3주차" / "_data" / "faq_tagged.json"
)


def load_fired():
    rows = json.load(open(TAGGED_JSON))
    fired = []
    for r in rows:
        if r.get("faqC") or r.get("faqD"):
            fired.append(
                {
                    "id": r["id"],
                    "question": r["question"],
                    "faqNo": r.get("faqNoC") or r.get("faqNoD"),
                }
            )
    return fired


async def main(apply: bool):
    fired = load_fired()
    print(f"FAQ 발동 {len(fired)}건 로드 (faq_tagged.json)")

    async with async_session() as session:
        groups = (await session.execute(select(RedteamQuestionGroup))).scalars().all()
        print(f"DB 그룹 {len(groups)}개")
        by_norm = {g.question_norm: g for g in groups}

        matched, missed = [], []
        target_groups = {}  # gid -> group (중복 제거)
        for f in fired:
            n = normalize_question(f["question"])
            g = by_norm.get(n)
            how = "exact"
            if g is None:
                cand = max(
                    groups, key=lambda gg: similarity(n, gg.question_norm), default=None
                )
                if cand and similarity(n, cand.question_norm) >= MATCH_THRESHOLD:
                    g = cand
                    how = f"sim={similarity(n, cand.question_norm):.2f}"
            if g is None:
                missed.append(f)
                print(f"  ✗ MISS  id{f['id']} FAQ#{f['faqNo']} | {f['question'][:40]}")
            else:
                matched.append((f, g, how))
                target_groups[g.id] = g
                cur = list(g.tags or [])
                has = TAG in cur
                print(
                    f"  ✓ {how:8s} id{f['id']} FAQ#{f['faqNo']} -> group {g.id} "
                    f"{'[이미태그]' if has else '[추가]'} | {f['question'][:36]}"
                )

        print(
            f"\n매칭 {len(matched)} / 미매칭 {len(missed)} | "
            f"대상 그룹 {len(target_groups)}개 (질문 중복 통합)"
        )

        if not apply:
            print("\n[dry-run] --apply 를 붙이면 위 그룹들의 tags에 'FAQ 자동응답'을 추가한다.")
            return

        changed = 0
        for g in target_groups.values():
            cur = list(g.tags or [])
            if TAG not in cur:
                cur.append(TAG)
                g.tags = cur
                flag_modified(g, "tags")
                changed += 1
        await session.commit()
        print(f"\n[apply] tags 갱신 그룹 {changed}개 커밋 완료.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(args.apply))
