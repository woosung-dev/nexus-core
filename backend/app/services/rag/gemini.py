"""
Gemini File Search API 기반 RAG 서비스.

하나의 공유 Store에 메타데이터(bot_id)로 봇별 문서를 구분한다.
벡터 DB 없이 Google 관리형 RAG를 구현.
"""

import hashlib
import io
import json
import logging
import re
import time
from datetime import datetime
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

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
# 일반 답변은 JSON 스키마가 아니라 텍스트 마커로 followups 를 분리한다.
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
# JSON 응답이 코드 펜스로 감싸져도 스키마 검증 전에 본문만 꺼낸다.
_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
# Interactions의 자연어 근거 블록 뒤에 붙는 기계 소비용 계획 JSON을 꺼낸다.
_PLAN_ENVELOPE_RE = re.compile(r"\[PLAN\]\s*(.*)\Z", re.DOTALL | re.IGNORECASE)


def _structured_json_from_output(output_text: str) -> str | None:
    """PLAN envelope를 우선하고, 유효한 bare JSON만 제한적으로 복구한다.

    Interactions가 명시된 [PLAN] 태그를 드물게 빼더라도 JSON 객체 자체가 온전하면 이는
    의미 판단 실패가 아니라 transport 형식 변형이다. 자연어 응답은 None으로 남겨 호출자가
    안전하게 실패 처리한다.
    """
    envelope_match = _PLAN_ENVELOPE_RE.search(output_text)
    if envelope_match:
        raw_json = _CITATION_MARKER_RE.sub("", envelope_match.group(1))
        fence_match = _JSON_FENCE_RE.match(raw_json)
        return fence_match.group(1) if fence_match else raw_json

    cleaned = _CITATION_MARKER_RE.sub("", output_text).strip()
    fence_match = _JSON_FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1)
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
    return None
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

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)


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


def _citation_key(c: RAGCitation) -> tuple[str | None, str | None, int | None, str]:
    """청크 동일성 키. Gemini Developer API 엔 안정적 청크 ID 가 없어(chunk_id·document_name 은
    Vertex 전용) (제목, uri, 페이지, 본문 앞부분 해시)로 근사한다.

    uri 를 포함하는 이유: source 가 비면 content 가 None 이라 해시가 전부 같아진다.
    그때 제목·페이지만으로 묶으면 서로 다른 청크가 한 건으로 뭉개진다.
    """
    body = (c.content or "").strip()
    return (c.title, c.uri, c.page_number, hashlib.sha256(body[:200].encode()).hexdigest())


def _dedupe_citations(citations: list[RAGCitation]) -> list[RAGCitation]:
    """같은 청크는 하나로 합치고 cite_count 를 누적한다(첫 등장 순서 보존).

    한 청크가 답변의 여러 구간을 뒷받침하면 어노테이션이 구간마다 1건씩 붙어 목록이
    수십 건으로 불어난다(실측 35건 → 고유 청크 10개, 문서 3개). 중복을 버리기만 하면
    "어느 문서를 제일 많이 참고했나"를 잃으므로, 합치면서 횟수를 점수로 남긴다.
    """
    merged: dict[tuple[str | None, str | None, int | None, str], RAGCitation] = {}
    for c in citations:
        key = _citation_key(c)
        prev = merged.get(key)
        if prev is None:
            merged[key] = c.model_copy(deep=True)
        else:
            prev.cite_count += c.cite_count
            # 같은 청크가 답변의 여러 구간을 뒷받침하면 구간도 함께 모은다(중복 제외).
            for seg in c.segments:
                if seg not in prev.segments:
                    prev.segments.append(seg)
    return list(merged.values())


