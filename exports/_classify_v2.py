# Neon 실서버 봇3종(통합/원리/정밀) 대화를 Gemini 로 분류해 봇별 필터 리포트용 레코드 JSON 생성
import asyncio
import datetime as dt
import json
import os
import re
from zoneinfo import ZoneInfo

import asyncpg
from google import genai

URL = "postgresql://neondb_owner:npg_l8Xgu2JIxnVA@ep-icy-wave-amjjo0k9-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
OUT = f"{BASE}/_chat_v2_records.json"
KST = ZoneInfo("Asia/Seoul")

START = "2026-05-31"   # 포함
END = "2026-06-09"     # 미포함 (06-08 까지)
EXCLUDE_EMAIL = "woosung@test.com"
BOT_IDS = [3, 4, 5]
BOT_SHORT = {
    "축복 상담 AI (통합)": "통합",
    "축복 상담 AI (원리)": "원리",
    "축복 상담 AI (정밀)": "정밀",
}

CATEGORIES = [
    "축복 절차·준비", "자격·연령 조건", "순결·과거 고민", "매칭·교류(B4U)",
    "상담·연락처 안내", "축복 정리·재축복", "교육·수련 이수", "의식·예식",
    "신앙·교리·가치", "가정출발·혼인생활", "부모-자녀 소통", "기타·인사",
]
PERSPECTIVES = [
    "규정·절차 정보제공", "전문가 연결 권유", "공감·정서 위로",
    "신앙적 격려·가치부여", "한계·면책 고지",
]

PROMPT = """너는 '가정연합 축복 상담 챗봇'의 대화 로그를 분석하는 분류기다.
아래 Q&A 목록 각각에 대해 다음을 판정해라.

[질문 카테고리] — 아래 중 정확히 하나:
{cats}

[답변 관점] — 아래 중 해당되는 것 모두(복수 가능). 답변이 빈 경우 빈 배열:
{pers}

출력은 반드시 JSON 배열. 각 원소는 {{"i": 번호, "category": "...", "perspectives": ["...", ...]}}.
설명/마크다운 없이 JSON 만.

Q&A 목록:
{items}
"""


def kst_date(ts):
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(KST).date().isoformat()


async def fetch_pairs():
    conn = await asyncpg.connect(URL)
    try:
        rows = await conn.fetch(
            """
            SELECT m.session_id, m.id, m.role::text AS role, m.content, m.feedback,
                   b.name AS bot, u.email AS email, m.created_at AS msg_created
            FROM messages m
            JOIN chat_sessions s ON s.id = m.session_id
            JOIN users u ON u.id = s.user_id
            JOIN bots b ON b.id = s.bot_id
            WHERE u.email <> $1
              AND s.bot_id = ANY($2::int[])
              AND s.created_at >= $3 AND s.created_at < $4
            ORDER BY m.session_id, m.id
            """,
            EXCLUDE_EMAIL, BOT_IDS,
            dt.date.fromisoformat(START), dt.date.fromisoformat(END),
        )
        by_sess = {}
        meta = {}
        for r in rows:
            by_sess.setdefault(r["session_id"], []).append(r)
            meta[r["session_id"]] = (r["bot"], r["email"])
        pairs = []
        for sid, msgs in by_sess.items():
            bot, email = meta[sid]
            for idx, m in enumerate(msgs):
                if m["role"] in ("USER", "user"):
                    ans = ""
                    fb = None
                    for nxt in msgs[idx + 1:]:
                        if nxt["role"] in ("ASSISTANT", "assistant"):
                            ans = nxt["content"] or ""
                            fb = nxt["feedback"]
                            break
                        if nxt["role"] in ("USER", "user"):
                            break
                    pairs.append({
                        "sid": sid,
                        "bot": BOT_SHORT.get(bot, bot or "기타"),
                        "user": (email or "").split("@")[0],
                        "date": kst_date(m["msg_created"]),
                        "q": (m["content"] or "").strip(),
                        "a": ans.strip(),
                        "fb": fb,
                    })
        return pairs
    finally:
        await conn.close()


def classify(client, batch, base_idx):
    items = []
    for j, p in enumerate(batch):
        q = p["q"][:300].replace("\n", " ")
        a = p["a"][:400].replace("\n", " ")
        items.append(f'#{base_idx + j} 질문: {q}\n     답변(요약): {a}')
    prompt = PROMPT.format(
        cats="\n".join(f"- {c}" for c in CATEGORIES),
        pers="\n".join(f"- {c}" for c in PERSPECTIVES),
        items="\n".join(items),
    )
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    txt = resp.text.strip()
    txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.MULTILINE).strip()
    return json.loads(txt)


async def main():
    pairs = await fetch_pairs()
    print(f"Q&A 쌍: {len(pairs)}개")
    client = genai.Client(api_key=GEMINI_KEY)

    results = {}
    BATCH = 20
    for i in range(0, len(pairs), BATCH):
        batch = pairs[i:i + BATCH]
        for attempt in range(3):
            try:
                arr = classify(client, batch, i)
                for o in arr:
                    results[int(o["i"])] = o
                print(f"  배치 {i}-{i+len(batch)-1} 완료 ({len(arr)}건)")
                break
            except Exception as e:
                print(f"  배치 {i} 재시도 {attempt+1}: {type(e).__name__} {str(e)[:80]}")
                await asyncio.sleep(3)

    records = []
    for idx, p in enumerate(pairs):
        c = results.get(idx, {})
        records.append({
            "bot": p["bot"], "user": p["user"], "sid": p["sid"], "date": p["date"],
            "q": p["q"], "fb": p["fb"],
            "category": c.get("category", "미분류"),
            "perspectives": c.get("perspectives", []),
        })

    users = sorted({r["user"] for r in records})
    out = {
        "window": [START, "2026-06-08"],
        "bots": ["통합", "원리", "정밀"],
        "categories": CATEGORIES,
        "perspectives": PERSPECTIVES,
        "users": users,
        "records": records,
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"저장: {OUT} ({len(records)}건, 분류성공 {len(results)}건, 사용자 {len(users)}명)")
    from collections import Counter
    print("봇별 질문수:", dict(Counter(r["bot"] for r in records)))
    print("봇별 세션수:", {b: len({r["sid"] for r in records if r["bot"] == b}) for b in ["통합", "원리", "정밀"]})


asyncio.run(main())
