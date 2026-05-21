from functools import lru_cache

from app.services.rag.base import BaseRAGService
from app.services.rag.gemini import GeminiRAGService


# 싱글톤 인스턴스 — provider 키별 1회 생성 후 재사용.
# 매 요청 신규 인스턴스 생성 시 인스턴스 로컬 store 캐시(_store_resource_name)가 무력화되어
# Gemini fileSearchStores.list 외부 API를 매번 호출하던 문제(580ms 손실)를 제거.
@lru_cache(maxsize=4)
def _get_gemini_rag_service() -> GeminiRAGService:
    return GeminiRAGService()


@lru_cache(maxsize=4)
def _get_openai_rag_service() -> "BaseRAGService":
    from app.services.rag.openai_rag import OpenAIRAGService

    return OpenAIRAGService()


def get_rag_service(provider: str) -> BaseRAGService:
    """
    LLM Provider 이름에 따라 적절한 RAG Service 인스턴스를 반환하는 팩토리 함수.

    Provider별 싱글톤 — 동일 provider 호출 시 같은 인스턴스를 재사용해
    인스턴스 로컬 캐시(예: Gemini의 _store_resource_name)가 유지된다.

    Args:
        provider (str): "gemini-2.5-flash", "gpt-4o" 등의 LLM 제공자/모델명

    Returns:
        BaseRAGService: 제공자에 맞는 RAG 서비스 구현체
    """
    if provider.startswith("gemini"):
        return _get_gemini_rag_service()
    elif provider.startswith("gpt") or provider == "openai":
        return _get_openai_rag_service()
    else:
        # 기본값으로 Gemini 반환 또는 에러 처리
        return _get_gemini_rag_service()
