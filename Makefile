# =============================================================================
# Nexus Core — 루트 Makefile
#
# 사용법: make <target>
#   예)  make be-dev     → 백엔드 개발 서버 실행
#        make fe-dev     → 프론트엔드(클라이언트) 개발 서버 실행
#        make up         → Docker 전체 서비스 기동
#
# 참고: 백엔드 명령어는 backend/ 디렉토리에서, 프론트 명령어는 해당 디렉토리에서 실행됩니다.
# =============================================================================

.PHONY: help \
        be-dev be-start be-migrate be-db-init \
        fe-dev fa-dev \
        up down logs

# ─── 기본: 도움말 출력 ───────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Nexus Core — 사용 가능한 명령어 목록"
	@echo ""
	@echo "  [Backend]"
	@echo "  make be-dev       백엔드 개발 서버 실행 (hot reload)"
	@echo "  make be-start     백엔드 프로덕션 서버 실행"
	@echo "  make be-migrate   Alembic 마이그레이션 실행"
	@echo "  make be-db-init   DB 초기화 스크립트 실행 (마이그레이션만)"
	@echo ""
	@echo "  [Frontend — Client]"
	@echo "  make fe-dev       클라이언트 개발 서버 실행 (port 3000)"
	@echo ""
	@echo "  [Frontend — Admin]"
	@echo "  make fa-dev       어드민 개발 서버 실행 (port 3001)"
	@echo ""
	@echo "  [Docker]"
	@echo "  make up           전체 서비스 Docker 기동"
	@echo "  make down         전체 서비스 Docker 종료"
	@echo "  make logs         전체 서비스 로그 출력 (Ctrl+C로 종료)"
	@echo ""


# ─── Backend ─────────────────────────────────────────────────────────────────

# 개발 서버 (hot reload)
be-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 프로덕션 서버
be-start:
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

# DB 마이그레이션
be-migrate:
	cd backend && uv run alembic upgrade head

# DB 초기화 (스키마 + 테이블 생성)
be-db-init:
	cd backend && uv run python scripts/setup_db.py


# ─── Frontend — Client ───────────────────────────────────────────────────────

fe-dev:
	cd frontend-client && pnpm dev


# ─── Frontend — Admin ────────────────────────────────────────────────────────

fa-dev:
	cd frontend-admin && pnpm dev


# ─── Docker ──────────────────────────────────────────────────────────────────

# 전체 서비스 기동 (백그라운드)
up:
	docker-compose up -d

# 전체 서비스 종료
down:
	docker-compose down

# 전체 로그 스트리밍
logs:
	docker-compose logs -f
