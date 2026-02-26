from app.services.rag.base import BaseRAGService
from app.services.rag.gemini import GeminiRAGService

def get_rag_service(provider: str) -> BaseRAGService:
    """
    LLM Provider 이름에 따라 적절한 RAG Service 인스턴스를 반환하는 팩토리 함수.
    이 함수는 애플리케이션 어디서나 RAG 서비스가 필요할 때 사용됩니다.

    Args:
        provider (str): "gemini-2.5-flash", "gpt-4o" 등의 LLM 제공자/모델명

    Returns:
        BaseRAGService: 제공자에 맞는 RAG 서비스 구현체
    """
    if provider.startswith("gemini"):
        return GeminiRAGService()
    elif provider.startswith("gpt") or provider == "openai":
        from app.services.rag.openai_rag import OpenAIRAGService

        return OpenAIRAGService()
    else:
        # 기본값으로 Gemini 반환 또는 에러 처리
        return GeminiRAGService()
