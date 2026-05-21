# 봇 답변 이후 사용자가 자연스럽게 이어 물을 만한 후속 질문 3개를 빠른 LLM 으로 생성
"""
truewords-platform 의 suggested_followups 패턴 포팅.
- 메인 답변이 끝난 직후 호출, asyncio.wait_for 로 짧은 timeout
- 실패하면 silent fallback (빈 리스트 반환) → 사용자에겐 followups 가 안 보일 뿐 메인 응답은 그대로 노출
- Provider: Gemini 단일 (truewords와 동일). OpenAI 분기는 비용/한도 분산 의도였으나
  운영에서 5초 timeout 풀히트로 직렬 9.5초가 메인 응답 wall-time 에 그대로 붙어
  단일 provider 로 통일.
"""

import asyncio
import logging
import re

from app.services.llm.gemini import GeminiService

logger = logging.getLogger(__name__)


# truewords-platform 의 SUGGESTED_FOLLOWUPS_TIMEOUT_SECONDS = 3.0 동일.
# 실측 hot call 0.6~1.5s 범위라 3초면 충분.
FOLLOWUP_TIMEOUT_SEC = 3.0
FOLLOWUP_MODEL = "gemini-3.1-flash-lite"
ANSWER_TRUNCATE = 1200

# 모듈 레벨 싱글톤 — genai.Client 재사용으로 매 요청 핸드셰이크 제거.
_followup_llm = GeminiService(model_name=FOLLOWUP_MODEL)

_PREFIX_PATTERN = re.compile(r'^\s*(?:\d+[.)]|[-*•])\s*')


SUGGESTED_FOLLOWUPS_SYSTEM_PROMPT = (
    "당신은 챗봇 후속 질문 추천기입니다.\n\n"
    "사용자가 챗봇으로부터 답변을 받은 직후, **사용자 본인이 챗봇에게 이어서 물을** 다음 질문\n"
    "3개를 한국어로 작성하세요. 즉 화자는 **사용자**, 청자는 **챗봇** 입니다.\n\n"
    "[관점이 중요합니다]\n"
    "✅ 올바른 예 (사용자 → 챗봇 어투):\n"
    "  - \"축복식 절차 더 자세히 알려줘\"\n"
    "  - \"신청서는 어디서 받아?\"\n"
    "  - \"3일 행사 준비물이 뭐야?\"\n"
    "❌ 잘못된 예 (챗봇이 사용자에게 묻는 어투 — 절대 사용 금지):\n"
    "  - \"어떤 점이 가장 궁금하신가요?\"\n"
    "  - \"더 알고 싶은 부분이 있으신가요?\"\n"
    "  - \"~하시는 데 어려움이 있나요?\"\n\n"
    "[규칙]\n"
    "- 정확히 3줄, 각 줄은 하나의 질문\n"
    "- 어투: 챗봇에게 묻는 식 — \"~알려줘\", \"~뭐야?\", \"~어떻게 해?\" 등\n"
    "- \"~있으신가요?\", \"~궁금하세요?\", \"~필요하세요?\" 같은 존댓말+상대를-향한-질문은 절대 금지\n"
    "- 번호/마커/따옴표/마크다운/부가 설명 일체 없음\n"
    "- 각 질문은 30자 이내, 자연스러운 한국어\n"
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
    """짧은 timeout 안에 Gemini 1회 호출로 후속 질문 최대 3개 생성. 실패 시 빈 리스트."""
    if not query or not answer:
        return []

    prompt = _build_prompt(query, answer)

    try:
        raw = await asyncio.wait_for(
            _followup_llm.generate(
                prompt=prompt,
                system_prompt=SUGGESTED_FOLLOWUPS_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=512,
            ),
            timeout=FOLLOWUP_TIMEOUT_SEC,
        )
        return _parse_followups(raw)
    except asyncio.TimeoutError:
        logger.info("followup Gemini timeout (>%.1fs) — silent", FOLLOWUP_TIMEOUT_SEC)
        return []
    except Exception as e:
        logger.warning("followup Gemini 실패: %s", e)
        return []
