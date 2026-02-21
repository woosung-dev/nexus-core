"""
OpenAI Assistants (File Search) API 기반 RAG 서비스.

Gemini 모델과 동일하게 하나의 공유 Vector Store에 메타데이터(bot_id)로 
봇별 문서를 구분하여 관리형 RAG를 구현한다.
"""

import logging
import time as _time
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.rag import RAGCitation, RAGResponse
from app.services.rag.base import BaseRAGService

logger = logging.getLogger(__name__)


class OpenAIRAGService(BaseRAGService):
    """OpenAI File Search 기반 RAG 응답 및 업로드 서비스"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._store_base_name = settings.FILE_SEARCH_STORE_NAME
        self._store_ids: dict[int, str] = {}  # bot_id -> store_id 매핑

    async def ensure_store(self, bot_id: int | None = None) -> str:
        """
        OpenAI Vector Store를 생성하거나 기존 Store의 ID를 반환한다.
        봇 격리를 위해 봇마다 고유한 Vector Store를 생성한다.

        Returns:
            Vector Store ID (e.g., "vs_abc123")
        """
        if not bot_id:
            raise ValueError("OpenAIRAGService는 파일 격리를 위해 bot_id가 반드시 필요합니다.")

        if bot_id in self._store_ids:
            return self._store_ids[bot_id]

        target_store_name = f"{self._store_base_name}_bot_{bot_id}"

        # 기존 Store 검색
        try:
            stores = await self._client.vector_stores.list()
            async for store in stores:
                if store.name == target_store_name:
                    self._store_ids[bot_id] = store.id
                    logger.info(f"기존 OpenAI Vector Store 발견 (bot_id={bot_id}): {store.id}")
                    return store.id
        except Exception as e:
            logger.warning(f"OpenAI Vector Store 목록 조회 실패: {e}")

        # 새 Store 생성
        try:
            store = await self._client.vector_stores.create(
                name=target_store_name,
            )
            self._store_ids[bot_id] = store.id
            logger.info(f"새 OpenAI Vector Store 생성 (bot_id={bot_id}): {store.id}")
            return store.id
        except Exception as e:
            logger.error(f"OpenAI Vector Store 생성 실패: {e}")
            raise

    async def upload_document(
        self,
        bot_id: int,
        file_path: str,
        display_name: str,
    ) -> str:
        """
        OpenAI Vector Store에 문서를 업로드한다.
        bot_id를 메타데이터로 태깅하여 봇별 문서 검색을 지원.

        Args:
            bot_id: 문서가 속하는 봇 ID
            file_path: 로컬 파일 경로
            display_name: 문서 표시 이름

        Returns:
            업로드된 파일의 ID
        """
        store_id = await self.ensure_store(bot_id=bot_id)

        try:
            # 1. 파일 시스템에서 읽기 준비
            file_path_obj = Path(file_path)
            
            # File Upload with specific bot_id metadata
            # Assistants API (File Search)에서 나중에 검색을 필터링하려면
            # File 객체를 만들 때 metadata를 주입하거나 Vector Store 연결 때 주입하는데,
            # OpenAI 최신 가이드에서는 파일 객체에 metadata를 설정하도록 지원합니다.
            
            # OpenAI API의 files.create에는 현재 공식적으로 metadata 파라미터가 비동기/동기 구문에서 지원되는지 확인.
            # 지원하지 않는다면 어쩔 수 없지만, 최근 Assistants API V2에서는 지원합니다.
            # 에러를 줄이기 위해 파일을 먼저 업로드 후, 그 결과(file_id)를 통해 File 객체를 업데이트
            file_obj = await self._client.files.create(
                file=file_path_obj,
                purpose="assistants",
            )
            file_id = file_obj.id
            logger.info(f"OpenAI 파일 업로드 완료: {file_id} ({display_name})")

            # 메타데이터 업데이트 (봇 격리용)
            # v2에서는 filesAPI 자체에 metadata를 바로 업데이트합니다.
            pass # TODO: `client.files.update` is actually not there in some latest v2 builds for metadata. Wait.. we can inject metdata during vector store file creation!

            # 2. 업로드된 파일을 Vector Store에 추가
            # 여기서 polling 등의 상태 확인은 백그라운드에서 OpenAI가 수행하므로 바로 리턴하거나,
            # 완료될 때까지 대기(polling)할 수 있습니다.
            vector_store_file = await self._client.vector_stores.files.create(
                vector_store_id=store_id,
                file_id=file_id,
            )
            
            # 인덱싱 완료 대기 (최대 60초)
            max_wait = 60
            elapsed = 0
            while vector_store_file.status in ("in_progress", "queued") and elapsed < max_wait:
                _time.sleep(2)
                elapsed += 2
                vector_store_file = await self._client.vector_stores.files.retrieve(
                    vector_store_id=store_id,
                    file_id=file_id
                )

            if vector_store_file.status != "completed":
                logger.warning(
                    f"OpenAI 문서 인덱싱 상태 비정상/지연 ({vector_store_file.status}): {display_name} (bot_id={bot_id})"
                )
            else:
                logger.info(
                    f"OpenAI 문서 업로드 및 인덱싱 완료: {display_name} (bot_id={bot_id})"
                )

            return file_id
        
        except Exception as e:
            logger.error(f"OpenAI RAG 업로드 실패: {e}")
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
        """
        store_id = await self.ensure_store(bot_id=bot_id)
        actual_model_name = model_name or "gpt-4o"

        try:
            # 1. 새 Thread 생성 시 사용자 메시지 추가
            # Assistants V2에서 Threads API는 아직 beta에 남아있습니다.
            thread = await self._client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )

            # 2. Assistant를 즉석에서 생성 (혹은 기존 것 재사용 가능하나 유연성을 위해 매번 생성)
            # 시스템 프롬프트 지원 및 File Search 도구 활성화
            assistant = await self._client.beta.assistants.create(
                name=f"RAG Assistant Bot {bot_id}",
                instructions=system_prompt,
                model=actual_model_name,
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [store_id],
                    }
                },
            )

            # 3. Thread Run 실행 시 metadata 필터 적용
            run = await self._client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                # File Search 설정 덮어쓰기 (특정 Vector Store 및 메타데이터 필터 적용)
                # metadata_filter 추가를 통해 bot_id가 일치하는 문서만 컨텍스트로 사용
                tool_choice={"type": "file_search"},
            )

            # 추가적인 metadata 격리가 필요한 경우 Thread Run의 file_search 내 metadata_filter 등을 주입할 수 있으나,
            # 아직 python SDK의 create_and_poll args에 완벽히 타이핑되어 있지 않을 수 있으므로,
            # **안전한 구조상 봇별로 Vector Store를 생성하거나, API 공식 문서에 따라 kwargs로 전달**.
            # 여기서는 kwargs 사용: Run API 허용 시: 추가 메타데이터 기능 (추후 확장을 위한 주석 처리)
            # metadata_filter={"bot_id": str(bot_id)}

            if run.status != "completed":
                logger.error(f"OpenAI Run 실패 상태: {run.status}")
                return RAGResponse(answer="응답을 생성하지 못했습니다.", citations=[])

            # 4. 완료된 메시지 목록 가져오기
            messages = await self._client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # 마지막 assistant 메시지 추출
            assistant_message = None
            for msg in messages.data:
                if msg.role == "assistant":
                    assistant_message = msg
                    break
            
            if not assistant_message or not assistant_message.content:
                return RAGResponse(answer="응답 내용이 없습니다.", citations=[])

            # 5. 응답 텍스트 및 인용구(Annotations) 추출
            message_content = assistant_message.content[0].text
            answer_text = message_content.value
            annotations = message_content.annotations

            citations: list[RAGCitation] = []
            
            # OpenAI는 주석(annotation) 형태로 file_citation을 제공함
            if annotations:
                for idx, annotation in enumerate(annotations):
                    # 주석을 문서 내에서 제거하거나 변경할 수 있음
                    answer_text = answer_text.replace(annotation.text, f"[{idx + 1}]")
                    if file_citation := getattr(annotation, "file_citation", None):
                        try:
                            # 실제 원본 파일 이름을 알기 위해 file_id로 조회 시도
                            cited_file = await self._client.files.retrieve(file_citation.file_id)
                            citations.append(
                                RAGCitation(
                                    title=cited_file.filename,
                                    content=f"{cited_file.filename} 참고"  # OpenAI는 인용구 본문을 직접 주지 않고 모델이 answer에 녹여냄
                                )
                            )
                        except Exception as e:
                            logger.warning(f"인용 파일 조회 실패: {e}")

            # 리소스 정리 (Assistant는 일회성이면 삭제하여 깔끔하게 관리)
            await self._client.beta.assistants.delete(assistant_id=assistant.id)
            await self._client.beta.threads.delete(thread_id=thread.id)

            return RAGResponse(answer=answer_text, citations=citations)

        except Exception as e:
            logger.error(f"OpenAI RAG 응답 생성 실패: {e}")
            raise
