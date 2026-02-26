"""
로컬 파일 시스템 스토리지 구현.
기본 구현체로 ./uploads/ 디렉토리에 파일을 저장한다.
"""

import uuid
from pathlib import Path

import aiofiles

from app.core.config import get_settings
from app.services.storage.base import FileStorageService


class LocalFileStorage(FileStorageService):
    """로컬 파일 시스템 기반 스토리지"""

    def __init__(self) -> None:
        self._upload_dir = Path(get_settings().UPLOAD_DIR)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """파일을 로컬 디스크에 저장하고 상대 경로 반환"""
        # 파일명은 UUID + 확장자만 사용 (한글 등 비ASCII 문자로 인한 인코딩 오류 방지)
        ext = Path(filename).suffix if filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = self._upload_dir / unique_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)

        return str(file_path)

    async def delete(self, file_path: str) -> bool:
        """로컬 파일 삭제"""
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False

    async def get_url(self, file_path: str) -> str:
        """로컬 파일의 접근 경로 반환 (정적 파일 서빙 URL)"""
        return f"/static/uploads/{Path(file_path).name}"