def _citations_from_grounding(grounding) -> list[RAGCitation]:
    """grounding_metadata → RAGCitation 목록. chunks 로 만들고 supports 로 답변 구간을 붙인다.

    grounding_supports[].grounding_chunk_indices 는 **원본 grounding_chunks 의 인덱스**라,
    구간을 붙이는 일은 반드시 중복 제거 이전에 끝내야 한다(합치고 나면 인덱스가 어긋난다).

    supports 는 지금까지 버려지던 데이터다. 여기엔 (답변 구간 ↔ 청크) 매핑이 들어 있어
    추가 API 호출 없이 "이 문장은 이 자료 근거" 표시를 만들 수 있다. 2026-07-25 D-1 프로브에서
    3.5-flash-lite 는 5/5 문항에 supports 를 3~10개씩 실었고, segment.text 는 답변 본문에
    100% 그대로 존재했다(37/37) — 그래서 byte offset 대신 문자열 검색으로 앵커한다.
    """
    chunks = grounding.grounding_chunks or []
    # supports 인덱스와 자리를 맞추기 위해 retrieved_context 가 없는 칸도 None 으로 남긴다.
    by_index: list[RAGCitation | None] = [
        _citation_from_retrieved_context(gc.retrieved_context) if gc.retrieved_context else None
        for gc in chunks
    ]

    for sup in getattr(grounding, "grounding_supports", None) or []:
        text = (getattr(sup.segment, "text", None) or "").strip() if sup.segment else ""
        if not text:
            continue
        for idx in sup.grounding_chunk_indices or []:
            cit = by_index[idx] if 0 <= idx < len(by_index) else None
            if cit is not None and text not in cit.segments:
                cit.segments.append(text)

    return _dedupe_citations([c for c in by_index if c is not None])


def _citations_from_interaction(interaction, *, approximate: bool) -> list[RAGCitation]:
    """Interactions의 같은 model_output annotations를 RAGCitation으로 변환한다."""
    dump = interaction.model_dump(mode="json", exclude_none=True)
    citations: list[RAGCitation] = []
    for step in dump.get("steps") or []:
        for content in step.get("content") or []:
            for annotation in content.get("annotations") or []:
                if annotation.get("type") != "file_citation":
                    continue
                source = annotation.get("source")
                citations.append(
                    RAGCitation(
                        title=annotation.get("file_name"),
                        content=source[:800] if source else None,
                        uri=annotation.get("document_uri"),
                        page_number=annotation.get("page_number"),
                        approximate=approximate,
                    )
                )
    citations = _dedupe_citations(citations)
    citations.sort(key=lambda citation: citation.cite_count, reverse=True)
    return citations


