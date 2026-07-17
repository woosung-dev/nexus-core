"""
레드팀 1·2·3주차 피드백 xlsx 임포트 스크립트.

- 3주차를 기준(base)으로 고유 질문마다 그룹을 만들고,
- 1·2주차 응답을 유사도로 매칭해 그룹에 연결하며,
- 카테고리를 자동 분류한다(매칭된 이전 주차 유형 상속 → 키워드 휴리스틱).
- 재실행 시 응답/그룹은 재적재하되 관리자 입력(reviews)은 question_norm 기준으로 보존한다.

Usage:
    uv run python scripts/import_redteam.py
    uv run python scripts/import_redteam.py --week3 a.xlsx --week2 b.xlsx --week1 c.xlsx
    uv run python scripts/import_redteam.py --reset-reviews   # 리뷰까지 초기화
"""

import argparse
import asyncio
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.database import async_session  # noqa: E402
from app.models.redteam import (  # noqa: E402
    RedteamManageFeedback,
    RedteamQuestionGroup,
    RedteamResponse,
    RedteamReview,
    RedteamTestbotEval,
)
from app.services.redteam_matching import (  # noqa: E402
    canonical_category,
    classify_by_keywords,
    normalize_question,
    similarity,
)

DOWNLOADS = Path("/Users/woosung/Downloads")
DEFAULT_FILES = {
    3: DOWNLOADS / "축복·가정관리 AI 상담 챗봇 테스트 및 피드백 v3주차(레드팀)(응답) (5).xlsx",
    2: DOWNLOADS / "축복·가정관리 AI 상담 챗봇 테스트 및 피드백 v2주차(레드팀)(응답) (3).xlsx",
    1: DOWNLOADS / "축복·가정관리 AI 상담 챗봇 테스트 및 피드백 (레드팀)(응답) (6).xlsx",
}

MATCH_THRESHOLD = 0.72
RISK_RANK = {"없음": 0, "하": 1, "중": 2, "상": 3}

# 3주차 제출자 이름 표기 교정 (오타/이형 → 정자). 3주차에만 적용.
# 정확한 매핑은 사용자 확정 예정 — 확정 시 아래에 항목 추가.
WEEK3_SUBMITTER_FIX: dict[str, str] = {
    # "이주하": "이주화",
}


def _fix_submitter(name: str | None) -> str | None:
    """3주차 제출자 이름 교정 (WEEK3_SUBMITTER_FIX 매핑)"""
    if not name:
        return name
    return WEEK3_SUBMITTER_FIX.get(name.strip(), name.strip())


def _s(v) -> str | None:
    """셀 값을 문자열로 정리 (빈값은 None)"""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _num(v) -> float | None:
    try:
        return float(v) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _ts(v) -> datetime | None:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return None


def _short_risk(v: str | None) -> str | None:
    """3주차 위험도 전체 문구를 짧은 라벨(없음/하/중/상)로 정규화"""
    if not v:
        return None
    for label in ("없음", "하", "중", "상"):
        if v.startswith(label):
            return label
    return None


def _join_feedback(*parts: tuple[str, str | None]) -> str | None:
    """라벨이 붙은 자유서술들을 하나로 합침"""
    chunks = [f"[{label}] {val}" for label, val in parts if val]
    return "\n".join(chunks) if chunks else None


def _load_rows(path: Path) -> list[tuple]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in r):
            continue
        rows.append(r)
    return rows


def parse_week3(rows: list[tuple]) -> list[RedteamResponse]:
    out = []
    for r in rows:
        q = _s(r[2])
        if not q:
            continue
        out.append(
            RedteamResponse(
                week=3,
                submitter=_fix_submitter(_s(r[1])),
                submitted_at=_ts(r[0]),
                question=q,
                question_norm=normalize_question(q),
                category=None,  # 3주차엔 유형 칸 없음
                rating=_num(r[6]),
                risk=_short_risk(_s(r[10])),
                bot_responses={"C": _s(r[3]), "D": _s(r[4]), "적절챗봇": _s(r[5])},
                feedback_text=_join_feedback(
                    ("좋았던 점", _s(r[7])), ("아쉬웠던 점", _s(r[8])), ("보완·제안", _s(r[9]))
                ),
                raw={"기타": _s(r[11])},
                match_status="base",
            )
        )
    return out


