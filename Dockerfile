# --- 1단계: 빌더 이미지 (Dependencies 설치) ---
FROM python:3.12-slim AS builder

# uv 패키지 매니저 바이너리 복사 (공식 이미지 활용)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 파이썬 바이트코드 컴파일 최적화 및 시스템 의존성 설정
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 종속성 파일(pyproject.toml, uv.lock)만 먼저 복사하여 캐시 효율 극대화
COPY pyproject.toml uv.lock ./

# uv 가상환경(.venv)에 종속성 패키지만 설치 (프로젝트 코드는 나중에 복사)
RUN uv sync --frozen --no-install-project --no-dev


# --- 2단계: 런타임 이미지 (최종 경량화 이미지) ---
FROM python:3.12-slim

WORKDIR /app

# 1단계에서 완성된 가상환경 폴더 복사
COPY --from=builder /app/.venv /app/.venv

# 실제 구동할 앱 소스코드 전체 복사 (.dockerignore 적용됨)
COPY . /app

# 환경 변수 설정
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Cloud Run 규격에 맞는 8080 포트 노출
EXPOSE 8080

# uvicorn 실행 (FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
