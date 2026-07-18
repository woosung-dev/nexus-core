# 재질문(clarify) 게이트 — 애매한 질문을 선택형 명확화 질문으로 되묻는 경량 분류 서비스
import asyncio
import logging
import re

from pydantic import BaseModel
from google.genai import types

from app.services.llm.gemini import _get_genai_client

logger = logging.getLogger(__name__)

CLARIFY_MODEL = "gemini-3.1-flash-lite"
CLARIFY_TIMEOUT_SEC = 4.0
CLARIFY_MAX_ITEMS = 3
CLARIFY_MIN_CHARS = 8
CLARIFY_INTRO = "정확히 안내드리기 위해 몇 가지만 확인할게요."

# 인사/감사/단답 등 되묻을 필요가 없는 메시지 사전 필터
_SKIP_RE = re.compile(r"^(안녕|반가|고마워|고맙|감사|ㅎㅇ|hi|hello|hey|ok|okay|넵|네|응|아니|예|yes|no)\b", re.I)


class _ClarifyItem(BaseModel):
    question: str
    options: list[str] = []


class ClarifyDecision(BaseModel):
    ambiguous: bool
    clarifications: list[_ClarifyItem] = []
    reason: str = ""


def should_consider_clarify(message: str) -> bool:
    """되묻기 후보인지 싼 사전 필터 — 너무 짧거나 인사/단답이면 제외."""
    m = (message or "").strip()
    if len(m) < CLARIFY_MIN_CHARS:
        return False
    if _SKIP_RE.match(m):
        return False
    return True


_META = (
    "너는 사용자의 질문이 우리 도메인 지식(RAG)으로 명확히 답변 가능한지 판단하는 분류기다. "
    "질문이 애매해서 답이 크게 달라질 때만 ambiguous=true로 하고, 사용자에게 물어볼 1~3개의 "
    "명확화 질문(clarifications)을 만들어라. 각 질문에는 사용자가 고르기 쉬운 2~5개의 구체적 "
    "선택지(options)를 제공하라. 조금이라도 그냥 답할 수 있으면 ambiguous=false로 하라(되묻기를 "
    "최소화). 인사/감사/잡담은 절대 되묻지 마라. 질문과 선택지는 자연스러운 한국어 존댓말로 작성하라."
)


async def run_clarify_gate(message: str, bot, domain_context: str = "") -> ClarifyDecision | None:
    """애매함을 분류해 명확화 질문을 생성한다. 실패/타임아웃/파싱실패 시 None(정상 답변으로 폴백)."""
    try:
        client = _get_genai_client()
        system = _META
        if domain_context:
            system += "\n\n[도메인 용어 정의]\n" + domain_context
        if getattr(bot, "system_prompt", ""):
            system += "\n\n[봇 지침 요약]\n" + (bot.system_prompt or "")[:800]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=ClarifyDecision,
        )
        response = await asyncio.wait_for(
            client.aio.models.generate_content(model=CLARIFY_MODEL, contents=message, config=config),
            timeout=CLARIFY_TIMEOUT_SEC,
        )
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ClarifyDecision):
            return parsed
        text = getattr(response, "text", None)
        if text:
            return ClarifyDecision.model_validate_json(text)
        return None
    except Exception as e:
        logger.warning("clarify gate 실패(정상 답변으로 폴백): %s", e)
        return None
