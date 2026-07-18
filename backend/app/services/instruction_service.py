# 봇 지침 생성과 저장하지 않는 실시간 미리보기를 제공한다.

from app.schemas.instruction import (
    InstructionGenerateRequest,
    InstructionPreviewRequest,
    InstructionPreviewResponse,
)


META_PROMPT = (
    "너는 최고의 프롬프트 엔지니어다. 아래 재료를 바탕으로 챗봇에게 지시하는 한국어 "
    "시스템 프롬프트 하나만 작성하라. 2인칭 지시문으로 쓰고, 역할/목표/말투/대상/제약을 "
    "자연스럽게 녹여라. 해야 할 것/하지 말 것은 명시적 규칙으로, 예시는 행동 지침으로 "
    "반영하라. 적절한 안전장치를 포함하라. 마크다운 코드펜스나 서두 설명 없이 최종 "
    "시스템 프롬프트 본문만 출력하라."
)


def compose_fields_to_prompt(req: InstructionGenerateRequest) -> str:
    """입력된 지침 재료를 결정적인 레이블 블록으로 조립한다."""
    lines = []
    if req.role:
        lines.append(f"[역할]\n{req.role}")
    if req.goal:
        lines.append(f"[목표]\n{req.goal}")
    if req.tone:
        lines.append(f"[말투]\n{req.tone}")
    if req.audience:
        lines.append(f"[대상 독자]\n{req.audience}")
    if req.constraints:
        lines.append(f"[제약]\n{req.constraints}")
    if req.dos:
        lines.append("[해야 할 것]\n" + "\n".join(f"- {item}" for item in req.dos))
    if req.donts:
        lines.append("[하지 말 것]\n" + "\n".join(f"- {item}" for item in req.donts))
    if req.examples:
        lines.append(
            "[예시]\n"
            + "\n".join(f"- 입력: {item.input}\n  출력: {item.output}" for item in req.examples)
        )
    return "\n\n".join(lines)


async def generate_instruction(req: InstructionGenerateRequest) -> str:
    """AI로 시스템 프롬프트를 생성하거나 기존 초안을 개선한다."""
    seed = (
        req.draft.strip()
        if req.mode == "improve" and req.draft.strip()
        else compose_fields_to_prompt(req)
    )
    if not seed:
        seed = "(입력 없음) 일반적인 도움을 주는 챗봇의 기본 지침을 작성하라."

    system = META_PROMPT
    if req.mode == "improve":
        system += "\n\n[개선 모드] 아래는 기존 지침이다. 의도를 보존하며 더 명확·구체적으로 다듬어라."

    from app.services.llm.factory import get_llm_service

    text = await get_llm_service(req.llm_model).generate(
        prompt=seed,
        system_prompt=system,
        temperature=0.7,
        max_tokens=2048,
    )
    return text.strip()


async def preview_instruction(req: InstructionPreviewRequest) -> InstructionPreviewResponse:
    """지침을 저장하지 않고 기존 LLM 또는 RAG 경로로 테스트한다."""
    if req.use_rag and req.bot_id:
        from app.services.rag.factory import get_rag_service

        rag = await get_rag_service(req.llm_model).generate_with_rag(
            bot_id=req.bot_id,
            prompt=req.message,
            system_prompt=req.system_prompt,
            model_name=req.llm_model,
        )
        return InstructionPreviewResponse(
            answer=rag.answer,
            citations=rag.citations,
            followups=rag.followups,
        )

    from app.services.llm.factory import get_llm_service

    answer = await get_llm_service(req.llm_model).generate(
        prompt=req.message,
        system_prompt=req.system_prompt,
    )
    return InstructionPreviewResponse(answer=answer)
