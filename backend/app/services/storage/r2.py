"""
Cloudflare R2 스토리지 구현체.
S3 호환 API를 통해 boto3로 연동한다.
"""

import logging
import uuid
from pathlib import Path

import boto3
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, ValidationError
from app.services.storage.base import FileStorageService

logger = logging.getLogger(__name__)


class R2FileStorage(FileStorageService):
    """Cloudflare R2 기반 파일 저장소 (S3 호환)"""

    def __init__(self) -> None:
        settings = get_settings()
        if not all([
            settings.R2_ACCOUNT_ID,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
            settings.R2_PUBLIC_URL,
        ]):
            raise ConfigurationError(
                "R2 Storage 설정이 누락되었습니다. R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL 환경변수를 확인해주세요."
            )

        self._bucket = settings.R2_BUCKET_NAME
        self._public_url = settings.R2_PUBLIC_URL.rstrip("/")

        # S3 호환 클라이언트 생성 (R2 엔드포인트 사용)
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
            region_name="auto",
        )

    async def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """파일을 R2에 업로드하고 퍼블릭 URL 반환"""
        # 파일명 충돌 방지: UUID + 원본 확장자
        ext = Path(filename).suffix if filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"

        # boto3는 동기이므로 I/O 차단 방지를 위해 run_in_threadpool 사용
        try:
            await run_in_threadpool(
                self._client.put_object,
                Bucket=self._bucket,
                Key=unique_name,
                Body=file_data,
                ContentType=content_type,
            )
        except Exception as e:
            logger.error(f"R2 업로드 중 오류 발생: {str(e)}", exc_info=True)
            raise ValidationError(f"이미지 업로드에 실패했습니다: {str(e)}")

        # 퍼블릭 URL 반환
        return f"{self._public_url}/{unique_name}"

    async def delete(self, file_path: str) -> bool:
        """R2에서 파일 삭제"""
        key = self._extract_key(file_path)
        try:
            await run_in_threadpool(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except Exception as e:
            logger.warning(f"R2 삭제 중 오류 발생: {str(e)}")
            return False

    async def get_url(self, file_path: str) -> str:
        """파일의 퍼블릭 URL 반환"""
        key = self._extract_key(file_path)
        return f"{self._public_url}/{key}"

    def _extract_key(self, file_path: str) -> str:
        """절대 URL 또는 오브젝트 키에서 키만 추출"""
        if file_path.startswith(self._public_url):
            return file_path[len(self._public_url):].lstrip("/")
        return file_path
