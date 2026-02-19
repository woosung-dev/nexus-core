# Nexus Core

> 멀티 페르소나 AI 챗봇 플랫폼 백엔드 — **Blessing Q&A** 상담 핵심

## 기술 스택

| 영역            | 기술                                    |
| --------------- | --------------------------------------- |
| Framework       | FastAPI (100% Async)                    |
| ORM             | SQLModel (Pydantic v2 + SQLAlchemy 2.0) |
| Database        | PostgreSQL + asyncpg                    |
| Migration       | Alembic                                 |
| Package Manager | uv                                      |
| AI (메인)       | Google Gemini 2.0 Flash                 |
| AI (서브)       | OpenAI GPT-4o                           |

## 시작하기

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env`를 편집하여 실제 값을 입력:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nexus
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
```

### 2. 의존성 설치

```bash
uv sync
```

### 3. 서버 실행

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 4. 확인

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 5. DB 초기화 (PostgreSQL 연결 후)

```bash
uv run python -m scripts.seed_bots
```

## API 엔드포인트

| 메서드   | 경로                       | 설명              |
| -------- | -------------------------- | ----------------- |
| `GET`    | `/api/v1/bots`             | 봇 목록 조회      |
| `POST`   | `/api/v1/chat/completions` | SSE 스트리밍 채팅 |
| `POST`   | `/api/v1/kakao/callback`   | 카카오톡 콜백     |
| `POST`   | `/api/v1/admin/bots`       | 봇 생성 (Admin)   |
| `PUT`    | `/api/v1/admin/bots/{id}`  | 봇 수정 (Admin)   |
| `DELETE` | `/api/v1/admin/bots/{id}`  | 봇 삭제 (Admin)   |

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱
├── core/                # 설정, DB
├── models/              # SQLModel 모델
├── schemas/             # Pydantic 스키마
├── api/v1/endpoints/    # API 엔드포인트
└── services/            # LLM, Storage 추상 레이어
```

> 상세 아키텍처 → [`docs/architecture/backend_structure.md`](docs/architecture/backend_structure.md)
