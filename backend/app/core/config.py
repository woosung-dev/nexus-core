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
    # 비영속 맥락 보완 UX 비교 화면/API는 별도 테스트 환경에서만 연다.
    CLARIFICATION_PROTOTYPE_ENABLED: bool = False
    # 로컬 프로토타입의 익명 접근. 운영에서는 반드시 False.
    CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS: bool = False
    # 기존 테스트 봇처럼 파일럿 컬럼이 없는 DB에서만 로컬 UI가 실제 질문 생성을 허용한다.
    CLARIFICATION_PROTOTYPE_ALLOW_LIVE_UNPILOTED: bool = False
    # 마이그레이션 전 원격 테스트 DB를 읽기 전용으로 연결하기 위한 프로토타입 호환 경로.
    CLARIFICATION_PROTOTYPE_LEGACY_BOT_SCHEMA: bool = False
    # 추가 확인 질문 카드 제출을 최초 정책 판정에 묶는 HMAC 키. 비우면 Gemini 키를 사용한다.
    CLARIFICATION_POLICY_SIGNING_SECRET: SecretStr | None = None

    # --- 데이터베이스 ---
    DATABASE_URL: str

    # --- AI API 키 ---
    GEMINI_API_KEY: SecretStr
    OPENAI_API_KEY: SecretStr | None = None

    # --- 파일 스토리지 ---
    STORAGE_PROVIDER: Literal["r2", "s3", "local"] = "r2"
    MAX_UPLOAD_SIZE_MB: int = 50

    # --- Cloudflare R2 ---
    # R2_ENDPOINT_URL: https://<account-id>.r2.cloudflarestorage.com
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: SecretStr | None = None
    R2_SECRET_ACCESS_KEY: SecretStr | None = None
    R2_BUCKET_NAME: str | None = None
    R2_PUBLIC_URL: str | None = None  # 커스텀 도메인 또는 r2.dev URL


    # --- RAG (File Search API) ---
    FILE_SEARCH_STORE_NAME: str = "nexus-core-knowledge-base"
    # true이면 Store를 새로 만들거나 문서를 변경하지 않는다. 기존 Store를 읽는
    # 원격 프로토타입 검증에 사용하며, 이름을 찾지 못하면 안전하게 실패한다.
    FILE_SEARCH_STORE_READ_ONLY: bool = False
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
    # 하나로 단독 인증으로 전환하면 불필요해지므로 optional 입니다.
    AUTH_JWKS_URL: str | None = None

    # 하나로 로그인 성공 시 발급하는 세션 JWT(HS256) 서명 키.
    # 설정되면 alg=HS256 토큰을 이 키로 검증하고, 그 외 알고리즘은 JWKS 경로를 탑니다.
    AUTH_JWT_SECRET: SecretStr | None = None
    AUTH_JWT_EXPIRE_HOURS: int = 12

    # --- 하나로 SSO (공직자 판별 API v2) ---
    # 규격서 2026-07-16 v2 기준. 발급 키는 20자 이상 무작위 문자열이며 IT팀이 별도 채널로 전달합니다.
    # 소스·저장소에 커밋 금지. v1 키를 v2 주소에 쓰면 업스트림이 invalid_key 로 거부합니다.
    OFFICIAL_CHECK_KEY: SecretStr | None = None
    OFFICIAL_CHECK_URL: str = "https://hanaro.ffwp.or.kr/API_kim/officialLoginCheck2"

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