def parse_week2(rows: list[tuple]) -> list[RedteamResponse]:
    out = []
    for r in rows:
        q = _s(r[3])
        if not q:
            continue
        c_jeongmil = "\n".join(p for p in (_s(r[6]), _s(r[7])) if p) or None
        out.append(
            RedteamResponse(
                week=2,
                submitter=_s(r[1]),
                submitted_at=_ts(r[0]),
                question=q,
                question_norm=normalize_question(q),
                category=canonical_category(_s(r[2])),
                bot_responses={"A_통합": _s(r[4]), "B_원리": _s(r[5]), "C_정밀": c_jeongmil},
                feedback_text=_s(r[8]),
                raw={"기타": _s(r[9]), "질문유형_원본": _s(r[2])},
            )
        )
    return out


def parse_week1(rows: list[tuple]) -> list[RedteamResponse]:
    out = []
    for r in rows:
        q = _s(r[3])
        if not q:
            continue
        out.append(
            RedteamResponse(
                week=1,
                submitter=_s(r[1]),
                submitted_at=_ts(r[0]),
                question=q,
                question_norm=normalize_question(q),
                category=canonical_category(_s(r[2])),
                rating=_num(r[5]),
                bot_responses={"원문": _s(r[4])},
                feedback_text=_join_feedback(("구체 피드백", _s(r[7]))),
                raw={
                    "개선영역": _s(r[6]),
                    "학습키워드": _s(r[8]),
                    "기타": _s(r[9]),
                    "질문유형_원본": _s(r[2]),
                },
                match_status="none",
            )
        )
    return out


def build_groups_all(
    week3: list[RedteamResponse],
    week2: list[RedteamResponse],
    week1: list[RedteamResponse],
) -> dict[str, RedteamQuestionGroup]:
    """전 주차 고유 질문(question_norm)마다 그룹 생성 — 전건 분류용.

    3주차를 기준으로 우선 처리해 대표 질문 텍스트·위험도를 3주차 값으로 잡고,
    1·2주차에만 있는 질문은 별도 그룹으로 승격한다.
    """
    groups: dict[str, RedteamQuestionGroup] = {}
    # 3주차 먼저 → 대표 질문/위험도 기준
    for resp in week3:
        norm = resp.question_norm
        g = groups.get(norm)
        if g is None:
            g = groups[norm] = RedteamQuestionGroup(
                question=resp.question, question_norm=norm, category=None, category_source="auto"
            )
        # 위험도 최대값 갱신 (위험도는 3주차에만 존재)
        if resp.risk and RISK_RANK.get(resp.risk, 0) > RISK_RANK.get(g.risk or "없음", 0):
            g.risk = resp.risk
    # 2·1주차 → 3주차에 없던 질문이면 그룹 승격 (대표 텍스트는 해당 주차 원문)
    for resp in (*week2, *week1):
        norm = resp.question_norm
        if norm not in groups:
            groups[norm] = RedteamQuestionGroup(
                question=resp.question, question_norm=norm, category=None, category_source="auto"
            )
    return groups


def match_prior(
    prior: list[RedteamResponse], group_norms: list[tuple[str, str]]
) -> None:
    """이전 주차 응답을 가장 유사한 그룹에 연결 (임계값 이상). group_norms=[(norm, gid_placeholder)]"""
    for resp in prior:
        best_norm, best_score = None, 0.0
        for gnorm, _ in group_norms:
            score = similarity(resp.question_norm, gnorm)
            if score > best_score:
                best_norm, best_score = gnorm, score
        if best_norm is not None and best_score >= MATCH_THRESHOLD:
            resp._match_norm = best_norm  # type: ignore[attr-defined]
            resp.match_score = round(best_score, 4)
            resp.match_status = "auto"


def assign_group_categories(
    groups: dict[str, RedteamQuestionGroup],
    matched_by_group: dict[str, list[RedteamResponse]],
) -> None:
    """그룹 카테고리 = 매칭된 이전 주차 유형 다수결 → 없으면 키워드 휴리스틱"""
    for norm, g in groups.items():
        cats = [m.category for m in matched_by_group.get(norm, []) if m.category]
        if cats:
            g.category = Counter(cats).most_common(1)[0][0]
        else:
            g.category = classify_by_keywords(g.question)


