"""
파일 스토리지 서비스 추상 인터페이스.
LocalFileStorage → S3FileStorage로 교체 가능하도록 설계.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class FileStorageService(ABC):
    """파일 저장소 추상 클래스"""

    @abstractmethod
    async def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """
        파일 업로드 후 접근 가능한 URL/경로 반환.

        Args:
            file_data: 파일 바이너리 데이터
            filename: 저장할 파일명
            content_type: MIME 타입

        Returns:
            저장된 파일의 접근 URL/경로
        """
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        파일 삭제.

        Args:
            file_path: 삭제할 파일 경로/키

        Returns:
            삭제 성공 여부
        """
        ...

    @abstractmethod
    async def get_url(self, file_path: str) -> str:
        """
        파일 접근 URL 반환.

        Args:
            file_path: 파일 경로/키

        Returns:
            파일 접근 URL
        """
        ...
