# FAQ 매칭 감도(threshold) 테스트 — 프로브 6개의 원시 코사인 유사도 측정 + 실제 override 확인
import asyncio
import sys
import logging

logging.disable(logging.INFO)
sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

BOT_ID = 5  # 블레싱 가
TARGET_FAQ_ID = 3  # "축복정리 절차와 요건이 뭐야?"
JEONGRI_FAMILY = {1, 2, 3, 4, 5, 6, 7, 8, 9}  # '축복 정리' 카테고리 FAQ ids

# (프로브, 기대) — pass=통과기대(패러프레이즈), block=비통과기대(유사어·다른의도)
PROBES = [
    ("축복을 정리하려면 어떤 절차와 조건이 필요한가요?", "pass"),
    ("축복정리 하는 방법하고 갖춰야 할 요건 알려줘", "pass"),
    ("축복 정리 진행 절차가 어떻게 되나요?", "pass"),
    ("축복식 준비 절차와 준비물이 뭐야?", "block"),
    ("축복정리하고 나서 재축복 받는 절차는?", "block"),
    ("축복 매칭은 어떤 절차로 이뤄지나요?", "block"),
]


async def raw_topk(session, bot_id, query_text, k=3):
    """threshold 게이트 없이 top-k FAQ와 원시 코사인 유사도 반환 (faq_service SQL 재사용)."""
    from sqlalchemy import text
    from app.utils.embeddings import get_embedding

    qv = await get_embedding(query_text)
    vec = f"[{','.join(str(v) for v in qv)}]"
    sql = f"""
        SELECT id, question, 1 - (question_vector <=> '{vec}'::vector) AS sim
        FROM faqs
        WHERE bot_id = :bot_id AND is_active = true AND question_vector IS NOT NULL
        ORDER BY question_vector <=> '{vec}'::vector
        LIMIT {k}
    """
    rows = (await session.execute(text(sql), {"bot_id": bot_id})).fetchall()
    return [(r[0], r[1], float(r[2])) for r in rows]


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.services.faq_service import search_faq_override

    async with async_session() as s:
        print(f"대상 봇 id={BOT_ID} · 타깃 FAQ id={TARGET_FAQ_ID} '축복정리 절차와 요건이 뭐야?'\n")
        print(f"{'기대':<6}{'유사도':>8}  {'top1':>5}  {'정리족?':<7}{'@0.85':<8} 프로브")
        print("-" * 96)

        results = []
        for probe, expect in PROBES:
            topk = await raw_topk(s, BOT_ID, probe, k=3)
            top_id, top_q, top_sim = topk[0]
            family = "예" if top_id in JEONGRI_FAMILY else "아니오"
            override = await search_faq_override(s, BOT_ID, probe)  # 실제 0.85 게이트
            ov = f"id={override.faq_id}" if override else "미발동"
            results.append((probe, expect, top_id, top_q, top_sim, override))
            print(f"{expect:<6}{top_sim:>8.4f}  id={top_id:<3} {family:<7}{ov:<8} {probe}")
            for fid, fq, fs in topk[1:]:
                print(f"{'':<6}{fs:>8.4f}  id={fid:<3} {'':<7}{'':<8}   ↳ (참고) {fq[:40]}")
            await asyncio.sleep(0.4)

        # 분석
        pass_sims = [r[4] for r in results if r[1] == "pass"]
        block_sims = [r[4] for r in results if r[1] == "block"]
        pass_min, block_max = min(pass_sims), max(block_sims)
        print("\n" + "=" * 96)
        print(f"통과기대 유사도: {[f'{x:.4f}' for x in sorted(pass_sims, reverse=True)]}  (최저 {pass_min:.4f})")
        print(f"차단기대 유사도: {[f'{x:.4f}' for x in sorted(block_sims, reverse=True)]}  (최고 {block_max:.4f})")
        gap = pass_min - block_max
        if gap > 0:
            rec = round(block_max + gap / 2, 3)
            print(f"분리 간극 {gap:.4f} 존재 → 권장 threshold ≈ {rec} (통과최저~차단최고 중간)")
            print(f"  · 보수적(오발동 최소화) 상단: {round(pass_min - 0.005, 3)}")
        else:
            print(f"분리 간극 없음(겹침 {-gap:.4f}) → 유사도만으로 완전분리 불가. 프로브/타깃 재설계 필요.")

        # 0.85 기준 오탐/미탐
        false_neg = sum(1 for r in results if r[1] == "pass" and r[5] is None)
        false_pos = sum(1 for r in results if r[1] == "block" and r[5] is not None and r[2] == TARGET_FAQ_ID)
        print(f"\n@0.85 기준: 통과기대 미발동(미탐) {false_neg}/3 · 차단기대 타깃오발동(오탐) {false_pos}/3")


if __name__ == "__main__":
    asyncio.run(main())
