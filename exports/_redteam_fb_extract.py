# 레드팀 1·2·3주차 응답을 DB에서 추출해 피드백 분류용 레코드 JSON 생성
import asyncio
import difflib
import json
import os
import re
from pathlib import Path

import asyncpg

BASE = Path("/Users/woosung/project/agy-project/nexus-core/exports")
OUT = BASE / "_redteam_fb_records.json"

# FAQ 지정답변 35종 (블레싱네비게이션). 봇 응답이 이와 거의 일치하면 FAQ 자동응답 발동.
FAQ_JSON = BASE / "faq_test" / "faqs_export.json"
FAQ_MATCH_TH = 0.92          # _build_faq_compare.py 와 동일 임계값
FAQ_EXCLUDE_BOTS = {"적절챗봇"}  # 적절챗봇=모범답변 참조용, FAQ 발동 대상 아님

# 로컬 docker nexus_db (호스트는 localhost override)
DSN = os.environ.get(
    "REDTEAM_DSN",
    "postgresql://nexus_user:nexus_pass@localhost:5432/nexus_core",
)

# 3주차 submitter 절단·노이즈 보정 (절단명 → 정식명, 질문 누수행 → 미상)
SUBMITTER_FIX = {
    "이보": "이보영",
    "김관": "김관우",
    "김소": "김소영",
    "이주": "이주화",
    "이진": "이진영",
    "미야자키 시호": "미야자키시호",
    "특별성염은 뭐예요?": "(미상)",
}

# 봇 응답 키 → 사람이 읽는 라벨(주차 맥락 유지). 필터/태깅 대상봇 어휘.
BOT_LABEL = {
    "원문": "1주차 원문봇",
    "A_통합": "통합(A)",
    "B_원리": "원리(B)",
    "C_정밀": "정밀(C)",
    "C": "C",
    "D": "D",
    "적절챗봇": "적절챗봇",
}


def clean(s):
    if s is None:
        return ""
    return re.sub(r"\s+\n", "\n", str(s)).strip()


def faq_norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def detect_faq(bot_resp, faq_answers):
    """봇 응답별로 FAQ 지정답변과 최고 유사도를 재 → 발동 봇 라벨/FAQ id 목록."""
    fired_bots, fired_ids = [], []
    for key, text in bot_resp.items():
        if key in FAQ_EXCLUDE_BOTS:
            continue
        t = faq_norm(text)
        if not t:
            continue
        best_id, best_r = None, 0.0
        for fid, ans in faq_answers:
            r = difflib.SequenceMatcher(None, ans, t).ratio()
            if r > best_r:
                best_id, best_r = fid, r
        if best_r >= FAQ_MATCH_TH:
            fired_bots.append(BOT_LABEL.get(key, key))
            fired_ids.append(best_id)
    return fired_bots, sorted(set(fired_ids))


async def main():
    faqs = json.loads(FAQ_JSON.read_text(encoding="utf-8"))
    faq_answers = [(f["id"], faq_norm(f["answer"])) for f in faqs if f.get("answer")]

    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        """
        SELECT r.id, r.week, r.group_id, r.submitter, r.rating, r.risk,
               r.question, r.feedback_text, r.bot_responses, r.raw,
               COALESCE(g.category, r.category) AS category,
               COALESCE(g.risk, r.risk)        AS group_risk
        FROM redteam_responses r
        LEFT JOIN redteam_question_groups g ON g.id = r.group_id
        ORDER BY r.week, r.id
        """
    )
    await conn.close()

    records = []
    for row in rows:
        d = dict(row)
        bot_resp = d["bot_responses"]
        raw = d["raw"]
        # asyncpg는 JSON 컬럼을 str로 줄 수 있어 안전 파싱
        if isinstance(bot_resp, str):
            bot_resp = json.loads(bot_resp) if bot_resp else {}
        if isinstance(raw, str):
            raw = json.loads(raw) if raw else {}
        bot_resp = bot_resp or {}
        raw = raw or {}

        submitter = clean(d["submitter"])
        submitter = SUBMITTER_FIX.get(submitter, submitter) or "(미상)"

        etc = clean(raw.get("기타"))
        if etc in ("없다", "없음", "x", "X", "-", "."):
            etc = ""
        fb_text = clean(d["feedback_text"])
        fb_full = "\n".join(p for p in [fb_text, (f"[기타] {etc}" if etc else "")] if p).strip()

        bot_labels = [BOT_LABEL.get(k, k) for k in bot_resp.keys()]
        faq_bots, faq_ids = detect_faq(bot_resp, faq_answers)

        records.append({
            "id": d["id"],
            "week": d["week"],
            "group_id": d["group_id"],
            "submitter": submitter,
            "category": clean(d["category"]) or "(미분류)",
            "rating": d["rating"],
            "risk": clean(d["risk"]) or clean(d["group_risk"]) or None,
            "bots": bot_labels,
            "question": clean(d["question"]),
            "fb_full": fb_full,
            "has_feedback": bool(fb_full),
            "faq_fired": bool(faq_bots),
            "faq_bots": faq_bots,
            "faq_ids": faq_ids,
        })

    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    by_week = {}
    for r in records:
        by_week[r["week"]] = by_week.get(r["week"], 0) + 1
    n_fb = sum(1 for r in records if r["has_feedback"])
    n_faq = sum(1 for r in records if r["faq_fired"])
    faq_by_week = {}
    for r in records:
        if r["faq_fired"]:
            faq_by_week[r["week"]] = faq_by_week.get(r["week"], 0) + 1
    print(f"추출 {len(records)}건 → {OUT}")
    print(f"주차별: {dict(sorted(by_week.items()))}")
    print(f"피드백 본문 보유(has_feedback): {n_fb}건")
    print(f"FAQ 자동응답 발동: {n_faq}건 (주차별 {dict(sorted(faq_by_week.items()))})")


if __name__ == "__main__":
    asyncio.run(main())
