"""
FAQ Override 시맨틱 라우팅 서비스.
사용자 질문을 임베딩 → pgvector 코사인 유사도 검색 → 임계값 초과 시 FAQ 응답 반환.

흐름:
  1. get_embedding(query_text) → 768차원 벡터
  2. pgvector `<=>` 연산자로 nexus_core.faqs 테이블 검색
  3. (1 - cosine_distance) >= threshold 인 행 반환

참조:
- app/utils/embeddings.py: gemini-embedding-001 임베딩
- app/models/faq.py: Faq 모델 (Vector(768), threshold)
"""

import logging
import time
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.embeddings import get_embedding

logger = logging.getLogger(__name__)

# FAQ 존재 여부 TTL 캐시 — bot_id -> (count, 만료_timestamp)
# DB round-trip을 줄이기 위해 60어 동안 캐시 (FAQ가 자주 바뀌지 않기 때문에 타당)
_FAQ_COUNT_CACHE: dict[int, tuple[int, float]] = {}
_FAQ_COUNT_TTL_SEC = 60.0


@dataclass
class FaqMatchResult:
    """FAQ 매칭 결과"""
    faq_id: int
    question: str
    answer: str
    similarity: float  # 코사인 유사도 (0.0 ~ 1.0)


async def search_faq_override(
    session: AsyncSession,
    bot_id: int,
    query_text: str,
) -> FaqMatchResult | None:
    """
    사용자 질문에 대해 FAQ Override 매칭을 수행한다.

    1. 질문 텍스트를 임베딩 벡터로 변환
    2. pgvector 코사인 거리 연산으로 해당 봇의 활성 FAQ 검색
    3. 유사도가 해당 FAQ의 threshold 이상인 최고 유사도 항목 반환

    Args:
        session: 비동기 DB 세션
        bot_id: 검색 대상 봇 ID
        query_text: 사용자 질문 텍스트

    Returns:
        FaqMatchResult — 매칭된 FAQ 정보 (없으면 None)
    """
    try:
        # 0. 사전 확인: 해당 봇에 활성 FAQ(벡터 포함)이 존재하는지 먼저 체크
        #    TTL 캐시 타겟 없으면 DB 쿼리 수행, 있으면 캐시로 증답
        now = time.monotonic()
        cached = _FAQ_COUNT_CACHE.get(bot_id)
        if cached and now - cached[1] < _FAQ_COUNT_TTL_SEC:
            # 캐시 HIT: DB 쿼리 생략
            faq_count = cached[0]
            logger.debug(f"FAQ count 캐시 HIT: bot_id={bot_id}, count={faq_count}")
        else:
            # 캐시 MISS: DB에서 COUNT 쿼리
            count_result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM nexus_core.faqs
                    WHERE bot_id = :bot_id
                      AND is_active = true
                      AND question_vector IS NOT NULL
                """),
                {"bot_id": bot_id},
            )
            faq_count = count_result.scalar() or 0
            _FAQ_COUNT_CACHE[bot_id] = (faq_count, now)
            logger.debug(f"FAQ count 캐시 MISS: bot_id={bot_id}, count={faq_count}")

        if not faq_count:
            logger.debug(f"FAQ 없음, 임베딩 생략: bot_id={bot_id}")
            return None

        # 1. FAQ가 존재하는 경우에만 사용자 질문 임베딩 생성
        query_vector = await get_embedding(query_text)
        vector_str = f"[{','.join(str(v) for v in query_vector)}]"

        # 2. pgvector 코사인 거리 검색
        #    <=> 연산자는 코사인 거리(0=동일, 2=정반대)를 반환하므로
        #    유사도 = 1 - distance
        #    asyncpg는 named param(:vec)과 ::vector 캐스팅을 혼용할 수 없으므로
        #    벡터 값은 SQL에 직접 포함한다 (float 배열이라 SQL Injection 위험 없음)
        sql = f"""
            SELECT id, question, answer, threshold,
                   1 - (question_vector <=> '{vector_str}'::vector) AS similarity
            FROM nexus_core.faqs
            WHERE bot_id = :bot_id
              AND is_active = true
              AND question_vector IS NOT NULL
            ORDER BY question_vector <=> '{vector_str}'::vector
            LIMIT 1
        """
        result = await session.execute(
            text(sql),
            {"bot_id": bot_id},
        )
        row = result.fetchone()

        if not row:
            logger.debug(f"FAQ 검색 결과 없음: bot_id={bot_id}")
            return None

        faq_id, question, answer, threshold, similarity = row

        logger.info(
            f"FAQ 매칭 후보: id={faq_id}, "
            f"similarity={similarity:.4f}, threshold={threshold}, "
            f"question='{question[:30]}...'"
        )

        # 3. 임계값 확인
        if similarity >= threshold:
            logger.info(
                f"✅ FAQ Override 매칭 성공: id={faq_id}, "
                f"similarity={similarity:.4f} >= threshold={threshold}"
            )
            return FaqMatchResult(
                faq_id=faq_id,
                question=question,
                answer=answer,
                similarity=round(similarity, 4),
            )

        logger.debug(
            f"❌ FAQ 임계값 미달: similarity={similarity:.4f} < threshold={threshold}"
        )
        return None

    except RuntimeError:
        # 임베딩 생성 실패 — FAQ 검색 실패 시 LLM 폴백
        logger.warning("FAQ 임베딩 생성 실패, LLM 폴백으로 진행")
        return None
    except Exception as e:
        # 기타 오류 — FAQ 검색 실패해도 채팅은 계속 동작해야 함
        logger.error(f"FAQ Override 검색 오류: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Admin FAQ 생성/수정 — 임베딩 조립 (Service 레이어)
# ──────────────────────────────────────────────────────────────────────────────

async def create_faq_with_embedding(
    session: AsyncSession,
    bot_id: int,
    question: str,
    answer: str,
    threshold: float,
) -> "Faq":
    """
    FAQ 등록 서비스.
    질문 텍스트를 임베딩(외부 AI API) → CRUD로 DB 저장.

    Raises:
        NexusException(EMBEDDING_FAILED): 임베딩 API 오류 시
    """
    from app.core.exceptions import NexusException
    from app.crud import crud_faq

    try:
        question_vector = await get_embedding(question)
    except RuntimeError as e:
        raise NexusException(
            error_code="EMBEDDING_FAILED",
            message="임베딩 생성 중 오류가 발생했습니다.",
            status_code=502,
            details=str(e),
        )

    faq = await crud_faq.create_faq(
        session=session,
        bot_id=bot_id,
        question=question,
        answer=answer,
        threshold=threshold,
        question_vector=question_vector,
    )
    logger.info(f"FAQ 등록: id={faq.id}, bot_id={bot_id}, question='{question[:30]}'")
    return faq


async def update_faq_with_embedding(
    session: AsyncSession,
    faq: "Faq",
    update_data: dict,
) -> "Faq":
    """
    FAQ 수정 서비스.
    question이 변경된 경우 임베딩을 자동 재생성.

    Raises:
        NexusException(EMBEDDING_FAILED): 임베딩 API 오류 시
    """
    from app.core.exceptions import NexusException
    from app.crud import crud_faq

    if "question" in update_data and update_data["question"] != faq.question:
        try:
            update_data["question_vector"] = await get_embedding(update_data["question"])
        except RuntimeError as e:
            raise NexusException(
                error_code="EMBEDDING_FAILED",
                message="임베딩 재생성 중 오류가 발생했습니다.",
                status_code=502,
                details=str(e),
            )

    updated = await crud_faq.update_faq(session, faq, update_data)
    logger.info(f"FAQ 수정: id={faq.id}, changes={list(update_data.keys())}")
    return updated

