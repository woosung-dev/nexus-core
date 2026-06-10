"""
RAG 서비스 추상 인터페이스.
모델 교체(Gemini ↔ OpenAI) 설정에 따라 파일 스토어 관리 및 
메타데이터 기반 검색(응답)을 동일한 구조로 처리하기 위해 설계.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.schemas.rag import DocumentInfo, RAGResponse

logger = logging.getLogger(__name__)


class BaseRAGService(ABC):
    """File Search 기반 RAG(Retrieval-Augmented Generation) 추상 클래스"""

    async def replace_document(
        self,
        bot_id: int,
        file_data: bytes,
        filename: str,
        display_name: str,
        mime_type: str | None = None,
    ) -> str:
        """
        동일 (display_name, bot_id) 문서를 안전하게 교체한다(append-only 중복 누적 방지).

        라이브 문서 소실을 막기 위해 **"신규 업로드 성공 후에만 구버전 삭제"** 순서를
        강제한다. 업로드가 실패하면 예외가 전파되고 기존 문서는 그대로 보존된다.
        provider 무관하게 추상 메서드(list/upload/delete)만으로 동작하므로
        Gemini·OpenAI 구현체가 공통 상속한다.
        """
        # ① 교체 대상(동일 display_name) 구버전 file_id 를 업로드 전에 수집한다.
        existing = await self.list_documents(bot_id=bot_id)
        old_file_ids = [d.file_id for d in existing if d.display_name == display_name]

        # ② 신규 업로드 먼저. 실패 시 예외 전파 → 아래 삭제로 진입하지 않아 기존 보존.
        result = await self.upload_document(
            bot_id=bot_id,
            file_data=file_data,
            filename=filename,
            display_name=display_name,
            mime_type=mime_type,
        )

        # ③ 업로드 성공 후에만 구버전 purge. 개별 삭제 실패는 치명 아님(중복만 잔존) → 경고.
        for file_id in old_file_ids:
            try:
                await self.delete_document(bot_id=bot_id, file_id=file_id)
            except Exception as e:
                logger.warning(
                    "replace_document: 구버전 삭제 실패 (bot_id=%s, file_id=%s): %s "
                    "— 중복이 남을 수 있어 수동 정리 필요",
                    bot_id,
                    file_id,
                    e,
                )

        logger.info(
            "replace_document 완료: bot_id=%s display_name=%s 구버전 %d건 정리",
            bot_id,
            display_name,
            len(old_file_ids),
        )
        return result

    @abstractmethod
    async def ensure_store(self, bot_id: int | None = None) -> str:
        """
        AI 제공자의 Vector Store(또는 File Search Store)를 생성하거나
        기존 Store의 ID/Resource Name을 반환한다.
        """
        ...

    @abstractmethod
    async def upload_document(
        self,
        bot_id: int,
        file_data: bytes,
        filename: str,
        display_name: str,
        mime_type: str | None = None,
    ) -> str:
        """
        Vector Store에 문서를 업로드한다.
        bot_id를 메타데이터로 태깅하여 봇별 문서 검색을 지원.

        Args:
            bot_id: 문서가 속하는 봇 ID
            file_data: 업로드할 파일의 바이너리 데이터 (bytes)
            filename: 실제 파일명 (확장자 포함, 스토리지/SDK 전달용)
            display_name: 문서 표시 이름
            mime_type: 파일의 마임 타입 (e.g., "application/pdf")

        Returns:
            업로드된 파일의 식별자 또는 표시 이름
        """
        ...

    @abstractmethod
    async def list_documents(self, bot_id: int) -> list[DocumentInfo]:
        """
        특정 봇에 속한 문서 목록을 조회한다.

        Args:
            bot_id: 검색 대상 봇 ID

        Returns:
            해당 봇에 속한 문서 목록
        """
        ...

    @abstractmethod
    async def delete_document(self, bot_id: int, file_id: str) -> None:
        """
        특정 봇의 문서를 삭제한다.

        Args:
            bot_id: 문서가 속한 봇 ID
            file_id: 삭제할 파일의 ID/리소스명
        """
        ...

    @abstractmethod
    async def generate_with_rag(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> RAGResponse:
        """
        RAG 기반 멀티턴 대체(또는 단일) 응답 생성.
        bot_id에 해당하는 문서(메타데이터)만 필터링하여 컨텍스트로 사용한다.

        Args:
            bot_id: 검색 대상 봇 ID
            prompt: 사용자 질문
            system_prompt: 시스템 프롬프트
            model_name: 오버라이드할 모델명 (지정 안 하면 제공자의 기본 모델 사용)
            temperature: 응답 다양성
            max_tokens: 최대 토큰 수

        Returns:
             답변과 인용 정보가 포함된 RAGResponse 객체
        """
        ...

    @abstractmethod
    async def generate_stream_with_rag(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str | dict, None]:
        """
        RAG 기반 스트리밍 응답 생성 (SSE용).
        bot_id에 해당하는 문서만 검색하여 컨텍스트로 사용하며,
        텍스트 청크(str)를 순차적으로 yield한다.
        구현에 따라 스트림 종료 후 인용 메타데이터를 dict({"citations": [...]}) 로 1회 yield할 수 있다.

        Args:
            bot_id: 검색 대상 봇 ID
            prompt: 사용자 질문
            system_prompt: 시스템 프롬프트
            model_name: 사용할 모델
            temperature: 응답 다양성
            max_tokens: 최대 토큰 수

        Yields:
            텍스트 청크 (str)
        """
        ...

