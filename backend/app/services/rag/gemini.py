"""
Gemini File Search API 기반 RAG 서비스.

하나의 공유 Store에 메타데이터(bot_id)로 봇별 문서를 구분한다.
벡터 DB 없이 Google 관리형 RAG를 구현.
"""

import hashlib
import io
import logging
import re
import time
from datetime import datetime

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.rag import DocumentInfo, RAGCitation, RAGResponse
from app.services.llm.gemini import (
    SAFETY_BLOCKED_MESSAGE,
    build_gemini_contents,
    is_blocked,
    safe_response_text,
)
from app.services.rag.base import BaseRAGService

logger = logging.getLogger(__name__)


# RAG 응답 1회로 본문과 followup 을 같이 받기 위한 system_prompt suffix.
# tools=[FileSearch] 와 response_schema 가 동시 사용 불가라 텍스트 마커로 분리한다.
# 모델이 포맷을 어겨 파싱이 실패해도 본문은 그대로 노출되고 followups 만 비어 나간다.
_FOLLOWUPS_INSTRUCTION = """

---
[FOLLOWUP_INSTRUCTION]
답변이 끝난 뒤 줄바꿈 두 번 후, 사용자가 챗봇에게 이어서 물을 다음 질문 3개를
정확히 아래 형식으로 첨부하라. 본문에는 절대 노출하지 말고, 형식을 그대로 지켜라.

<followups>
질문1
질문2
질문3
</followups>

규칙:
- 화자는 사용자, 청자는 챗봇. "~알려줘", "~뭐야?", "~어떻게 해?" 등 사용자→챗봇 어투.
- "~궁금하신가요?", "~필요하세요?" 같이 챗봇이 사용자에게 묻는 어투는 절대 금지.
- 각 질문은 30자 이내, 자연스러운 한국어 한 줄.
- 줄 앞에 "1." / "1)" / "-" / "•" / "*" 같은 리스트 마커를 붙이지 말 것.
- **단, "3일 행사", "40일 성별" 처럼 단어 일부인 숫자는 반드시 그대로 보존하라.**
  잘못된 예: "일 행사가 뭐야" / 올바른 예: "3일 행사가 뭐야"
- 따옴표/마크다운 금지.
- 봇 도메인 안에서만 추천 (탈선 금지).
"""


# 본문에서 followups 블록과 RAG citation marker 를 분리하기 위한 정규식.
# 견고화: 여는 태그의 공백/구분자 변형(`< followups >`, `<follow_ups>`, `<follow-ups>`)을 허용하고,
# 닫는 태그가 누락돼도(`</followups>` 없음) 문자열 끝(\Z)까지 흡수해 본문 노출을 막는다.
_FOLLOWUPS_BLOCK_RE = re.compile(
    r"<\s*follow[\s_-]?ups\s*>(.*?)(?:<\s*/\s*follow[\s_-]?ups\s*>|\Z)",
    re.DOTALL | re.IGNORECASE,
)
# 파싱이 실패하거나 부분만 매칭돼도 내부 마커/지시문이 사용자에게 노출되지 않도록 제거하는 안전망.
_FOLLOWUPS_RESIDUE_RE = re.compile(
    r"<\s*/?\s*follow[\s_-]?ups\s*>|\[FOLLOWUP_INSTRUCTION\]",
    re.IGNORECASE,
)
# Gemini file_search grounding 이 본문에 자동 삽입하는 `[1.2, 1.5]` 같은 인용 마커.
# 사용자에겐 의미 불명이라 시각 노이즈로 작용 → 본문에서 제거 (citations 배열은 보존).
_CITATION_MARKER_RE = re.compile(r"\s*\[[\d.,\s]+\]")
# followup 블록 앞쪽의 `---` 같은 구분자 잔여 제거용.
_TRAILING_SEPARATOR_RE = re.compile(r"\n\s*-{3,}\s*$", re.MULTILINE)
# 줄 앞의 list marker 만 잡는 패턴 — 숫자 뒤에 ".)" 같은 구분자가 따라와야 인정.
# "3." / "3)" / "- " / "* " / "• " 는 매칭, "3일 행사" 는 비매칭.
_LIST_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]\s+|[-*•]\s+)")

# search_citations 의 system_instruction 끝에 붙이는 인용 지침.
# 통제실험에서 이 지침을 추가하면 interactions 인용 보고율이 33%→75% 로 상승함을 확인.
_CITATION_INSTRUCTION = (
    "\n\n[인용 지침] 답변에 사용한 모든 사실은 file_search로 검색한 문서에 근거해야 한다. "
    "각 핵심 주장이 어떤 문서에 근거하는지 반드시 file_citation 인용으로 표기하라."
)