class GeminiRAGService(BaseRAGService):
    """Gemini File Search 기반 RAG 응답 및 업로드 서비스"""

    def __init__(self) -> None:
        # 프로세스 레벨 싱글톤 client 재사용 (메인 LLM/followup과 동일).
        from app.services.llm.gemini import _get_genai_client

        settings = get_settings()
        self._client = _get_genai_client()
        self._store_name = settings.FILE_SEARCH_STORE_NAME
        self._store_read_only = settings.FILE_SEARCH_STORE_READ_ONLY
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
            if self._store_read_only:
                raise RuntimeError(
                    "읽기 전용 File Search Store를 조회하지 못했습니다. "
                    "새 Store를 만들지 않습니다."
                ) from e

        if self._store_read_only:
            raise RuntimeError(
                f"읽기 전용 File Search Store를 찾지 못했습니다: {self._store_name}"
            )

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
        if self._store_read_only:
            raise PermissionError("읽기 전용 File Search Store에는 문서를 업로드할 수 없습니다.")
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
        if self._store_read_only:
            raise PermissionError("읽기 전용 File Search Store에서는 문서를 삭제할 수 없습니다.")
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
                citations = _citations_from_grounding(grounding)
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

    async def generate_structured_with_rag(
        self,
        *,
        bot_id: int,
        prompt: str,
        system_prompt: str,
        model_name: str,
        response_schema: type[StructuredResult],
        temperature: float = 0.0,
        max_tokens: int = 1_200,
    ) -> tuple[StructuredResult, list[RAGCitation]]:
        """한 번의 Interactions File Search 호출에서 계획 JSON과 같은 호출 인용을 받는다.

        D-1의 Gemini 3.5 Flash-Lite는 native ``response_format`` JSON과 File Search를
        같이 쓰면 file_citation을 반환하지 않았다. 먼저 짧은 자연어 근거를 생성해
        citation annotation을 붙이고, 뒤의 ``[PLAN]`` JSON만 Pydantic으로 검증한다.
        """
        store_name = await self.ensure_store()
        tool = {
            "type": "file_search",
            "file_search_store_names": [store_name],
            "metadata_filter": f"bot_id = {bot_id}",
            "top_k": get_settings().RAG_TOP_K,
        }

        t_gen = time.perf_counter()
        interaction = await self._client.aio.interactions.create(
            model=model_name,
            input=prompt,
            system_instruction=(system_prompt or "")
            + _CITATION_INSTRUCTION
            + """

[출력 형식]
먼저 [EVIDENCE] 태그 안에 검색 문서에 근거한 한두 문장만 작성한다.
그 다음 [PLAN] 태그 안에 기존 계약의 JSON 객체만 작성한다. JSON 외 설명은 EVIDENCE에만 둔다.
""",
            tools=[tool],
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
            # D-1 프로토타입은 DB와 함께 Gemini의 서버 대화 상태도 남기지 않는다.
            store=False,
        )
        gen_ms = (time.perf_counter() - t_gen) * 1000

        output_text = getattr(interaction, "output_text", "") or ""
        raw_json = _structured_json_from_output(output_text)
        if raw_json is None:
            raise RuntimeError("RAG 기반 맥락 보완 응답에 [PLAN] JSON이 없습니다.")
        if not raw_json.strip():
            raise RuntimeError("RAG 기반 맥락 보완 응답이 비어 있습니다.")
        result = response_schema.model_validate_json(raw_json)

        try:
            citations = _citations_from_interaction(interaction, approximate=False)
        except Exception as exc:
            logger.debug("구조화 Interactions 인용 추출 실패: %s", exc)
            citations = []

        logger.info(
            "gemini structured Interactions elapsed=%.1fms model=%s bot_id=%s citations=%d",
            gen_ms,
            model_name,
            bot_id,
            len(citations),
        )
        return result, citations

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
            citations = _citations_from_grounding(last_grounding)
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
        # 주의: 이 기본값은 사실상 죽은 값이다 — chat_service 가 항상 model_name=bot.llm_model
        # (=gemini-3.1-flash-lite)을 명시 전달한다. 그리고 그게 맞다: 2026-07-14 스윕(봇5 라이브
        # persona × 실사용자 25문항)에서 인용율이 flash-lite 88% vs 2.5-flash 40% 로, 현행 lite 가
        # 2.2배 낫다. 2.5-flash 는 상담형 질문에서 인용을 통째로 포기한다(13문항 중 lite 만 인용).
        # 2026-06-30 통제실험의 "2.5-flash 100%" 는 정보성 문항 12trial 한정이라 재현되지 않았다.
        # 근거: exports/rag_citation_sweep_2026-07-14/REPORT.md
        actual_model_name = model_name or "gemini-3.1-flash-lite"
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
        except Exception as e:
            logger.warning("search_citations 호출 실패 bot_id=%s: %s", bot_id, e)
            return []

        try:
            citations = _citations_from_interaction(interaction, approximate=True)
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

    async def fill_evidence(
        self, citations: list[RAGCitation], answer: str, model_name: str | None = None
    ) -> int:
        """각 인용 청크에서 실제 근거가 된 구절을 찾아 evidence 에 채운다(제자리 수정).

        답변 전송 이후 비동기로 도는 것을 전제로 한다 — 청크당 1회 호출이라 사용자 대기에
        넣으면 안 된다. 자세한 근거는 services/rag/evidence.py 참조.
        """
        from app.services.rag.evidence import fill_evidence

        return await fill_evidence(
            self._client, model_name or "gemini-3.5-flash-lite", citations, answer
        )
