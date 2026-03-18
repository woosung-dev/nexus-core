"""
Supabase Storage 구현체.
supabase-py SDK를 사용하여 파일 업로드/삭제/URL 조회를 수행한다.
"""

import logging
import uuid
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from supabase import create_client

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, ValidationError
from app.services.storage.base import FileStorageService

logger = logging.getLogger(__name__)


class SupabaseFileStorage(FileStorageService):
    """Supabase Storage 기반 파일 저장소"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ConfigurationError(
                "Supabase 설정(SUPABASE_URL, SUPABASE_SERVICE_KEY)이 누락되었습니다. 실서버 환경변수를 확인해주세요."
            )

        self._client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY.get_secret_value(),
        )
        self._bucket = settings.SUPABASE_STORAGE_BUCKET

    async def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """파일을 Supabase Storage에 업로드하고 퍼블릭 URL 반환"""
        # 파일명 충돌 방지: UUID + 원본 확장자
        ext = Path(filename).suffix if filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"

        # supabase-py의 storage.upload는 동기 함수이므로 루프 차단 방지를 위해 run_in_threadpool 사용
        try:
            await run_in_threadpool(
                self._client.storage.from_(self._bucket).upload,
                path=unique_name,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": "false",
                },
            )
        except Exception as e:
            logger.error(f"Supabase 업로드 중 오류 발생: {str(e)}", exc_info=True)
            raise ValidationError(f"이미지 업로드에 실패했습니다: {str(e)}")

        # 퍼블릭 URL 반환
        return self.get_public_url(unique_name)

    async def delete(self, file_path: str) -> bool:
        """Supabase Storage에서 파일 삭제"""
        key = self._extract_key(file_path)
        try:
            await run_in_threadpool(
                self._client.storage.from_(self._bucket).remove,
                [key]
            )
            return True
        except Exception as e:
            logger.warning(f"Supabase 삭제 중 오류 발생: {str(e)}")
            return False

    async def get_url(self, file_path: str) -> str:
        """파일의 퍼블릭 URL 반환"""
        key = self._extract_key(file_path)
        # URL 생성은 단순 문자열 조작이므로 스레드풀 불필요
        return self.get_public_url(key)

    def get_public_url(self, key: str) -> str:
        """오브젝트 키로 퍼블릭 URL 생성"""
        return self._client.storage.from_(self._bucket).get_public_url(key)

    def _extract_key(self, file_path: str) -> str:
        """절대 URL 또는 오브젝트 키에서 키만 추출"""
        bucket_marker = f"/object/public/{self._bucket}/"
        if bucket_marker in file_path:
            return file_path.split(bucket_marker, 1)[1]
        return file_path
