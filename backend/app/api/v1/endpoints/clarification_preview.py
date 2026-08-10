"""비영속 맥락 보완 UX 프로토타입 API."""

from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, ValidationError
from app.crud import crud_bot
from app.models.user import User
from app.schemas.clarification import (
    ClarificationAnswerRequest,
    ClarificationAnswerResponse,
    ClarificationPreviewRequest,
    ClarificationPreviewResponse,
)
from app.services.chat_service import _effective_retrieval_mode
from app.services.clarification_service import (
    fixture_decision,
    live_decision,
    retrieval_query_from_summary,
)
from app.services.ops_facts_service import (
    apply_term_rules,
    apply_term_rules_to_citations,
    load_runtime_facts,
    term_rules,
)
from app.services.rag.factory import get_rag_service
from app.services.strict_mode import STRICT_EVIDENCE_MESSAGE, has_direct_citation
from app.services.wiki.service import answer_with_wiki

router = APIRouter(prefix="/clarification-preview", tags=["맥락 보완 프로토타입"])
_optional_bearer = HTTPBearer(auto_error=False)
PROTOTYPE_TEST_BOT_ID = 0
_prototype_test_bot = SimpleNamespace(
    id=PROTOTYPE_TEST_BOT_ID,
    name="맥락 보완 UX 테스트 봇",
    system_prompt="예약 기능 요청의 누락된 맥락을 한국어 선택형 질문으로 확인한다.",
    llm_model="gemini-3.5-flash-lite",
    clarify_enabled=True,
)


def _dev_auth_bypass_enabled() -> bool:
    settings = get_settings()
    return (
        settings.CLARIFICATION_PROTOTYPE_ENABLED
        and settings.CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS
    )


async def _get_prototype_bot(session: AsyncSession, bot_id: int):
    """마이그레이션 전 테스트 DB는 필요한 봇 컬럼만 읽어 프로토타입에 전달한다."""
    if not getattr(get_settings(), "CLARIFICATION_PROTOTYPE_LEGACY_BOT_SCHEMA", False):
        return await crud_bot.get_active_bot(session, bot_id)

    row = (
        await session.execute(
            text(
                "SELECT id, name, system_prompt, llm_model, use_rag, is_active, "
                "evidence_policy_mode FROM bots WHERE id = :bot_id AND is_active = true"
            ),
            {"bot_id": bot_id},
        )
    ).mappings().first()
    return SimpleNamespace(**dict(row)) if row else None


async def get_preview_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """로컬 프로토타입에서만 익명을 허용하고, 그 밖에는 표준 인증을 유지한다."""
    if _dev_auth_bypass_enabled():
        return None
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
        )
    return await get_current_user(credentials, session)


@router.post("", response_model=ClarificationPreviewResponse)
async def preview_clarification(
    request: ClarificationPreviewRequest,
    _current_user: User | None = Depends(get_preview_user),
    session: AsyncSession = Depends(get_session),
) -> ClarificationPreviewResponse:
    """선택형 UX 검증용 판정. Message/ChatSession에는 어떤 데이터도 저장하지 않는다."""
    if not get_settings().CLARIFICATION_PROTOTYPE_ENABLED:
        raise ValidationError("맥락 보완 프로토타입이 활성화되어 있지 않습니다.")

    if _dev_auth_bypass_enabled() and request.bot_id == PROTOTYPE_TEST_BOT_ID:
        if request.mode == "fixture":
            return fixture_decision(request.message, request.answers, request.round)
        return await live_decision(
            request.message,
            request.answers,
            request.round,
            _prototype_test_bot,
            policy_rule_id=request.policy_rule_id,
            policy_context=request.policy_context,
        )

    bot = await _get_prototype_bot(session, request.bot_id)
    if not bot:
        raise BotNotFoundError()

    if request.mode == "fixture":
        return fixture_decision(request.message, request.answers, request.round)

    if (
        not getattr(bot, "clarify_enabled", False)
        and not getattr(get_settings(), "CLARIFICATION_PROTOTYPE_ALLOW_LIVE_UNPILOTED", False)
    ):
        raise ValidationError("이 봇은 맥락 보완 파일럿이 활성화되어 있지 않습니다.")

    return await live_decision(
        request.message,
        request.answers,
        request.round,
        bot,
        policy_rule_id=request.policy_rule_id,
        policy_context=request.policy_context,
    )


@router.post("/answer", response_model=ClarificationAnswerResponse)
async def preview_rag_answer(
    request: ClarificationAnswerRequest,
    _current_user: User | None = Depends(get_preview_user),
    session: AsyncSession = Depends(get_session),
) -> ClarificationAnswerResponse:
    """확정된 요약을 봇의 RAG에 전달한다. ChatSession/Message는 만들지 않는다."""
    if not get_settings().CLARIFICATION_PROTOTYPE_ENABLED:
        raise ValidationError("맥락 보완 프로토타입이 활성화되어 있지 않습니다.")
    if request.bot_id == PROTOTYPE_TEST_BOT_ID:
        raise ValidationError("RAG 답변은 관리자에서 만든 테스트 봇으로 확인해 주세요.")

    bot = await _get_prototype_bot(session, request.bot_id)
    if not bot:
        raise BotNotFoundError()
    if not bot.use_rag:
        raise ValidationError("이 봇의 문서 답변이 비활성화되어 있습니다.")

    # 되물은 뒤 답변이 진짜 병목이다(§8). 셋을 지킨다.
    #  ① 검색 질의와 생성 컨텍스트를 가른다 — 「[요청 요약]」 불릿 덩어리를 그대로
    #     검색어로 넣으면 형식어가 질의에 섞인다.
    #  ② 라운드0과 같은 retrieval_mode 를 탄다 — file_search 로 하드코딩하지 않는다.
    #  ③ strict 게이트와 표기 치환을 우회하지 않는다.
    query = retrieval_query_from_summary(request.message)
    if _effective_retrieval_mode(bot) == "lexical":
        rag_response, _retrieved = await answer_with_wiki(
            bot_id=bot.id,
            question=query,
            system_prompt=bot.system_prompt,
            model_name=bot.llm_model,
            context_mode="raw_budget",
        )
    else:
        rag_response = await get_rag_service(provider=bot.llm_model).generate_with_rag(
            bot_id=bot.id,
            prompt=query,
            system_prompt=bot.system_prompt,
            model_name=bot.llm_model,
        )

    if getattr(bot, "evidence_policy_mode", "legacy") == "strict" and not has_direct_citation(
        rag_response.citations
    ):
        rag_response.answer = STRICT_EVIDENCE_MESSAGE
        rag_response.citations = []
        rag_response.followups = []

    ops_term_rules = term_rules(await load_runtime_facts(session, bot, query))
    if ops_term_rules:
        rag_response.answer = apply_term_rules(rag_response.answer, ops_term_rules)
        apply_term_rules_to_citations(rag_response.citations, ops_term_rules)

    return ClarificationAnswerResponse(
        content=rag_response.answer,
        citations=rag_response.citations,
        followups=rag_response.followups,
    )
