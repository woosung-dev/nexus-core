"""
스토리지 서비스 팩토리.
환경변수 STORAGE_PROVIDER에 따라 적절한 구현체를 반환한다.
FastAPI Depends()로 사용 가능.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import FileStorageService


@lru_cache
def get_storage_service() -> FileStorageService:
    """
    환경변수 STORAGE_PROVIDER에 따라 스토리지 구현체를 반환하는 팩토리.

    Returns:
        FileStorageService 구현체 (싱글톤)

    사용 예시 (FastAPI DI):
        storage: FileStorageService = Depends(get_storage_service)
    """
    provider = get_settings().STORAGE_PROVIDER.lower()

    match provider:
        case "supabase":
            from app.services.storage.supabase import SupabaseFileStorage

            return SupabaseFileStorage()
        case "r2":
            from app.services.storage.r2 import R2FileStorage

            return R2FileStorage()
        case _:
            raise ValueError(
                f"Unknown STORAGE_PROVIDER: '{provider}'. "
                f"지원 값: 'supabase', 'r2'"
            )
