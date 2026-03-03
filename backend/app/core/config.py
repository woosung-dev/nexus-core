"""
Nexus Core 애플리케이션 설정.
pydantic-settings 기반 환경변수 관리.
"""

import json
from functools import lru_cache

from pydantic import computed_field
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

    # --- Auth (Provider-Agnostic) ---
    # JWKS URL로 JWT 서명 검증. 인증 플랫폼 교체 시 이 URL만 바꾸면 됩니다.
    # Supabase: https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
    # Auth0:    https://<domain>.auth0.com/.well-known/jwks.json
    AUTH_JWKS_URL: str

    # --- CORS ---
    # 환경변수에서는 콤마 구분 문자열로 주입 (예: "http://a.com,http://b.com")
    # JSON 배열 형식도 지원 (예: '["http://a.com","http://b.com"]')
    CORS_ORIGINS: str = "http://localhost:3000"

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS 문자열을 리스트로 변환하여 반환."""
        raw = self.CORS_ORIGINS.strip()
        # JSON 배열 형식인 경우
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        # 콤마 구분 문자열인 경우
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
