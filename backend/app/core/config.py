"""
Nexus Core 애플리케이션 설정.
pydantic-settings 기반 환경변수 관리.
"""

import json
from functools import lru_cache

from typing import Literal

from pydantic import SecretStr, computed_field
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

    # --- AI API 키 ---
    GEMINI_API_KEY: SecretStr
    OPENAI_API_KEY: SecretStr | None = None

    # --- 파일 스토리지 ---
    STORAGE_PROVIDER: Literal["r2", "s3", "local"] = "r2"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- Cloudflare R2 ---
    # R2_ENDPOINT_URL: https://<account-id>.r2.cloudflarestorage.com
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: SecretStr | None = None
    R2_SECRET_ACCESS_KEY: SecretStr | None = None
    R2_BUCKET_NAME: str | None = None
    R2_PUBLIC_URL: str | None = None  # 커스텀 도메인 또는 r2.dev URL


    # --- RAG (File Search API) ---
    FILE_SEARCH_STORE_NAME: str = "nexus-core-knowledge-base"
    # File Search 검색 청크 수(top_k). 미설정 시 서버 기본값 → 명시 상향으로 recall 보강.
    RAG_TOP_K: int = 12
    # RAG 사실 답변 경로 생성 temperature. 재현성과 상담가 어조(다양성) 사이의 절충값.
    RAG_TEMPERATURE: float = 0.3

    # --- 멀티턴 대화 기억 ---
    # 히스토리에 포함되는 개별 메시지의 최대 길이(자). 초과분은 잘라 토큰 폭주를 막는다.
    # 0이면 컷 없음. 현재 질문에는 적용되지 않음 (봇별 윈도우 크기는 bots.history_window).
    CHAT_HISTORY_MAX_CHARS_PER_MESSAGE: int = 500

    # --- Auth (Provider-Agnostic) ---
    # JWKS URL로 JWT 서명 검증. 인증 플랫폼 교체 시 이 URL만 바꾸면 됩니다.
    # Clerk:    https://<frontend-api>.clerk.accounts.dev/.well-known/jwks.json
    # Auth0:    https://<domain>.auth0.com/.well-known/jwks.json
    AUTH_JWKS_URL: str

    # --- CORS ---
    # 환경변수에서는 콤마 구분 문자열로 주입 (예: "http://a.com,http://b.com")
    # JSON 배열 형식도 지원 (예: '["http://a.com","http://b.com"]')
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- 카카오 채널 챗봇 ---
    KAKAO_SKILL_SECRET: str | None = None
    KAKAO_SKILL_SECRET_HEADER: str = "X-Kakao-Skill-Secret"
    KAKAO_CALLBACK_ALLOWED_HOSTS: str = ".kakao.com"

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

    @computed_field
    @property
    def kakao_callback_allowed_hosts_list(self) -> list[str]:
        """콤마 구분 또는 JSON 배열 → 허용 host suffix 리스트."""
        raw = self.KAKAO_CALLBACK_ALLOWED_HOSTS.strip()
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return [h.strip() for h in raw.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
