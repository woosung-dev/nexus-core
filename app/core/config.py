"""
Nexus Core 애플리케이션 설정.
pydantic-settings 기반 환경변수 관리.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- 앱 기본 ---
    APP_NAME: str = "Nexus Core"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- 데이터베이스 ---
    DATABASE_URL: str
    DB_SCHEMA: str = "public"

    # --- AI API 키 ---
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str | None = None

    # --- 파일 업로드 ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- RAG (File Search API) ---
    FILE_SEARCH_STORE_NAME: str = "nexus-core-knowledge-base"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
