# AWS 이관 분석 리포트 — Nexus Core

> 작성일: 2026-03-21
> 현재 스택: GCP Cloud Run / Vercel / Supabase / Cloudflare R2
> 이관 대상: AWS (EC2 or ECR+ECS/Fargate)

---

## 현재 인프라 구성 요약

| 레이어              | 현재                             | 이관 대상                           |
| ------------------- | -------------------------------- | ----------------------------------- |
| Backend 호스팅      | GCP Cloud Run                    | AWS EC2 or ECR+ECS/Fargate          |
| Frontend 호스팅     | Vercel                           | AWS (Amplify / S3+CloudFront / EC2) |
| Database            | Supabase (PostgreSQL)            | 유지 or AWS RDS                     |
| 파일 스토리지       | Supabase Storage / Cloudflare R2 | AWS S3                              |
| 컨테이너 레지스트리 | GCP Artifact Registry            | AWS ECR                             |
| CI/CD               | GitHub Actions → GCP             | GitHub Actions → AWS                |

---

## EC2 vs ECR+ECS 비교

| 항목                  | EC2 (직접 운영)              | ECR + ECS/Fargate                              |
| --------------------- | ---------------------------- | ---------------------------------------------- |
| 인프라 관리           | 직접 OS/런타임 관리 필요     | 완전 컨테이너 오케스트레이션                   |
| 비용                  | 상시 고정 비용               | 실행 시간 기반                                 |
| 현재 Docker 구성 활용 | 가능 (docker-compose)        | 그대로 재활용 가능 (권장)                      |
| 스케일링              | Auto Scaling Group 별도 구성 | 자동 스케일링 내장                             |
| GCP Cloud Run 유사성  | 낮음                         | **높음** (Cloud Run → Fargate 전환 자연스러움) |
| 배포 파이프라인 변경  | 중간                         | 소규모 (Dockerfile 재사용)                     |

> **권장**: 현재 Cloud Run 환경이므로 **ECR + ECS Fargate**가 가장 자연스러운 전환입니다.

---

## 1. CI/CD 파이프라인 변경

**파일**: `.github/workflows/deploy-backend.yml`

### 현재 (GCP)

```yaml
- google-github-actions/auth@v2 # GCP 인증
- docker/login-action → GCP Artifact Registry
- google-github-actions/deploy-cloudrun@v2
```

### AWS 전환 시 교체 항목

```yaml
# 변경 전
env:
  GCP_PROJECT_ID: developer-project-488310
  REGION: asia-northeast3
  REPOSITORY: nexus-repo
  SERVICE: nexus-core

# 변경 후 (예시)
env:
  AWS_REGION: ap-northeast-2           # 서울 리전
  ECR_REPOSITORY: nexus-core
  ECS_SERVICE: nexus-core-service      # ECS 사용 시
  ECS_CLUSTER: nexus-cluster

# 인증 변경
- uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ap-northeast-2
```

**GitHub Secrets 교체 목록**:

- `GCP_CREDENTIALS` → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

---

## 2. Docker 이미지 레지스트리 변경

**파일**: `backend/Dockerfile`, `.github/workflows/deploy-backend.yml`

```bash
# 현재 이미지 태그 형식
asia-northeast3-docker.pkg.dev/developer-project-488310/nexus-repo/nexus-core:${{ github.sha }}

# AWS ECR 형식으로 변경
{account_id}.dkr.ecr.ap-northeast-2.amazonaws.com/nexus-core:${{ github.sha }}
```

> **Dockerfile 자체는 변경 불필요** — `python:3.12-slim` 기반으로 GCP 의존성 없음.

---

## 3. Frontend 배포 변경 (Vercel → AWS)

**CORS 설정 변경 필요** — 현재 하드코딩된 Vercel URL들:

**파일**: `.github/workflows/deploy-backend.yml:64`

```yaml
# 현재
CORS_ORIGINS=https://nexus-core-admin.vercel.app,https://nexus-core-six.vercel.app,...

# AWS 도메인으로 교체 필요
CORS_ORIGINS=https://your-admin.amazonaws.com,https://your-client.amazonaws.com,...
```

**Frontend 옵션별 추가 작업**:

| 옵션                | 변경 사항                                      |
| ------------------- | ---------------------------------------------- |
| **AWS Amplify**     | 연결만 하면 Vercel과 유사 (최소 변경)          |
| **S3 + CloudFront** | `next export` 또는 static build 필요, SSR 불가 |
| **EC2/ECS**         | Next.js standalone mode 빌드 설정 추가         |

> 현재 frontend가 Supabase SSR(`@supabase/ssr`)을 사용하므로 **SSR 지원 필수** → S3+CloudFront 단독은 부적합

**파일**: `frontend-client/next.config.ts:6`

```ts
// 현재 Cloud Run URL 하드코딩 → AWS ALB/ECS URL로 교체 필요
"nexus-core-58481128769.asia-northeast3.run.app";
```

---

## 4. 스토리지 마이그레이션 (R2 / Supabase Storage → S3)

**현재 구조**: Factory 패턴으로 provider 교체 가능하게 이미 설계됨 (`STORAGE_PROVIDER` env)

**파일**: `backend/app/services/storage/`

### S3 Provider 추가 작업

`r2.py`는 이미 `boto3` 기반이므로 거의 그대로 재활용 가능:

