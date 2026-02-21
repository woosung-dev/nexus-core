"""
RAG 서비스 추상 인터페이스.
모델 교체(Gemini ↔ OpenAI) 설정에 따라 파일 스토어 관리 및 
메타데이터 기반 검색(응답)을 동일한 구조로 처리하기 위해 설계.
"""

from abc import ABC, abstractmethod

from app.schemas.rag import RAGResponse


class BaseRAGService(ABC):
    """File Search 기반 RAG(Retrieval-Augmented Generation) 추상 클래스"""

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
        file_path: str,
        display_name: str,
    ) -> str:
        """
        Vector Store에 문서를 업로드한다.
        bot_id를 메타데이터로 태깅하여 봇별 문서 검색을 지원.

        Args:
            bot_id: 문서가 속하는 봇 ID
            file_path: 로컬 파일 경로
            display_name: 문서 표시 이름

        Returns:
            업로드된 파일의 식별자 또는 표시 이름
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
