"""
Supabase Storage 구현체.
supabase-py SDK를 사용하여 파일 업로드/삭제/URL 조회를 수행한다.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.storage.base import FileStorageService


class SupabaseFileStorage(FileStorageService):
    """Supabase Storage 기반 파일 저장소"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase Storage 사용 시 SUPABASE_URL, SUPABASE_SERVICE_KEY 환경변수가 필요합니다."
            )

        from supabase import create_client

        self._client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
        self._bucket = settings.SUPABASE_STORAGE_BUCKET

    async def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """파일을 Supabase Storage에 업로드하고 퍼블릭 URL 반환"""
        # 파일명 충돌 방지: UUID + 원본 확장자
        ext = Path(filename).suffix if filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"

        # Supabase Storage 업로드
        self._client.storage.from_(self._bucket).upload(
            path=unique_name,
            file=file_data,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )

        # 퍼블릭 URL 반환
        return self.get_public_url(unique_name)

    async def delete(self, file_path: str) -> bool:
        """Supabase Storage에서 파일 삭제"""
        # file_path에서 오브젝트 키 추출
        key = self._extract_key(file_path)
        try:
            self._client.storage.from_(self._bucket).remove([key])
            return True
        except Exception:
            return False

    async def get_url(self, file_path: str) -> str:
        """파일의 퍼블릭 URL 반환"""
        key = self._extract_key(file_path)
        return self.get_public_url(key)

    def get_public_url(self, key: str) -> str:
        """오브젝트 키로 퍼블릭 URL 생성"""
        result = self._client.storage.from_(self._bucket).get_public_url(key)
        # supabase-py는 문자열 URL을 직접 반환
        return result

    def _extract_key(self, file_path: str) -> str:
        """절대 URL 또는 오브젝트 키에서 스토리지 키만 추출"""
        # 절대 URL인 경우 버킷명 이후 경로를 추출
        bucket_marker = f"/object/public/{self._bucket}/"
        if bucket_marker in file_path:
            return file_path.split(bucket_marker, 1)[1]
        return file_path
