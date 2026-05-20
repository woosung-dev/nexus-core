# 봇 답변 이후 사용자가 자연스럽게 이어 물을 만한 후속 질문 3개를 빠른 LLM 으로 생성
"""
truewords-platform 의 suggested_followups 패턴 포팅.
- 메인 답변 스트리밍이 끝난 직후에 호출, asyncio.wait_for 로 짧은 timeout
- 실패하면 silent fallback (빈 리스트 반환) → 사용자에겐 followups 가 안 보일 뿐 메인 응답은 그대로 노출
"""

import asyncio
import logging
import re

from app.services.llm.gemini import GeminiService

logger = logging.getLogger(__name__)


FOLLOWUP_TIMEOUT_SEC = 5.0
FOLLOWUP_MODEL = "gemini-2.5-flash"
ANSWER_TRUNCATE = 1200

_PREFIX_PATTERN = re.compile(r'^\s*(?:\d+[.)]|[-*•])\s*')


SUGGESTED_FOLLOWUPS_SYSTEM_PROMPT = (
    "당신은 챗봇 후속 질문 추천기입니다.\n\n"
    "방금 사용자가 받은 답변을 바탕으로, 사용자가 자연스럽게 이어서 물어볼 만한\n"
    "후속 질문 3개를 한국어로 제안하세요.\n\n"
    "[규칙]\n"
    "- 정확히 3줄, 각 줄은 하나의 질문\n"
    "- 1) / 2) / 3) 등의 번호 접두사를 붙이지 않습니다\n"
    "- 따옴표, 마크다운, 부가 설명 일체 금지\n"
    "- 각 질문은 30자 이내로 간결하게\n"
    "- 봇의 도메인 안에서만 추천 (탈선 금지)\n"
)


def _build_prompt(query: str, answer: str) -> str:
    truncated = (answer or "")[:ANSWER_TRUNCATE]
    return (
        f"[사용자 질문]\n{query}\n\n"
        f"[방금 받은 답변]\n{truncated}\n\n"
        f"[지시] 위 규칙에 따라 후속 질문 3개만 출력하세요."
    )


def _parse_followups(raw: str) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for line in raw.splitlines():
        cleaned = _PREFIX_PATTERN.sub("", line).strip().strip('"').strip("'")
        if len(cleaned) < 3:
            continue
        out.append(cleaned)
        if len(out) >= 3:
            break
    return out


async def generate_followups(query: str, answer: str) -> list[str]:
    """짧은 timeout 안에 후속 질문 최대 3개를 생성. 실패 시 빈 리스트."""
    if not query or not answer:
        return []

    try:
        llm = GeminiService(model_name=FOLLOWUP_MODEL)
        prompt = _build_prompt(query, answer)

        raw = await asyncio.wait_for(
            llm.generate(
                prompt=prompt,
                system_prompt=SUGGESTED_FOLLOWUPS_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=512,
            ),
            timeout=FOLLOWUP_TIMEOUT_SEC,
        )
        logger.debug("followup raw output:\n%s", raw)
        return _parse_followups(raw)
    except asyncio.TimeoutError:
        logger.info("followup 생성 timeout (%.1fs) — silent fallback", FOLLOWUP_TIMEOUT_SEC)
        return []
    except Exception as e:
        logger.warning("followup 생성 실패: %s", e)
        return []
