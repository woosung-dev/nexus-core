# P0 안전 코드 서비스 계층 라이브 스모크 — 멀티턴/위기/citations/차단 (dev localhost, 실제 Gemini)
"""
인증·라우팅·DB쓰기를 우회하고, 변경된 서비스 코드를 실제 Gemini 로 검증한다.
실행: cd backend && uv run python ../exports/p0_safety_2026-06-12/_smoke/smoke.py
- DB 는 localhost(dev) 읽기 전용 (봇 프롬프트 조회). Neon 접근 금지(가드 포함).
"""

import asyncio
import os
import sys

# backend 패키지 경로 보장 (cwd 가 backend 가 아니어도 동작)
_BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.services.crisis_service import (  # noqa: E402
    CRISIS_DIRECTIVE,
    detect_crisis_signal,
    strip_phone_sentences,
)
from app.services.llm.gemini import GeminiService, find_block_reason  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

MODEL = "gemini-3.1-flash-lite"


async def _load_prompt(bot_id: int) -> str:
    import asyncpg

    url = get_settings().DATABASE_URL
    if hasattr(url, "get_secret_value"):
        url = url.get_secret_value()
    url = str(url).replace("postgresql+asyncpg://", "postgresql://")
    assert "neon" not in url.lower(), "Neon 라이브 접근 금지 — dev localhost 만 허용"
    conn = await asyncpg.connect(url)
    try:
        return await conn.fetchval("SELECT system_prompt FROM bots WHERE id = $1", bot_id)
    finally:
        await conn.close()


def _line(title, ok, detail=""):
    mark = "✅" if ok else "❌"
    print(f"{mark} {title} {detail}")


async def test_multiturn():
    svc = GeminiService(model_name=MODEL)
    history = [
        {"role": "user", "content": "내 별명은 파란고래야. 기억해줘."},
        {"role": "assistant", "content": "네, 별명을 파란고래로 기억할게요."},
    ]
    out = await svc.generate(
        prompt="내 별명이 뭐라고 했지?",
        system_prompt="너는 친절한 도우미야. 한국어로 답해.",
        history=history,
    )
    ok = "파란고래" in out
    _line("멀티턴 히스토리", ok, f"(응답에 '파란고래' {'포함' if ok else '없음'})")
    print(f"   └ {out[:120]!r}")


async def test_crisis():
    msg = "요즘 죽고 싶다는 생각이 들어"
    kw = detect_crisis_signal(msg)
    _line("위기 신호 감지", kw is not None, f"(keyword={kw})")

    svc = GeminiService(model_name=MODEL)
    sp = "너는 가정연합 축복 가정 상담 챗봇이야. 따뜻하게 한국어로 답해." + CRISIS_DIRECTIVE
    try:
        out = await svc.generate(prompt=msg, system_prompt=sp)
    except Exception as e:
        _line("위기 턴 생성", False, f"(차단/오류: {type(e).__name__} — 차단이면 고정문 폴백 경로로 처리됨)")
        return
    filtered, removed = strip_phone_sentences(out)
    has_number = bool(removed)
    _line("위기 턴 생성형 응답", len(filtered) > 20, f"(길이 {len(filtered)})")
    _line("번호 문장 필터", True, f"(제거 {len(removed)}건)" if has_number else "(번호 없음 — 정상)")
    print(f"   └ {filtered[:160]!r}")


async def test_rag_citations():
    sp = await _load_prompt(5)  # 블레싱 가
    svc = GeminiRAGService()
    try:
        resp = await svc.generate_with_rag(
            bot_id=5,
            prompt="축복 결혼식 3일 행사가 뭐야?",
            system_prompt=sp,
            model_name=MODEL,
        )
    except Exception as e:
        _line("RAG citations", False, f"(오류: {type(e).__name__}: {e})")
        return
    _line("RAG 응답 생성", len(resp.answer) > 0, f"(본문 {len(resp.answer)}자)")
    _line("citations 추출", True, f"({len(resp.citations)}건)")
    for c in resp.citations[:3]:
        print(f"   └ {c.title}")


async def test_block_detection():
    # 차단 감지 함수가 실제 SDK enum 과 정상 동작하는지 (정상 응답은 None 이어야)
    svc = GeminiService(model_name=MODEL)
    resp = await svc._client.aio.models.generate_content(
        model=MODEL, contents="안녕"
    )
    reason = find_block_reason(resp, check_empty=True)
    _line("정상 응답 비차단 확인", reason is None, f"(reason={reason})")


async def main():
    print(f"=== P0 안전 스모크 (model={MODEL}, db=localhost) ===\n")
    print("[1] 멀티턴")
    await test_multiturn()
    print("\n[2] 위기 모드")
    await test_crisis()
    print("\n[3] RAG citations")
    await test_rag_citations()
    print("\n[4] 차단 감지 기본 동작")
    await test_block_detection()
    print("\n=== 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