def _split_answer_and_followups(raw: str) -> tuple[str, list[str]]:
    """모델 응답에서 <followups> 블록을 떼어 본문/추천 질문으로 분리한다."""
    if not raw:
        return "", []

    followups: list[str] = []
    match = _FOLLOWUPS_BLOCK_RE.search(raw)
    if match:
        block = match.group(1)
        for line in block.splitlines():
            cleaned = line.strip()
            # 코드펜스(``` 또는 ```lang) 줄은 followup 이 아니므로 건너뛴다.
            if cleaned.startswith("```"):
                continue
            cleaned = _LIST_MARKER_RE.sub("", cleaned).strip().strip('"').strip("'").strip("`").strip()
            if len(cleaned) >= 3:
                followups.append(cleaned)
            if len(followups) >= 3:
                break
        # 본문에서 블록 자체와 그 앞 구분자 흔적 제거
        raw = _FOLLOWUPS_BLOCK_RE.sub("", raw)

    # 안전망: 매칭 실패/부분 노출에 대비해 잔여 마커·지시문을 제거(사용자 노출 0건 보장).
    raw = _FOLLOWUPS_RESIDUE_RE.sub("", raw)
    # citation marker 제거 (citations 배열은 그대로 유지되므로 출처 추적은 가능)
    raw = _CITATION_MARKER_RE.sub("", raw)
    # followup 안내 직전에 넣어둔 `---` 잔여 제거
    raw = _TRAILING_SEPARATOR_RE.sub("", raw)

    return raw.strip(), followups


def _citation_from_retrieved_context(ctx) -> RAGCitation:
    """grounding_chunks[].retrieved_context → RAGCitation 로 변환한다.

    page_number·uri 는 Gemini Developer API 에서 지원되는 필드다(SDK docstring 상
    "not supported in **Vertex AI**"). 반대로 document_name·rag_chunk(chunk_id)는
    Vertex 전용이라 이 클라이언트에선 항상 None 이므로 쓰지 않는다.
    """
    return RAGCitation(
        title=ctx.title,
        content=ctx.text[:800] if ctx.text else None,
        uri=ctx.uri,
        page_number=ctx.page_number,
    )


def _dedupe_citations(citations: list[RAGCitation]) -> list[RAGCitation]:
    """같은 청크가 여러 번 인용돼도 목록엔 한 번만 남긴다(첫 등장 순서 보존).

    Gemini Developer API 에는 안정적인 청크 식별자가 없다(chunk_id·document_name 은
    Vertex 전용). 그래서 (제목, 페이지, 본문 앞부분 해시) 복합 키로 근사 dedup 한다.
    top_k=12 인데 한 문서가 여러 청크로 쪼개지거나, interactions 가 같은 근거를 여러 주장에
    반복 인용하면 목록이 수십 건으로 불어나기 때문이다(실측 31건 → 고유 4종).
    """
    seen: set[tuple[str | None, int | None, str]] = set()
    unique: list[RAGCitation] = []
    for c in citations:
        body = (c.content or "").strip()
        key = (c.title, c.page_number, hashlib.sha256(body[:200].encode()).hexdigest())
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


