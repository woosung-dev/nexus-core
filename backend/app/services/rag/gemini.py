"""
Gemini File Search API 기반 RAG 서비스.

하나의 공유 Store에 메타데이터(bot_id)로 봇별 문서를 구분한다.
벡터 DB 없이 Google 관리형 RAG를 구현.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.rag import DocumentInfo, RAGCitation, RAGResponse
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
            stores = await self._client.aio.file_search_stores.list()
            async for store in stores:
                if store.display_name == self._store_name:
                    self._store_resource_name = store.name
                    logger.info(f"기존 Store 발견: {store.name}")
                    return self._store_resource_name
        except Exception as e:
            logger.warning(f"Store 목록 조회 실패: {e}")

        # 새 Store 생성
        store = await self._client.aio.file_search_stores.create(
            config={"display_name": self._store_name},
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

        try:
            await self._client.aio.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=store_name,
                config={
                    "display_name": display_name,
                    "custom_metadata": [
                        {"key": "bot_id", "numeric_value": bot_id},
                    ],
                },
            )

            logger.info(
                f"Gemini 문서 업로드 완료: {display_name} (bot_id={bot_id}). "
                f"인덱싱은 Gemini 서버에서 백그라운드로 처리됩니다."
            )
        except Exception as e:
            logger.error(f"Gemini 문서 업로드 실패: {display_name} (bot_id={bot_id}). Error: {e}")
            raise

        return display_name

    async def list_documents(self, bot_id: int) -> list[DocumentInfo]:
        """
        특정 봇에 속한 문서 목록을 조회한다.
        Store의 전체 문서를 가져온 후 bot_id 메타데이터로 필터링.
        """
        store_name = await self.ensure_store()
        documents: list[DocumentInfo] = []

        try:
            # Store 내 문서 목록 조회
            doc_list = await self._client.aio.file_search_stores.documents.list(
                parent=store_name,
            )

            async for doc in doc_list:
                # 메타데이터에서 bot_id 필터링
                is_target = False
                if hasattr(doc, "custom_metadata") and doc.custom_metadata:
                    for meta in doc.custom_metadata:
                        if meta.key == "bot_id" and meta.numeric_value == bot_id:
                            is_target = True
                            break

                if is_target:
                    # 생성 시간 처리
                    created_at = None
                    if hasattr(doc, "create_time") and doc.create_time:
                        if isinstance(doc.create_time, datetime):
                            created_at = doc.create_time.isoformat()
                        else:
                            created_at = str(doc.create_time)

                    documents.append(
                        DocumentInfo(
                            file_id=(doc.name or "").rsplit("/", 1)[-1],
                            display_name=doc.display_name or "unknown",
                            created_at=created_at,
                            status="completed",
                            size_bytes=getattr(doc, "size_bytes", None),
                        )
                    )

            logger.info(f"Gemini 문서 목록 조회 완료: bot_id={bot_id}, count={len(documents)}")
        except Exception as e:
            logger.error(f"Gemini 문서 목록 조회 실패: {e}")
            raise

        return documents

    async def delete_document(self, bot_id: int, file_id: str) -> None:
        """
        특정 봇의 문서를 Store에서 삭제한다.

        Args:
            bot_id: 문서가 속한 봇 ID (검증용)
            file_id: 삭제할 문서의 짧은 ID (e.g., "2022ver-txt-e9u4ujeowola")
        """
        store_name = await self.ensure_store()
        # 짧은 ID를 전체 리소스 이름으로 복원
        full_doc_name = f"{store_name}/documents/{file_id}"

        try:
            # 문서 소유권 확인 (bot_id 검증)
            doc_list = await self._client.aio.file_search_stores.documents.list(
                parent=store_name,
            )

            found = False
            async for doc in doc_list:
                doc_short_id = (doc.name or "").rsplit("/", 1)[-1]
                if doc_short_id == file_id:
                    # bot_id 메타데이터 검증
                    if hasattr(doc, "custom_metadata") and doc.custom_metadata:
                        for meta in doc.custom_metadata:
                            if meta.key == "bot_id" and meta.numeric_value == bot_id:
                                found = True
                                break
                    break

            if not found:
                raise ValueError(
                    f"해당 봇(bot_id={bot_id})에 속한 문서를 찾을 수 없습니다: {file_id}"
                )

            # 문서 삭제 (force=True: 인덱싱된 콘텐츠 포함 강제 삭제)
            await self._client.aio.file_search_stores.documents.delete(
                name=full_doc_name,
                config={"force": True},
            )
            logger.info(f"Gemini 문서 삭제 완료: bot_id={bot_id}, file_id={file_id}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Gemini 문서 삭제 실패: {e}")
            raise

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

        # generate_content는 이미 async 지원 (aio)
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
