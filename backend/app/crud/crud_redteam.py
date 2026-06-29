"""
레드팀 대시보드 DB 연산(CRUD) Repository.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import String, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.redteam import RedteamQuestionGroup, RedteamResponse, RedteamReview
from app.schemas.redteam import TAG_PRESETS
from app.services.redteam_matching import similarity

MATCHED_STATUSES = ("auto", "confirmed")
UNMATCHED_STATUSES = ("none", "rejected")

# 이전 주차 봇 → 3주차 C/D 라인업 정규화 (표시용 기본맵, 추후 조정 가능)
PRIOR_BOT_TO_CD: dict[str, str | None] = {
    "A_통합": "D",  # 2주차 통합A → D (여정 동반자 계열)
    "C_정밀": "C",  # 2주차 정밀C → C (실무안내자 계열)
    "B_원리": None,  # 원리B 단종 → 별도표시
    "원문": None,  # 1주차 단일봇 → C/D 매핑 없음, 원문 별도표시
}


def normalize_bots(resp: RedteamResponse) -> tuple[dict[str, str | None], str | None]:
    """응답의 bot_responses를 3주차 C/D 키로 정규화 + 별도표시 note."""
    raw = resp.bot_responses or {}
    if resp.week == 3:
        return {"C": raw.get("C"), "D": raw.get("D")}, None
    bots: dict[str, str | None] = {}
    notes: list[str] = []
    for key, val in raw.items():
        if key == "적절챗봇":
            continue
        target = PRIOR_BOT_TO_CD.get(key)
        if target:
            bots[target] = val
        elif key == "원문":
            bots["원문"] = val
            notes.append("1주차 단일봇(원문)")
        elif key == "B_원리":
            notes.append("원리B 단종")
    return bots, ("; ".join(notes) or None)


# ─── 그룹 ─────────────────────────────────────────────


async def get_group(session: AsyncSession, group_id: int) -> RedteamQuestionGroup | None:
    result = await session.execute(
        select(RedteamQuestionGroup).where(RedteamQuestionGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def list_groups(
    session: AsyncSession,
    *,
    category: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    level: int | None = None,
    disposition: str | None = None,
    assignee: str | None = None,
    tag: str | None = None,
    week_present: int | None = None,
    matched_only: bool = False,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[Sequence[RedteamQuestionGroup], int]:
    """필터 + 페이지네이션으로 기준 질문 그룹 조회"""
    stmt = select(RedteamQuestionGroup)
    count_stmt = select(func.count()).select_from(RedteamQuestionGroup)

    conditions = []
    if category:
        conditions.append(RedteamQuestionGroup.category == category)
    if risk:
        conditions.append(RedteamQuestionGroup.risk == risk)
    if status:
        conditions.append(RedteamQuestionGroup.status == status)
    if level is not None:
        conditions.append(RedteamQuestionGroup.level == level)
    if disposition:
        conditions.append(RedteamQuestionGroup.disposition == disposition)
    if assignee:
        conditions.append(RedteamQuestionGroup.assignee == assignee)
    if tag:
        # JSON 컬럼은 containment 연산자 미지원 → 텍스트 캐스팅 ilike (부차 필터)
        conditions.append(cast(RedteamQuestionGroup.tags, String).ilike(f'%"{tag}"%'))
    if q:
        conditions.append(RedteamQuestionGroup.question.ilike(f"%{q}%"))

    # 특정 주차 매칭이 있는 그룹만 / 또는 임의 매칭 존재 그룹만
    if week_present in (1, 2) or matched_only:
        sub = select(RedteamResponse.group_id).where(
            RedteamResponse.match_status.in_(MATCHED_STATUSES)
        )
        if week_present in (1, 2):
            sub = sub.where(RedteamResponse.week == week_present)
        matched_ids_subq = sub.distinct().scalar_subquery()
        conditions.append(RedteamQuestionGroup.id.in_(matched_ids_subq))

    for c in conditions:
        stmt = stmt.where(c)
        count_stmt = count_stmt.where(c)

    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(RedteamQuestionGroup.id).offset((page - 1) * page_size).limit(page_size)
    groups = (await session.execute(stmt)).scalars().all()
    return groups, total


async def get_matched_weeks_map(
    session: AsyncSession, group_ids: list[int]
) -> dict[int, set[int]]:
    """그룹별 매칭된 주차 집합 {group_id: {1,2}}"""
    if not group_ids:
        return {}
    result = await session.execute(
        select(RedteamResponse.group_id, RedteamResponse.week)
        .where(
            RedteamResponse.group_id.in_(group_ids),
            RedteamResponse.match_status.in_(MATCHED_STATUSES),
        )
        .distinct()
    )
    out: dict[int, set[int]] = {}
    for gid, week in result.all():
        out.setdefault(gid, set()).add(week)
    return out


async def get_reviews_map(
    session: AsyncSession, group_ids: list[int]
) -> dict[int, list[RedteamReview]]:
    """그룹별 리뷰 목록 {group_id: [review,...]}"""
    if not group_ids:
        return {}
    result = await session.execute(
        select(RedteamReview).where(RedteamReview.group_id.in_(group_ids))
    )
    out: dict[int, list[RedteamReview]] = {}
    for rv in result.scalars().all():
        out.setdefault(rv.group_id, []).append(rv)
    return out


async def update_group_category(
    session: AsyncSession, group: RedteamQuestionGroup, category: str | None
) -> RedteamQuestionGroup:
    group.category = category
    group.category_source = "manual"
    group.updated_at = datetime.now(timezone.utc)
    session.add(group)
    await session.flush()
    await session.refresh(group)
    return group


async def update_group_manage(
    session: AsyncSession, group: RedteamQuestionGroup, fields: dict
) -> RedteamQuestionGroup:
    """중간보고 입력관리 부분 갱신 — fields에 담긴 키만 적용 (model_fields_set 기준)."""
    for key, value in fields.items():
        setattr(group, key, value)
    group.updated_at = datetime.now(timezone.utc)
    session.add(group)
    await session.flush()
    await session.refresh(group)
    return group


async def list_used_tags(session: AsyncSession) -> list[str]:
    """프리셋 ∪ 실제 사용된 distinct 태그 (정렬)."""
    rows = (await session.execute(select(RedteamQuestionGroup.tags))).scalars().all()
    used: set[str] = set(TAG_PRESETS)
    for tags in rows:
        for t in tags or []:
            used.add(t)
    return sorted(used)


# ─── 응답 ─────────────────────────────────────────────


async def get_group_responses(
    session: AsyncSession, group_id: int
) -> Sequence[RedteamResponse]:
    """그룹에 연결된 모든 응답 (3주차 base + 매칭된 1·2주차)"""
    result = await session.execute(
        select(RedteamResponse)
        .where(
            RedteamResponse.group_id == group_id,
            RedteamResponse.match_status != "rejected",
        )
        .order_by(RedteamResponse.week.desc(), RedteamResponse.id)
    )
    return result.scalars().all()


async def get_response(session: AsyncSession, response_id: int) -> RedteamResponse | None:
    result = await session.execute(
        select(RedteamResponse).where(RedteamResponse.id == response_id)
    )
    return result.scalar_one_or_none()


async def get_match_candidates(
    session: AsyncSession,
    group: RedteamQuestionGroup,
    *,
    limit: int = 10,
) -> list[tuple[RedteamResponse, float]]:
    """미연결 1·2주차 응답 중 유사도 상위 후보 (수동 매칭용)"""
    result = await session.execute(
        select(RedteamResponse).where(
            RedteamResponse.week.in_([1, 2]),
            RedteamResponse.match_status.in_(["none", "rejected"]),
            RedteamResponse.group_id.is_(None),
        )
    )
    scored: list[tuple[RedteamResponse, float]] = []
    for resp in result.scalars().all():
        score = similarity(group.question_norm, resp.question_norm)
        if score > 0:
            scored.append((resp, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


async def list_unmatched(
    session: AsyncSession,
    *,
    week: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[Sequence[RedteamResponse], int]:
    """미분류 큐 — 그룹에 연결되지 않은 1·2주차 응답 (수동 분류·연결 대상)."""
    conditions = [
        RedteamResponse.group_id.is_(None),
        RedteamResponse.match_status.in_(UNMATCHED_STATUSES),
        RedteamResponse.week.in_((1, 2)),
    ]
    if week in (1, 2):
        conditions.append(RedteamResponse.week == week)
    if q:
        conditions.append(RedteamResponse.question.ilike(f"%{q}%"))

    count_stmt = select(func.count()).select_from(RedteamResponse)
    stmt = select(RedteamResponse)
    for c in conditions:
        stmt = stmt.where(c)
        count_stmt = count_stmt.where(c)

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = (
        stmt.order_by(RedteamResponse.week, RedteamResponse.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return rows, total


async def link_response(
    session: AsyncSession, group_id: int, response: RedteamResponse, action: str
) -> RedteamResponse:
    """후보 매칭 확정(confirm) / 해제(reject)"""
    if action == "confirm":
        response.group_id = group_id
        response.match_status = "confirmed"
        if response.match_score is None:
            response.match_score = 1.0
    else:  # reject
        response.group_id = None
        response.match_status = "rejected"
    session.add(response)
    await session.flush()
    await session.refresh(response)
    return response


# ─── 리뷰 ─────────────────────────────────────────────


async def get_reviews(session: AsyncSession, group_id: int) -> Sequence[RedteamReview]:
    result = await session.execute(
        select(RedteamReview)
        .where(RedteamReview.group_id == group_id)
        .order_by(RedteamReview.reviewer)
    )
    return result.scalars().all()


async def upsert_review(
    session: AsyncSession,
    *,
    group_id: int,
    reviewer: str,
    correct_answer: str,
    week1_reflect: str,
    week2_reflect: str,
    week3_reflect: str,
) -> RedteamReview:
    """(group_id, reviewer) 리뷰 upsert"""
    result = await session.execute(
        select(RedteamReview).where(
            RedteamReview.group_id == group_id, RedteamReview.reviewer == reviewer
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        review = RedteamReview(group_id=group_id, reviewer=reviewer)

    review.correct_answer = correct_answer
    review.week1_reflect = week1_reflect
    review.week2_reflect = week2_reflect
    review.week3_reflect = week3_reflect
    review.updated_at = datetime.now(timezone.utc)
    session.add(review)
    await session.flush()
    await session.refresh(review)
    return review


# ─── 통계 ─────────────────────────────────────────────


async def get_stats(session: AsyncSession) -> dict:
    total_groups = (
        await session.execute(select(func.count()).select_from(RedteamQuestionGroup))
    ).scalar_one()
    total_responses = (
        await session.execute(select(func.count()).select_from(RedteamResponse))
    ).scalar_one()

    by_category: dict[str, int] = {}
    cat_rows = await session.execute(
        select(RedteamQuestionGroup.category, func.count()).group_by(
            RedteamQuestionGroup.category
        )
    )
    for cat, cnt in cat_rows.all():
        by_category[cat or "미분류"] = cnt

    by_risk: dict[str, int] = {}
    risk_rows = await session.execute(
        select(RedteamQuestionGroup.risk, func.count()).group_by(RedteamQuestionGroup.risk)
    )
    for risk, cnt in risk_rows.all():
        by_risk[risk or "없음"] = cnt

    matched_rows = await session.execute(
        select(RedteamResponse.week, func.count(func.distinct(RedteamResponse.group_id)))
        .where(RedteamResponse.match_status.in_(MATCHED_STATUSES))
        .group_by(RedteamResponse.week)
    )
    matched_map = {week: cnt for week, cnt in matched_rows.all()}

    progress_rows = await session.execute(
        select(RedteamReview.reviewer, func.count(func.distinct(RedteamReview.group_id))).group_by(
            RedteamReview.reviewer
        )
    )
    review_progress = {reviewer: cnt for reviewer, cnt in progress_rows.all()}

    return {
        "total_groups": total_groups,
        "total_responses": total_responses,
        "by_category": by_category,
        "by_risk": by_risk,
        "matched_week2": matched_map.get(2, 0),
        "matched_week1": matched_map.get(1, 0),
        "review_progress": review_progress,
    }


async def get_manage_stats(session: AsyncSession) -> dict:
    """중간보고 요약 — 상태·레벨·분류·태그·담당자·미분류 분포."""
    from collections import Counter

    groups = (await session.execute(select(RedteamQuestionGroup))).scalars().all()

    by_status: Counter = Counter(g.status for g in groups)
    by_level: Counter = Counter(
        str(g.level) if g.level is not None else "미분류" for g in groups
    )
    by_disposition: Counter = Counter(g.disposition for g in groups)
    by_tag: Counter = Counter()
    assignee_load: Counter = Counter()
    for g in groups:
        for t in g.tags or []:
            by_tag[t] += 1
        if g.assignee:
            assignee_load[g.assignee] += 1

    unmatched_rows = await session.execute(
        select(RedteamResponse.week, func.count())
        .where(
            RedteamResponse.group_id.is_(None),
            RedteamResponse.match_status.in_(UNMATCHED_STATUSES),
            RedteamResponse.week.in_((1, 2)),
        )
        .group_by(RedteamResponse.week)
    )
    um = {week: cnt for week, cnt in unmatched_rows.all()}

    return {
        "total_groups": len(groups),
        "by_status": dict(by_status),
        "by_level": dict(by_level),
        "by_disposition": dict(by_disposition),
        "by_tag": dict(by_tag.most_common()),
        "unmatched_week2": um.get(2, 0),
        "unmatched_week1": um.get(1, 0),
        "assignee_load": dict(assignee_load.most_common()),
    }


# ─── 보고용 종합 집계 ─────────────────────────────────────────

RISK_ORDER = {"없음": 0, "하": 1, "중": 2, "상": 3}


def _classify_pref(value: str | None) -> str | None:
    """3주차 적절챗봇 값을 C / D / 부적절로 정규화"""
    if not value:
        return None
    if "챗봇C" in value or "실무안내자" in value:
        return "C"
    if "챗봇D" in value or "여정" in value:
        return "D"
    if "둘다" in value or "못함" in value or "부적절" in value:
        return "부적절"
    return None


async def get_report(session: AsyncSession) -> dict:
    """윗선 보고용 종합 집계 — 위험도·품질, 주차별 추이, 봇 비교."""
    from collections import Counter

    groups = (await session.execute(select(RedteamQuestionGroup))).scalars().all()
    responses = (await session.execute(select(RedteamResponse))).scalars().all()
    reviews = (await session.execute(select(RedteamReview))).scalars().all()

    group_by_id = {g.id: g for g in groups}

    # 카테고리/위험도 (그룹 단위)
    category_dist = Counter(g.category or "미분류" for g in groups)
    risk_dist = Counter(g.risk or "없음" for g in groups)

    # 위험도 × 카테고리
    risk_by_cat: dict[str, Counter] = {}
    for g in groups:
        cat = g.category or "미분류"
        risk_by_cat.setdefault(cat, Counter())[g.risk or "없음"] += 1

    # 응답: 주차별 카운트 / 평점 / 적절챗봇
    by_week: Counter = Counter()
    ratings_by_week: dict[int, list[float]] = {1: [], 2: [], 3: []}
    pref_counter: Counter = Counter()
    pref_by_cat: dict[str, Counter] = {}
    for r in responses:
        by_week[r.week] += 1
        if r.rating is not None:
            ratings_by_week[r.week].append(r.rating)
        if r.week == 3 and r.bot_responses:
            pref = _classify_pref(r.bot_responses.get("적절챗봇"))
            if pref:
                pref_counter[pref] += 1
                g = group_by_id.get(r.group_id) if r.group_id else None
                cat = (g.category if g else None) or "미분류"
                pref_by_cat.setdefault(cat, Counter())[pref] += 1

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 2) if xs else None

    # 평점 분포 (1·3주차)
    rating_by_week = []
    for score in range(1, 6):
        rating_by_week.append(
            {
                "rating": score,
                "week1": sum(1 for v in ratings_by_week[1] if round(v) == score),
                "week3": sum(1 for v in ratings_by_week[3] if round(v) == score),
            }
        )

    # 평점 추이 (주차별 평균 — 2주차는 평점 미측정)
    rating_trend = [
        {"week": w, "label": f"{w}주차", "avg": _avg(ratings_by_week[w]), "count": len(ratings_by_week[w])}
        for w in (1, 2, 3)
    ]

    # 그룹별 3주차 평점 평균 (상위 위험 질문 표용)
    group_ratings: dict[int, list[float]] = {}
    for r in responses:
        if r.week == 3 and r.rating is not None and r.group_id:
            group_ratings.setdefault(r.group_id, []).append(r.rating)

    top_risk = sorted(
        (g for g in groups if (g.risk or "없음") in ("상", "중")),
        key=lambda g: (-RISK_ORDER.get(g.risk or "없음", 0), _avg(group_ratings.get(g.id, [])) or 5),
    )
    top_risk_questions = [
        {
            "group_id": g.id,
            "question": g.question,
            "category": g.category,
            "risk": g.risk,
            "rating_avg": _avg(group_ratings.get(g.id, [])),
        }
        for g in top_risk[:25]
    ]

    # 리뷰 반영 결정 요약
    reflect_summary = []
    for week_key, label in (("week1_reflect", 1), ("week2_reflect", 2), ("week3_reflect", 3)):
        c = Counter(getattr(rv, week_key) for rv in reviews)
        reflect_summary.append(
            {"week": label, "reflect": c.get("reflect", 0), "skip": c.get("skip", 0), "pending": c.get("pending", 0)}
        )

    # ─── 개선 추적: 같은 질문의 1주차 vs 3주차 평점 델타 ───
    w1_group_ratings: dict[int, list[float]] = {}
    for r in responses:
        if r.week == 1 and r.rating is not None and r.group_id:
            w1_group_ratings.setdefault(r.group_id, []).append(r.rating)

    improvement_rows = []
    imp_counter: Counter = Counter()
    for gid, w3 in group_ratings.items():
        w1 = w1_group_ratings.get(gid)
        if not w1 or not w3:
            continue
        w1_avg = round(sum(w1) / len(w1), 2)
        w3_avg = round(sum(w3) / len(w3), 2)
        delta = round(w3_avg - w1_avg, 2)
        bucket = "improved" if delta > 0.25 else "declined" if delta < -0.25 else "same"
        imp_counter[bucket] += 1
        g = group_by_id.get(gid)
        improvement_rows.append(
            {
                "group_id": gid,
                "question": g.question if g else "",
                "category": g.category if g else None,
                "week1_avg": w1_avg,
                "week3_avg": w3_avg,
                "delta": delta,
            }
        )
    bot_improvement = {
        "improved": imp_counter.get("improved", 0),
        "same": imp_counter.get("same", 0),
        "declined": imp_counter.get("declined", 0),
        "compared": len(improvement_rows),
        "top_improved": sorted((r for r in improvement_rows if r["delta"] > 0.25), key=lambda r: -r["delta"])[:10],
        "top_declined": sorted((r for r in improvement_rows if r["delta"] < -0.25), key=lambda r: r["delta"])[:10],
    }

    # ─── 반영 현황(위험도 교차) & 리뷰어 합의도 (3주차 반영결정 기준) ───
    reviews_by_group: dict[int, list] = {}
    for rv in reviews:
        reviews_by_group.setdefault(rv.group_id, []).append(rv)

    reflect_by_risk_counter: dict[str, Counter] = {lv: Counter() for lv in ("없음", "하", "중", "상")}
    agree_counter: Counter = Counter()
    split_groups: list[dict] = []
    pending_high_risk: list[dict] = []
    for g in groups:
        lv = g.risk or "없음"
        grp_reviews = reviews_by_group.get(g.id, [])
        decided = [rv.week3_reflect for rv in grp_reviews if rv.week3_reflect in ("reflect", "skip")]
        if not decided:
            reflect_by_risk_counter[lv]["pending"] += 1
            if lv in ("상", "중"):
                pending_high_risk.append(
                    {
                        "group_id": g.id,
                        "question": g.question,
                        "category": g.category,
                        "risk": g.risk,
                        "reviewer_count": len(grp_reviews),
                    }
                )
        else:
            reflect_by_risk_counter[lv]["reflect" if decided.count("reflect") >= decided.count("skip") else "skip"] += 1

        if len(decided) >= 2:
            if all(d == "reflect" for d in decided):
                agree_counter["unanimous_reflect"] += 1
            elif all(d == "skip" for d in decided):
                agree_counter["unanimous_skip"] += 1
            else:
                agree_counter["split"] += 1
                split_groups.append(
                    {
                        "group_id": g.id,
                        "question": g.question,
                        "category": g.category,
                        "risk": g.risk,
                        "reflect": decided.count("reflect"),
                        "skip": decided.count("skip"),
                    }
                )

    reflect_by_risk = [
        {
            "risk": lv,
            "reflect": reflect_by_risk_counter[lv].get("reflect", 0),
            "skip": reflect_by_risk_counter[lv].get("skip", 0),
            "pending": reflect_by_risk_counter[lv].get("pending", 0),
        }
        for lv in ("상", "중", "하", "없음")
    ]
    reviewer_agreement = {
        "unanimous_reflect": agree_counter.get("unanimous_reflect", 0),
        "unanimous_skip": agree_counter.get("unanimous_skip", 0),
        "split": agree_counter.get("split", 0),
    }
    pending_high_risk.sort(key=lambda r: -RISK_ORDER.get(r["risk"] or "없음", 0))
    split_groups.sort(key=lambda r: -RISK_ORDER.get(r["risk"] or "없음", 0))

    return {
        "summary": {
            "total_groups": len(groups),
            "total_responses": len(responses),
            "responses_by_week": {str(w): by_week.get(w, 0) for w in (1, 2, 3)},
            "high_risk": risk_dist.get("상", 0),
            "mid_risk": risk_dist.get("중", 0),
            "avg_rating_week1": _avg(ratings_by_week[1]),
            "avg_rating_week3": _avg(ratings_by_week[3]),
            "bot_c": pref_counter.get("C", 0),
            "bot_d": pref_counter.get("D", 0),
            "bot_none": pref_counter.get("부적절", 0),
        },
        "risk_distribution": [{"level": lv, "count": risk_dist.get(lv, 0)} for lv in ("없음", "하", "중", "상")],
        "category_distribution": [
            {"category": k, "count": v} for k, v in category_dist.most_common()
        ],
        "risk_by_category": [
            {
                "category": cat,
                "없음": cnt.get("없음", 0),
                "하": cnt.get("하", 0),
                "중": cnt.get("중", 0),
                "상": cnt.get("상", 0),
            }
            for cat, cnt in sorted(risk_by_cat.items(), key=lambda kv: -sum(kv[1].values()))
        ],
        "rating_by_week": rating_by_week,
        "rating_trend": rating_trend,
        "bot_preference": [
            {"bot": b, "count": pref_counter.get(b, 0)} for b in ("C", "D", "부적절")
        ],
        "bot_by_category": [
            {
                "category": cat,
                "C": cnt.get("C", 0),
                "D": cnt.get("D", 0),
                "부적절": cnt.get("부적절", 0),
            }
            for cat, cnt in sorted(pref_by_cat.items(), key=lambda kv: -sum(kv[1].values()))
        ],
        "reflect_summary": reflect_summary,
        "reflect_by_risk": reflect_by_risk,
        "reviewer_agreement": reviewer_agreement,
        "pending_high_risk": pending_high_risk,
        "split_groups": split_groups,
        "bot_improvement": bot_improvement,
        "top_risk_questions": top_risk_questions,
    }
