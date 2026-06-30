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

from app.core.config import get_settings
from app.schemas.rag import DocumentInfo, RAGCitation, RAGResponse
from app.services.llm.gemini import SAFETY_BLOCKED_MESSAGE
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


def _citations_from_steps(steps: list[dict]) -> list[RAGCitation]:
    """interactions 응답의 steps[].content[].annotations[] 에서 file_citation 을 RAGCitation 으로 변환.

    같은 호출에서 답변과 함께 보고된 '그 답변의 실제 출처'이므로 approximate=False (근사 아님).
    답변/스트림 경로와 search_citations 가 공유해 파싱이 갈라지지 않게 한다.
    """
    out: list[RAGCitation] = []
    for step in steps or []:
        for content in step.get("content") or []:
            for ann in content.get("annotations") or []:
                if ann.get("type") != "file_citation":
                    continue
                source = ann.get("source")
                out.append(
                    RAGCitation(
                        title=ann.get("file_name"),
                        content=source[:800] if source else None,
                        uri=ann.get("document_uri"),
                        page_number=ann.get("page_number"),
                        approximate=False,
                    )
                )
    return out


def _build_interaction_input(prompt: str, history: list[dict[str, str]] | None):
    """interactions input 생성 — history 없으면 str(단일턴), 있으면 step 리스트(과거→현재).

    build_gemini_contents 의 멀티턴 의미를 interactions step 형식으로 대응한다.
    history 규약: [{"role":"user"|"assistant","content":str}], 과거→현재, 현재 질문 미포함.
    """
    if not history:
        return prompt
    steps: list[dict] = []
    for m in history:
        step_type = "user_input" if m["role"] == "user" else "model_output"
        steps.append({"type": step_type, "content": [{"type": "text", "text": m["content"]}]})
    steps.append({"type": "user_input", "content": [{"type": "text", "text": prompt}]})
    return steps


def _chunk_text(text: str, size: int = 40):
    """의사-스트림용: 완성된 답변을 ~size자 조각으로 나눠 순차 yield(클라이언트는 그대로 이어붙임)."""
    for i in range(0, len(text), size):
        yield text[i:i + size]


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

    async def _interactions_answer(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str,
        model_name: str | None,
        temperature: float | None,
        max_tokens: int,
        history: list[dict[str, str]] | None,
    ) -> tuple[str, list[RAGCitation], list[str], bool]:
        """interactions.create 1회로 답변+정확인용+followups 를 함께 받는다(단일 호출).

        레거시 generate_content 는 persona 가 grounding 보고를 억제해 인용이 거의 0이지만,
        interactions 채널은 persona 가 있어도 '그 답변 자신의' 정확 인용(annotations)을 보고한다.
        따라서 답변과 인용이 같은 생성에서 나와 무결성이 보장된다(approximate=False).
        반환: (clean_answer, citations, followups, blocked).
        """
        actual_model_name = model_name or "gemini-2.5-flash"
        settings = get_settings()
        if temperature is None:
            temperature = settings.RAG_TEMPERATURE
        store_name = await self.ensure_store()

        # persona + 인용지침 + followups지침을 한 호출에 합친다(본문에 <followups> 블록 동반 — 실측 확인).
        system_instruction = (system_prompt or "") + _CITATION_INSTRUCTION + _FOLLOWUPS_INSTRUCTION
        tool = {
            "type": "file_search",
            "file_search_store_names": [store_name],
            "metadata_filter": f"bot_id = {bot_id}",
            "top_k": settings.RAG_TOP_K,
        }

        t_gen = time.perf_counter()
        try:
            interaction = await self._client.aio.interactions.create(
                model=actual_model_name,
                input=_build_interaction_input(prompt, history),
                system_instruction=system_instruction,
                tools=[tool],
                # temperature 0 은 인용 보고를 억제하므로 RAG_TEMPERATURE(0.3) 유지.
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens + 256},
            )
        except Exception as e:
            logger.warning("interactions RAG 호출 실패 — bot_id=%s: %s", bot_id, e)
            return SAFETY_BLOCKED_MESSAGE, [], [], True
        gen_ms = (time.perf_counter() - t_gen) * 1000

        # 세이프티/실패 차단 — interactions 는 finish_reason 대신 status 로 표현한다.
        status = getattr(interaction, "status", None)
        raw = interaction.output_text or ""
        if status in ("failed", "cancelled") or not raw.strip():
            logger.warning("RAG 응답 차단/빈응답 — bot_id=%s status=%s gen=%.1fms", bot_id, status, gen_ms)
            return SAFETY_BLOCKED_MESSAGE, [], [], True

        dump = interaction.model_dump(mode="json", exclude_none=True)
        citations = _citations_from_steps(dump.get("steps") or [])
        clean_answer, followups = _split_answer_and_followups(raw)

        logger.info(
            "interactions RAG elapsed=%.1fms model=%s bot_id=%s status=%s "
            "answer_len=%d citations=%d followups=%d",
            gen_ms, actual_model_name, bot_id, status,
            len(clean_answer), len(citations), len(followups),
        )
        return clean_answer, citations, followups, False

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
        """RAG 기반 응답 생성(비스트림). 단일 interactions 호출로 답변+정확인용+followups 동시 수신.

        Args:
            bot_id: 검색 대상 봇 ID / prompt: 사용자 질문 / system_prompt: 페르소나
            model_name: 모델(기본 gemini-2.5-flash) / temperature / max_tokens
            history: 멀티턴 이력(과거→현재, 현재 질문 미포함)
        """
        answer, citations, followups, _blocked = await self._interactions_answer(
            bot_id, prompt, system_prompt, model_name, temperature, max_tokens, history
        )
        return RAGResponse(answer=answer, citations=citations, followups=followups)

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
        """RAG 기반 의사-스트림 응답 생성.

        interactions 는 스트리밍 시 인용(annotations)을 보고하지 않는다(실측: 0건). 따라서
        단일 interactions 비스트림 호출로 답변+정확인용+followups 를 한 번에 받고(무결성 보장),
        본문을 청크로 나눠 순차 yield 해 기존 SSE 계약(str 청크 → 최종 dict)을 유지한다.
        최종 dict 는 citations 와 followups 를 함께 싣는다(별도 followup 호출 불필요).
        """
        answer, citations, followups, _blocked = await self._interactions_answer(
            bot_id, prompt, system_prompt, model_name, temperature, max_tokens, history
        )
        for piece in _chunk_text(answer):
            yield piece
        yield {
            "citations": [c.model_dump() for c in citations],
            "followups": followups,
        }

    async def search_citations(
        self,
        bot_id: int,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[RAGCitation]:
        """interactions.create 로 정확 인용(file_citation)만 별도 캡처한다(관리/수동 재인용용).

        답변 경로(generate_with_rag/generate_stream_with_rag)가 interactions 로 이전돼 인용이
        같은 호출에서 인라인으로 오므로, 이 메서드는 더 이상 답변 경로에서 자동 호출되지 않는다.
        관리자 화면의 수동 재인용 등 보조 용도로 유지한다. 실패는 [] 반환(답변 경로 무영향).
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

        citations = _citations_from_steps(dump.get("steps") or [])

        logger.info(
            "search_citations bot_id=%s model=%s citations=%d",
            bot_id,
            actual_model_name,
            len(citations),
        )
        return citations
