"""
LLM 서비스 팩토리.
RAG, Storage와 동일한 Factory 패턴으로 일관성을 맞춘다.
봇의 llm_model 설정에 따라 적절한 LLM 서비스 구현체를 반환한다.
"""

from app.services.llm.base import LLMService
from app.services.llm.gemini import GeminiService
from app.services.llm.openai import OpenAIService


def get_llm_service(model_name: str) -> LLMService:
    """
    모델명에 따라 적절한 LLM 서비스를 반환한다.
    - 'gpt'로 시작하는 모델명 → OpenAIService
    - 그 외 → GeminiService (기본값)
    """
    if model_name.startswith("gpt"):
        return OpenAIService(model_name=model_name)
    return GeminiService(model_name=model_name)