class GeminiRAGService(BaseRAGService):
    """Gemini File Search 기반 RAG 응답 및 업로드 서비스"""

    def __init__(self) -> None:
        # 프로세스 레벨 싱글톤 client 재사용 (메인 LLM/followup과 동일).
        from app.services.llm.gemini import _get_genai_client

        settings = get_settings()
        self._client = _get_genai_client()
        self._store_name = settings.FILE_SEARCH_STORE_NAME
        self._store_resource_name: str | None = None

    async def ensure_store(self, bot_id: int | None = None) -> str:
        """
        File Search Store를 생성하거나 기존 Store를 반환한다.

        Returns:
            Store의 리소스 이름 (e.g., "fileSearchStores/abc123")
        """
        # 캐시 hit — 외부 API 호출 0회.
        if self._store_resource_name:
            logger.debug("ensure_store cache hit")
            return self._store_resource_name

        # 캐시 miss — list + (필요 시) create. 둘 다 외부 API.
        t0 = time.perf_counter()
        # 기존 Store 검색
        try:
            stores = await self._client.aio.file_search_stores.list()
            async for store in stores:
                if store.display_name == self._store_name:
                    self._store_resource_name = store.name
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    logger.info(
                        "ensure_store cache miss (list hit) — store=%s elapsed=%.1fms",
                        store.name,
                        elapsed_ms,
                    )
                    return self._store_resource_name
        except Exception as e:
            logger.warning(f"Store 목록 조회 실패: {e}")

        # 새 Store 생성
        store = await self._client.aio.file_search_stores.create(
            config={"display_name": self._store_name},
        )
        self._store_resource_name = store.name
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "ensure_store cache miss (new store created) — store=%s elapsed=%.1fms",
            store.name,
            elapsed_ms,
        )
        return self._store_resource_name

    async def upload_document(
        self,
        bot_id: int,
        file_data: bytes,
        filename: str,
        display_name: str,
        mime_type: str | None = None,
    ) -> str:
        """
        File Search Store에 문서를 업로드한다.
        bot_id를 메타데이터로 태깅하여 봇별 문서 검색을 지원.

        Args:
            bot_id: 문서가 속하는 봇 ID
            file_data: 업로드할 파일의 바이너리 데이터 (bytes)
            filename: 실제 파일명
            display_name: 문서 표시 이름
            mime_type: 파일의 마임 타입 (e.g., "application/pdf")

        Returns:
            업로드된 파일의 리소스 이름
        """
        store_name = await self.ensure_store()

        # 내용 해시 — 동일 문서 식별/dedup 근거. (display_name, bot_id) 만으로는
        # 같은 이름 다른 버전을 구분 못 하므로 content_sha256 을 메타데이터로 박는다.
        content_hash = hashlib.sha256(file_data).hexdigest()

        try:
            # Gemini SDK는 업로드 시 파일 자체(bytes) 보다는 파일 객체 또는 경로를 권장합니다.
            # 마임타입이 없으면 인덱싱 에러가 발생하므로 config 내에 명시적으로 전달합니다.
            await self._client.aio.file_search_stores.upload_to_file_search_store(
                file=io.BytesIO(file_data),
                file_search_store_name=store_name,
                config={
                    "mime_type": mime_type,
                    "display_name": display_name,
                    "custom_metadata": [
                        {"key": "bot_id", "numeric_value": bot_id},
                        {"key": "content_sha256", "string_value": content_hash},
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
                config={"page_size": 20},  # 최대 페이지 크기로 전체 순회 왕복 횟수 최소화
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
                config={"page_size": 20},  # 최대 페이지 크기로 전체 순회 왕복 횟수 최소화
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
        temperature: float | None = None,
        max_tokens: int = 2048,
        history: list[dict[str, str]] | None = None,
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
            history: 멀티턴 대화 이력 (과거→현재, 현재 질문 미포함)
        """
        # 기본 모델 지정
        actual_model_name = model_name or "gemini-2.5-flash"
        settings = get_settings()
        if temperature is None:
            temperature = settings.RAG_TEMPERATURE

        store_name = await self.ensure_store()

        # 본문 + followups 를 1회 호출에 같이 받기 위해 system_instruction 끝에 지시 첨부.
        # max_output_tokens 도 followup 3줄 분량을 흡수할 정도로 약간 늘린다 (~120 tokens).
        merged_system_instruction = (system_prompt or "") + _FOLLOWUPS_INSTRUCTION

        config = types.GenerateContentConfig(
            system_instruction=merged_system_instruction or None,
            temperature=temperature,
            max_output_tokens=max_tokens + 256,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name],
                        metadata_filter=f"bot_id = {bot_id}",
                        top_k=settings.RAG_TOP_K,
                    )
                )
            ],
        )

        # generate_content는 이미 async 지원 (aio). 외부 API wall-time을 단독 측정한다.
        t_gen = time.perf_counter()
        response = await self._client.aio.models.generate_content(
            model=actual_model_name,
            contents=build_gemini_contents(prompt, history),
            config=config,
        )
        gen_ms = (time.perf_counter() - t_gen) * 1000

        # 세이프티 차단 시 raw 에러 대신 간단한 안내 문구로 처리.
        # (candidates=None 차단 응답이 아래 인용 추출에서 TypeError 로 터지던 H25 직접 수정)
        if is_blocked(response):
            logger.warning("RAG 응답 차단 — bot_id=%s, gen=%.1fms", bot_id, gen_ms)
            return RAGResponse(answer=SAFETY_BLOCKED_MESSAGE, citations=[], followups=[])

        # 인용 정보 추출
        citations: list[RAGCitation] = []
        chunk_count = 0
        try:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                chunk_count = len(grounding.grounding_chunks)
                for chunk in grounding.grounding_chunks:
                    if chunk.retrieved_context:
                        citations.append(
                            _citation_from_retrieved_context(chunk.retrieved_context)
                        )
                citations = _dedupe_citations(citations)
        except (AttributeError, IndexError) as e:
            logger.debug(f"인용 정보 추출 실패 (정상 케이스일 수 있음): {e}")

        # 본문/followups 분리 + citation marker 제거.
        clean_answer, followups = _split_answer_and_followups(safe_response_text(response))

        # 핵심 측정 지점: generate_content 자체 wall-time + retrieval 양 + followup 추출 결과.
        logger.info(
            "gemini RAG generate_content elapsed=%.1fms model=%s bot_id=%s "
            "answer_len=%d grounding_chunks=%d citations=%d followups=%d",
            gen_ms,
            actual_model_name,
            bot_id,
            len(clean_answer),
            chunk_count,
            len(citations),
            len(followups),
        )

        return RAGResponse(
            answer=clean_answer,
            citations=citations,
            followups=followups,
        )

    async def generate_stream_with_rag(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2048,
        history: list[dict[str, str]] | None = None,
    ):
        """
        RAG 기반 스트리밍 응답 생성.
        Gemini generate_content_stream을 사용하여 청크를 즉시 yield한다.
        """

        actual_model_name = model_name or "gemini-2.5-flash"
        settings = get_settings()
        if temperature is None:
            temperature = settings.RAG_TEMPERATURE
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
                        top_k=settings.RAG_TOP_K,
                    )
                )
            ],
        )

        # grounding(인용)은 보통 마지막 청크에 실린다 — 가장 최근 값을 보관했다가 스트림 종료 후 1회 방출.
        last_grounding = None
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=actual_model_name,
            contents=build_gemini_contents(prompt, history),
            config=config,
        ):
            try:
                cand = chunk.candidates[0] if chunk.candidates else None
                gm = cand.grounding_metadata if cand else None
                if gm and gm.grounding_chunks:
                    last_grounding = gm
            except (AttributeError, IndexError):
                pass
            if chunk.text:
                yield chunk.text

        # 스트림 종료 후 인용 메타데이터를 dict 로 1회 yield (본문 str 청크와 구분).
        # generate_with_rag(비스트리밍)과 동일한 추출 로직.
        citations: list[RAGCitation] = []
        if last_grounding and last_grounding.grounding_chunks:
            for gc in last_grounding.grounding_chunks:
                if gc.retrieved_context:
                    citations.append(_citation_from_retrieved_context(gc.retrieved_context))
            citations = _dedupe_citations(citations)
        yield {"citations": [c.model_dump() for c in citations]}

    async def search_citations(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[RAGCitation]:
        """interactions.create 로 file_citation 인용을 별도 캡처한다(근사 인용).

        메인 답변 경로(generate_content)는 persona가 grounding 보고를 억제해 인용을 거의 못 남긴다.
        interactions 채널은 persona가 있어도 annotations 를 보고하므로, 응답 후 비동기 백필에서
        호출해 messages.citations 를 채운다.

        **approximate=True 인 이유**: 이 호출은 사용자에게 표시된 답변과 별개의 두 번째 생성이다.
        어노테이션의 span 은 그 두 번째 답변(B) 기준이라, 사용자가 읽은 답변(A)의 인용이 아니다.
        2026-07-02 프로브에서 25문항 중 7건의 앵커 불일치를 실측했다(표시답변엔 없는 금액을
        백필 인용이 근거로 제시하는 등). 그래서 "정확 인용"으로 단정하지 않고 근사로 라벨한다.
        exports/rag_ad_probe_2026-07-02/REPORT.md, exports/rag_citation_audit/REPORT.md 참조.

        호출/파싱 실패는 [] 반환(logger.warning) — 답변 경로를 절대 막지 않는다.
        """
        actual_model_name = model_name or "gemini-2.5-flash"
        settings = get_settings()
        store_name = await self.ensure_store()

        # persona + 인용 지침. temperature 는 지정하지 않음(0 은 인용을 억제하므로 기본 유지).
        instruction = (system_prompt or "") + _CITATION_INSTRUCTION
        tool = {
            "type": "file_search",
            "file_search_store_names": [store_name],
            "metadata_filter": f"bot_id = {bot_id}",
            "top_k": settings.RAG_TOP_K,
        }

        try:
            interaction = await self._client.aio.interactions.create(
                model=actual_model_name,
                input=prompt,
                system_instruction=instruction,
                tools=[tool],
            )
            dump = interaction.model_dump(mode="json", exclude_none=True)
        except Exception as e:
            logger.warning("search_citations 호출 실패 bot_id=%s: %s", bot_id, e)
            return []

        citations: list[RAGCitation] = []
        try:
            for step in dump.get("steps") or []:
                for content in step.get("content") or []:
                    for ann in content.get("annotations") or []:
                        if ann.get("type") != "file_citation":
                            continue
                        source = ann.get("source")
                        citations.append(
                            RAGCitation(
                                title=ann.get("file_name"),
                                content=source[:800] if source else None,
                                uri=ann.get("document_uri"),
                                page_number=ann.get("page_number"),
                                approximate=True,
                            )
                        )
            citations = _dedupe_citations(citations)
        except Exception as e:
            logger.warning("search_citations 파싱 실패 bot_id=%s: %s", bot_id, e)
            return []

        logger.info(
            "search_citations bot_id=%s model=%s citations=%d",
            bot_id,
            actual_model_name,
            len(citations),
        )
        return citations
