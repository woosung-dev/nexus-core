# 지침 빌더의 AI 생성, 미리보기, 저장 API를 제공한다.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.crud import crud_instruction
from app.schemas.instruction import (
    BotInstructionCreateRequest,
    BotInstructionListResponse,
    BotInstructionResponse,
    BotInstructionUpdateRequest,
    InstructionGenerateRequest,
    InstructionGenerateResponse,
    InstructionPreviewRequest,
    InstructionPreviewResponse,
)
from app.services import instruction_service


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/instructions/generate",
    response_model=InstructionGenerateResponse,
    tags=["Admin - 지침 빌더"],
)
async def generate_instruction(
    request: InstructionGenerateRequest,
) -> InstructionGenerateResponse:
    """AI로 시스템 프롬프트를 생성하거나 개선한다."""
    return InstructionGenerateResponse(
        system_prompt=await instruction_service.generate_instruction(request)
    )


@router.post(
    "/instructions/preview",
    response_model=InstructionPreviewResponse,
    tags=["Admin - 지침 빌더"],
)
async def preview_instruction(
    request: InstructionPreviewRequest,
) -> InstructionPreviewResponse:
    """지침을 저장하지 않고 응답을 미리본다."""
    return await instruction_service.preview_instruction(request)


@router.get(
    "/instructions",
    response_model=BotInstructionListResponse,
    tags=["Admin - 지침 빌더"],
)
async def list_instructions(
    bot_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> BotInstructionListResponse:
    """지침 목록을 조회한다."""
    instructions = await crud_instruction.list_instructions(session, bot_id)
    return BotInstructionListResponse(
        instructions=[BotInstructionResponse.model_validate(item) for item in instructions],
        total=len(instructions),
    )


@router.get(
    "/bots/{bot_id}/instructions",
    response_model=BotInstructionListResponse,
    tags=["Admin - 지침 빌더"],
)
async def list_bot_instructions(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> BotInstructionListResponse:
    """특정 봇의 지침 목록을 조회한다."""
    instructions = await crud_instruction.list_instructions(session, bot_id)
    return BotInstructionListResponse(
        instructions=[BotInstructionResponse.model_validate(item) for item in instructions],
        total=len(instructions),
    )


@router.get(
    "/instructions/{instruction_id}",
    response_model=BotInstructionResponse,
    tags=["Admin - 지침 빌더"],
)
async def get_instruction(
    instruction_id: int,
    session: AsyncSession = Depends(get_session),
) -> BotInstructionResponse:
    """지침 단건을 조회한다."""
    instruction = await crud_instruction.get_instruction(session, instruction_id)
    if not instruction:
        raise HTTPException(status_code=404, detail="지침을 찾을 수 없습니다.")
    return BotInstructionResponse.model_validate(instruction)


@router.post(
    "/instructions",
    response_model=BotInstructionResponse,
    status_code=201,
    tags=["Admin - 지침 빌더"],
)
async def create_instruction(
    request: BotInstructionCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotInstructionResponse:
    """지침을 저장한다."""
    instruction = await crud_instruction.create_instruction(session, request.model_dump())
    return BotInstructionResponse.model_validate(instruction)


@router.put(
    "/instructions/{instruction_id}",
    response_model=BotInstructionResponse,
    tags=["Admin - 지침 빌더"],
)
async def update_instruction(
    instruction_id: int,
    request: BotInstructionUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotInstructionResponse:
    """지침을 부분 수정한다."""
    instruction = await crud_instruction.get_instruction(session, instruction_id)
    if not instruction:
        raise HTTPException(status_code=404, detail="지침을 찾을 수 없습니다.")

    instruction = await crud_instruction.update_instruction(
        session,
        instruction,
        request.model_dump(exclude_unset=True),
    )
    return BotInstructionResponse.model_validate(instruction)


@router.delete(
    "/instructions/{instruction_id}",
    tags=["Admin - 지침 빌더"],
)
async def delete_instruction(
    instruction_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """지침을 삭제한다."""
    instruction = await crud_instruction.get_instruction(session, instruction_id)
    if not instruction:
        raise HTTPException(status_code=404, detail="지침을 찾을 수 없습니다.")

    await crud_instruction.delete_instruction(session, instruction)
    return {"deleted": True}
