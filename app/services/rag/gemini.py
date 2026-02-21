"""
Gemini File Search API 기반 RAG 서비스.

하나의 공유 Store에 메타데이터(bot_id)로 봇별 문서를 구분한다.
벡터 DB 없이 Google 관리형 RAG를 구현.
"""

import logging
import time as _time
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.rag import RAGCitation, RAGResponse
from app.services.rag.base import BaseRAGService

logger = logging.getLogger(__name__)


class GeminiRAGService(BaseRAGService):
    """Gemini File Search 기반 RAG 응답 및 업로드 서비스"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._store_name = settings.FILE_SEARCH_STORE_NAME
        self._store_resource_name: str | None = None

    async def ensure_store(self, bot_id: int | None = None) -> str:
        """
        File Search Store를 생성하거나 기존 Store를 반환한다.

        Returns:
            Store의 리소스 이름 (e.g., "fileSearchStores/abc123")
        """
        if self._store_resource_name:
            return self._store_resource_name

        # 기존 Store 검색
        try:
            stores = self._client.file_search_stores.list()
            for store in stores:
                if store.display_name == self._store_name:
                    self._store_resource_name = store.name
                    logger.info(f"기존 Store 발견: {store.name}")
                    return self._store_resource_name
        except Exception as e:
            logger.warning(f"Store 목록 조회 실패: {e}")

        # 새 Store 생성
        store = self._client.file_search_stores.create(
            config={"display_name": self._store_name}
        )
        self._store_resource_name = store.name
        logger.info(f"새 Store 생성: {store.name}")
        return self._store_resource_name

    async def upload_document(
        self,
        bot_id: int,
        file_path: str,
        display_name: str,
    ) -> str:
        """
        File Search Store에 문서를 업로드한다.
        bot_id를 메타데이터로 태깅하여 봇별 문서 검색을 지원.

        Args:
            bot_id: 문서가 속하는 봇 ID
            file_path: 로컬 파일 경로
            display_name: 문서 표시 이름

        Returns:
            업로드된 파일의 리소스 이름
        """
        store_name = await self.ensure_store()

        operation = self._client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config={
                "display_name": display_name,
                "custom_metadata": [
                    {"key": "bot_id", "numeric_value": bot_id},
                ],
            },
        )

        # 인덱싱 완료 대기 (최대 60초)
        max_wait = 60
        elapsed = 0
        while not operation.done and elapsed < max_wait:
            _time.sleep(2)
            elapsed += 2
            operation = self._client.operations.get(operation)

        if not operation.done:
            logger.warning(
                f"문서 인덱싱이 아직 진행 중: {display_name} (bot_id={bot_id})"
            )
        else:
            logger.info(
                f"문서 업로드 및 인덱싱 완료: {display_name} (bot_id={bot_id})"
            )

        return display_name

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
        RAG 기반 응답 생성.
        bot_id에 해당하는 문서만 검색하여 컨텍스트로 사용.

        Args:
            bot_id: 검색 대상 봇 ID
            prompt: 사용자 질문
            system_prompt: 시스템 프롬프트
            model_name: 사용할 모델 (기본값 gemini-2.5-flash)
            temperature: 응답 다양성
            max_tokens: 최대 토큰
        """
        # 기본 모델 지정
        actual_model_name = model_name or "gemini-2.5-flash"
        
        store_name = await self.ensure_store()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name],
                        metadata_filter=f"bot_id = {bot_id}",
                    )
                )
            ],
        )

        response = await self._client.aio.models.generate_content(
            model=actual_model_name,
            contents=prompt,
            config=config,
        )

        # 인용 정보 추출
        citations: list[RAGCitation] = []
        try:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if chunk.retrieved_context:
                        citations.append(
                            RAGCitation(
                                title=chunk.retrieved_context.title,
                                content=(
                                    chunk.retrieved_context.text[:300]
                                    if chunk.retrieved_context.text
                                    else None
                                ),
                            )
                        )
        except (AttributeError, IndexError) as e:
            logger.debug(f"인용 정보 추출 실패 (정상 케이스일 수 있음): {e}")

        return RAGResponse(
            answer=response.text or "",
            citations=citations,
        )