```python
# r2.py → s3.py 복사 후 수정 포인트

# 현재 R2 엔드포인트 (제거)
endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# S3는 endpoint_url 불필요 (기본 AWS endpoint 사용)
# R2_* 환경변수 → AWS_S3_* 로 rename
```

**환경변수 추가/변경**:

```
STORAGE_PROVIDER=s3
AWS_S3_BUCKET_NAME=nexus-core-uploads
AWS_S3_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_PUBLIC_URL=https://your-cdn.cloudfront.net  # CloudFront 사용 시
```

**파일**: `backend/app/core/config.py` — S3 관련 필드 추가 필요

---

## 5. 데이터베이스 (Supabase PostgreSQL)

Supabase는 내부적으로 AWS `ap-south-1`(인도)에서 호스팅 중:

```
aws-1-ap-south-1.pooler.supabase.com:6543
```

### 선택지

| 옵션                        | 변경 규모 | 비고                                    |
| --------------------------- | --------- | --------------------------------------- |
| **Supabase 유지**           | 없음      | 지역 레이턴시 이슈 가능                 |
| **AWS RDS PostgreSQL 이관** | 대규모    | pgvector 지원 확인 필요, 인증 체계 변경 |

**RDS 이관 시 필수 변경**:

1. `database.py:statement_cache_size=0` 설정 — RDS는 제거 가능
2. `DB_SCHEMA=nexus_core` — 스키마 유지 필요
3. **Supabase Auth 대체 솔루션 필요** (Cognito, Auth.js, 자체 구현 등)
4. JWKS URL 변경: `AUTH_JWKS_URL` → Cognito JWKS endpoint 등

> **Supabase Auth를 AWS Cognito로 교체하는 것이 가장 큰 작업입니다.**

---

## 6. 인증 시스템 (가장 큰 변경 포인트)

현재 **Supabase Auth** 의존도가 높음:

**Frontend** (`frontend-client/src/lib/supabase/`):

- `createBrowserClient()` — Supabase JS SDK
- `createServerClient()` — SSR 쿠키 기반
- Zustand store에서 Supabase session 동기화

**Backend** (`backend/app/core/config.py:46`):

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- JWT 검증: `AUTH_JWKS_URL` (Supabase JWKS endpoint)

**Cognito 전환 시 수정 파일 목록**:

```
frontend-client/src/lib/supabase/client.ts     → Cognito Amplify SDK
frontend-client/src/lib/supabase/server.ts     → Cognito server-side
frontend-client/src/store/useAuthStore.ts      → Cognito session 관리
frontend-admin/src/lib/supabase/ (동일 구조)
backend/app/core/config.py                     → Cognito 환경변수
backend/app/api/deps.py (JWT 검증 로직)        → Cognito JWKS
```

---

## 7. 이미지 도메인 허용 설정

**파일**: `frontend-client/next.config.ts`, `frontend-admin/next.config.ts`

```ts
// 현재 허용 도메인 → 교체 필요
images: {
  remotePatterns: [
    { hostname: "*.supabase.co" }, // → S3/CloudFront 도메인
    { hostname: "*.r2.cloudflarestorage.com" }, // → S3 도메인
  ];
}
```

---

## 8. 변경 규모별 우선순위 (Phase)

### Phase 1 — 최소 변경 (Backend만 AWS 이관)

| 항목                       | 파일                                   | 난이도 |
| -------------------------- | -------------------------------------- | ------ |
| CI/CD GCP → AWS            | `.github/workflows/deploy-backend.yml` | 낮음   |
| ECR 이미지 레지스트리 교체 | 동일 파일                              | 낮음   |
| ECS Task Definition 작성   | 신규 파일                              | 중간   |
| CORS_ORIGINS URL 교체      | 환경변수                               | 낮음   |
| Cloud Run URL 제거         | `frontend-client/next.config.ts:6`     | 낮음   |

### Phase 2 — 스토리지 S3 전환

| 항목                              | 파일                                        | 난이도 |
| --------------------------------- | ------------------------------------------- | ------ |
| S3 StorageProvider 추가           | `backend/app/services/storage/s3.py` (신규) | 낮음   |
| factory.py s3 케이스 추가         | `backend/app/services/storage/factory.py`   | 낮음   |
| config.py S3 필드 추가            | `backend/app/core/config.py`                | 낮음   |
| next.config.ts 이미지 도메인 교체 | `frontend-*/next.config.ts`                 | 낮음   |

### Phase 3 — 데이터베이스 & 인증 (선택적)

| 항목                              | 난이도    |
| --------------------------------- | --------- |
| Supabase DB → RDS PostgreSQL 이관 | 높음      |
| Supabase Auth → Cognito 전환      | 매우 높음 |
| Frontend 인증 라이브러리 교체     | 높음      |

---

## 9. 전체 수정 파일 체크리스트

```
[ ] .github/workflows/deploy-backend.yml         # CI/CD 전면 교체
[ ] frontend-client/next.config.ts               # Cloud Run URL, 이미지 도메인
[ ] frontend-admin/next.config.ts                # 이미지 도메인
[ ] backend/app/core/config.py                   # S3/AWS 환경변수 추가
[ ] backend/app/services/storage/factory.py      # s3 케이스 추가
[ ] backend/app/services/storage/s3.py           # 신규 파일 (r2.py 기반)
[ ] (선택) frontend-client/src/lib/supabase/     # Cognito 전환 시
[ ] (선택) frontend-admin/src/lib/supabase/      # Cognito 전환 시
[ ] (선택) backend/app/api/deps.py               # JWKS 변경 시
```