async def import_all(files: dict[int, Path], reset_reviews: bool) -> None:
    for week, p in files.items():
        if not p.exists():
            raise SystemExit(f"❌ {week}주차 파일 없음: {p}")

    week3 = parse_week3(_load_rows(files[3]))
    week2 = parse_week2(_load_rows(files[2]))
    week1 = parse_week1(_load_rows(files[1]))
    print(f"파싱: 3주차 {len(week3)}건 / 2주차 {len(week2)}건 / 1주차 {len(week1)}건")

    groups = build_groups_all(week3, week2, week1)
    w3_norms = {r.question_norm for r in week3}
    prior_only = sum(1 for n in groups if n not in w3_norms)
    print(
        f"그룹(전 주차 고유질문): {len(groups)}개 — "
        f"3주차 기준 {len(w3_norms)} / 1·2주차 전용 {prior_only}"
    )

    # 카테고리: 같은 norm의 1·2주차 유형 다수결 → 없으면 키워드 휴리스틱
    cat_src: dict[str, list[RedteamResponse]] = {}
    for resp in (*week2, *week1):
        cat_src.setdefault(resp.question_norm, []).append(resp)
    assign_group_categories(groups, cat_src)
    cat_dist = Counter(g.category or "미분류" for g in groups.values())
    print(f"카테고리 분포: {dict(cat_dist)}")

    async with async_session() as session:
        # 기존 리뷰 보존 (question_norm 기준)
        saved_reviews: list[dict] = []
        if not reset_reviews:
            res = await session.execute(
                text(
                    "SELECT g.question_norm, r.reviewer, r.correct_answer, "
                    "r.week1_reflect, r.week2_reflect, r.week3_reflect "
                    "FROM redteam_reviews r JOIN redteam_question_groups g ON r.group_id = g.id"
                )
            )
            saved_reviews = [dict(row._mapping) for row in res]
            if saved_reviews:
                print(f"보존할 리뷰: {len(saved_reviews)}건")

        # 기존 관리필드 보존 (question_norm 기준) — 입력관리 작업도 리뷰와 함께 보존
        saved_manage: dict[str, dict] = {}
        if not reset_reviews:
            res2 = await session.execute(
                text(
                    "SELECT question_norm, status, level, disposition, tags, "
                    "assignee, model_answer FROM redteam_question_groups"
                )
            )
            saved_manage = {row._mapping["question_norm"]: dict(row._mapping) for row in res2}
            if saved_manage:
                print(f"보존할 관리필드 그룹: {len(saved_manage)}건")

        # 기존 담당자 피드백 보존 (question_norm 기준)
        saved_feedback: list[dict] = []
        if not reset_reviews:
            res3 = await session.execute(
                text(
                    "SELECT g.question_norm, f.author, f.content, f.created_at "
                    "FROM redteam_manage_feedback f "
                    "JOIN redteam_question_groups g ON f.group_id = g.id"
                )
            )
            saved_feedback = [dict(row._mapping) for row in res3]
            if saved_feedback:
                print(f"보존할 피드백: {len(saved_feedback)}건")

        # 기존 테스트 봇 재검증 보존 (question_norm 기준) — CASCADE로 지워지므로 함께 보존
        saved_testbot: list[dict] = []
        if not reset_reviews:
            res4 = await session.execute(
                text(
                    "SELECT g.question_norm, t.run_label, t.bot_label, t.bot_id, t.bot_model, "
                    "t.answer, t.citations, t.bf_citations, t.risk_recur, t.risk_recur_detail, "
                    "t.independent_risk, t.independent_risk_detail, t.ai_rating, t.ai_rating_detail, "
                    "t.eval_engine "
                    "FROM redteam_testbot_evals t "
                    "JOIN redteam_question_groups g ON t.group_id = g.id"
                )
            )
            saved_testbot = [dict(row._mapping) for row in res4]
            if saved_testbot:
                print(f"보존할 테스트봇 평가: {len(saved_testbot)}건")

        # 초기화 (CASCADE로 응답/리뷰 함께 제거)
        await session.execute(
            text("TRUNCATE redteam_responses, redteam_reviews, redteam_question_groups "
                 "RESTART IDENTITY CASCADE")
        )

        # 그룹 삽입 → id 확보
        session.add_all(list(groups.values()))
        await session.flush()
        norm_to_gid = {g.question_norm: g.id for g in groups.values()}

        # 관리필드 복원 (question_norm 기준) — flush 이후 속성 변경은 commit 시 UPDATE
        if saved_manage:
            restored_manage = 0
            for g in groups.values():
                m = saved_manage.get(g.question_norm)
                if not m:
                    continue
                g.status = m["status"] or "대기"
                g.level = m["level"]
                g.disposition = m["disposition"] or "미정"
                g.tags = m["tags"] or []
                g.assignee = m["assignee"]
                g.model_answer = m["model_answer"] or ""
                restored_manage += 1
            if restored_manage:
                print(f"관리필드 복원: {restored_manage}건")

        # 응답 group_id 연결 — 모든 응답이 자기 norm 그룹에 속함(미연결 없음)
        for resp in week3:
            resp.group_id = norm_to_gid[resp.question_norm]
            resp.match_status = "base"
        for resp in (*week2, *week1):
            resp.group_id = norm_to_gid[resp.question_norm]
            resp.match_status = "member"

        session.add_all([*week3, *week2, *week1])
        await session.flush()

        # 리뷰 복원
        restored = 0
        for rv in saved_reviews:
            gid = norm_to_gid.get(rv["question_norm"])
            if gid is None:
                continue
            session.add(
                RedteamReview(
                    group_id=gid,
                    reviewer=rv["reviewer"],
                    correct_answer=rv["correct_answer"] or "",
                    week1_reflect=rv["week1_reflect"],
                    week2_reflect=rv["week2_reflect"],
                    week3_reflect=rv["week3_reflect"],
                )
            )
            restored += 1
        if restored:
            print(f"리뷰 복원: {restored}건")

        # 피드백 복원 (question_norm 기준)
        restored_fb = 0
        for fb in saved_feedback:
            gid = norm_to_gid.get(fb["question_norm"])
            if gid is None:
                continue
            session.add(
                RedteamManageFeedback(
                    group_id=gid,
                    author=fb["author"],
                    content=fb["content"],
                    created_at=fb["created_at"],
                )
            )
            restored_fb += 1
        if restored_fb:
            print(f"피드백 복원: {restored_fb}건")

        # 테스트 봇 재검증 복원 (question_norm 기준)
        restored_tb = 0
        for t in saved_testbot:
            gid = norm_to_gid.get(t["question_norm"])
            if gid is None:
                continue
            session.add(
                RedteamTestbotEval(
                    group_id=gid,
                    question_norm=t["question_norm"],
                    run_label=t["run_label"],
                    bot_label=t["bot_label"],
                    bot_id=t["bot_id"],
                    bot_model=t["bot_model"],
                    answer=t["answer"] or "",
                    citations=t["citations"] or [],
                    bf_citations=t["bf_citations"] or [],
                    risk_recur=t["risk_recur"],
                    risk_recur_detail=t["risk_recur_detail"] or "",
                    independent_risk=t["independent_risk"],
                    independent_risk_detail=t["independent_risk_detail"] or "",
                    ai_rating=t["ai_rating"],
                    ai_rating_detail=t["ai_rating_detail"] or "",
                    eval_engine=t["eval_engine"] or "codex",
                )
            )
            restored_tb += 1
        if restored_tb:
            print(f"테스트봇 평가 복원: {restored_tb}건")

        await session.commit()

    print(
        f"✅ 완료 — 그룹 {len(groups)} / 응답 {len(week3) + len(week2) + len(week1)} "
        f"(3주차 {len(week3)}, 2주차 {len(week2)}, 1주차 {len(week1)})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="레드팀 피드백 xlsx 임포트")
    parser.add_argument("--week3", type=Path, default=DEFAULT_FILES[3])
    parser.add_argument("--week2", type=Path, default=DEFAULT_FILES[2])
    parser.add_argument("--week1", type=Path, default=DEFAULT_FILES[1])
    parser.add_argument("--reset-reviews", action="store_true", help="관리자 입력(리뷰)까지 초기화")
    args = parser.parse_args()

    files = {3: args.week3, 2: args.week2, 1: args.week1}
    asyncio.run(import_all(files, args.reset_reviews))


if __name__ == "__main__":
    main()
