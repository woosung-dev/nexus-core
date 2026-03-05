from typing import Any, Optional
from fastapi import status

class NexusException(Exception):
    """
    Nexus Core 시스템에서 발생하는 모든 커스텀 예외의 최상위 클래스
    프론트엔드로 일관된 에러 포맷을 내려주기 위해 사용됩니다.
    """
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class NotFoundError(NexusException):
    """기본 404 Not Found 에러"""
    def __init__(self, message: str = "해당 리소스를 찾을 수 없습니다.", details: Optional[Any] = None):
        super().__init__(
            error_code="RESOURCE_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )

class BotNotFoundError(NotFoundError):
    """봇을 찾을 수 없을 때 발생하는 에러"""
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="해당 봇을 찾을 수 없습니다.",
            details=details,
        )

class ValidationError(NexusException):
    """기본 400 Bad Request 검증 에러"""
    def __init__(self, message: str = "잘못된 요청입니다.", details: Optional[Any] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )

class AuthenticationError(NexusException):
    """기본 401 Unauthorized 에러"""
    def __init__(self, message: str = "인증되지 않은 사용자입니다.", details: Optional[Any] = None):
        super().__init__(
            error_code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )

# ==========================================
# 향후 새로운 도메인(Chat, RAG 등)에 대한 에러 클래스들도 
# 이 파일에 계속 추가하시면 됩니다.
# ==========================================
