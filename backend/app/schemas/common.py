from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class ErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=False, description="요청 성공 여부 (에러이므로 항상 False)")
    error_code: str = Field(..., description="에러 식별 코드 (예: RESOURCE_NOT_FOUND)")
    message: str = Field(..., description="사용자/클라이언트가 읽을 수 있는 에러 메시지")
    details: Optional[Any] = Field(default=None, description="추가 에러 상세 정보 (옵션)")
