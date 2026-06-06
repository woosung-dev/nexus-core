# AWS 이관 단계별 실습 가이드

> 이 문서는 AWS 인프라 경험이 많지 않은 분을 위한 단계별 실습 가이드입니다.
> 전략적 분석은 [aws-migration.md](../architecture/aws-migration.md)를 참고하세요.

---

## 용어 먼저 이해하기

| 용어                                 | 쉬운 설명                                                      | 현재 대응                        |
| ------------------------------------ | -------------------------------------------------------------- | -------------------------------- |
| **ECR** (Elastic Container Registry) | Docker 이미지를 저장하는 창고                                  | GCP Artifact Registry            |
| **ECS** (Elastic Container Service)  | Docker 컨테이너를 실행·관리하는 시스템                         | GCP Cloud Run                    |
| **Fargate**                          | ECS에서 서버 없이 컨테이너만 실행하는 방식 (서버리스 컨테이너) | GCP Cloud Run과 동일 개념        |
| **EC2**                              | 직접 관리하는 가상 서버 (리눅스 서버 한 대를 빌리는 것)        | —                                |
| **S3**                               | 파일(이미지, 문서 등)을 저장하는 클라우드 저장소               | Cloudflare R2 / Supabase Storage |
| **ALB**                              | 트래픽을 여러 서버로 분산해주는 로드밸런서                     | Cloud Run 내장 기능              |
| **IAM**                              | AWS 권한 관리 시스템 (누가 무엇을 할 수 있는지 설정)           | GCP Service Account              |
| **Region**                           | AWS 서버가 있는 지역. 한국은 `ap-northeast-2` (서울)           | `asia-northeast3` (서울)         |

---

## 전체 이관 흐름

```
[Phase 1] AWS 계정 준비 & 기본 설정
     ↓
[Phase 2] ECR에 Docker 이미지 등록
     ↓
[Phase 3] ECS Fargate로 Backend 실행
     ↓
[Phase 4] GitHub Actions CI/CD 연결
     ↓
[Phase 5] S3로 파일 스토리지 이관
     ↓
[Phase 6] Frontend 이관 (Vercel → AWS Amplify)
     ↓
[Phase 7] (선택) Supabase → RDS + Cognito 이관
```

---

## Phase 1 — AWS 계정 준비 & 기본 설정

### 1-1. AWS 계정 생성

1. [https://aws.amazon.com](https://aws.amazon.com) 접속 → 계정 생성
2. 신용카드 등록 (처음 12개월은 무료 티어 제공)
3. **리전을 서울로 설정**: 우측 상단 드롭다운 → `아시아 태평양(서울) ap-northeast-2`

> 중요: 모든 서비스를 같은 리전(서울)에 만들어야 네트워크 비용이 최소화됩니다.

### 1-2. IAM 사용자 생성 (보안 설정)

AWS root 계정을 직접 사용하면 위험합니다. 별도 사용자를 만들어야 합니다.

1. AWS 콘솔 → 검색창에 `IAM` 입력 → IAM 서비스 이동
2. 좌측 메뉴 → `사용자` → `사용자 생성` 클릭
3. 사용자 이름 입력 (예: `nexus-core-deploy`)
4. `직접 정책 연결` 선택 후 아래 권한 추가:
   - `AmazonEC2ContainerRegistryFullAccess` — ECR 접근
   - `AmazonECS_FullAccess` — ECS 접근
   - `AmazonS3FullAccess` — S3 접근
5. 사용자 생성 후 → `보안 자격 증명` 탭 → `액세스 키 만들기`
6. `AWS 외부에서 실행되는 애플리케이션` 선택
7. **Access Key ID**와 **Secret Access Key**를 안전한 곳에 저장 (다시 볼 수 없음!)

### 1-3. AWS CLI 설치 (로컬 컴퓨터)

```bash
# macOS
brew install awscli

# 설치 확인
aws --version
```

### 1-4. AWS CLI 설정

```bash
aws configure
```

아래 내용 입력:

```
AWS Access Key ID: (1-2에서 저장한 Access Key ID)
AWS Secret Access Key: (1-2에서 저장한 Secret Access Key)
Default region name: ap-northeast-2
Default output format: json
```

---

## Phase 2 — ECR에 Docker 이미지 등록

ECR은 Docker 이미지를 저장하는 창고입니다. GitHub Actions가 여기에 이미지를 올리고, ECS가 여기서 이미지를 가져와 실행합니다.

### 2-1. ECR 저장소 생성

1. AWS 콘솔 → 검색창 `ECR` → `Elastic Container Registry` 이동
2. `리포지토리 생성` 클릭
3. 설정:
   - 가시성: `프라이빗`
   - 리포지토리 이름: `nexus-core`
4. `리포지토리 생성` 완료
5. 생성된 리포지토리 클릭 → 상단의 **URI 복사** (예: `123456789.dkr.ecr.ap-northeast-2.amazonaws.com/nexus-core`)

### 2-2. 로컬에서 ECR 연결 테스트

```bash
# ECR 로그인 (AWS CLI 필요)
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com

# 현재 backend 이미지 빌드
cd backend
docker build -t nexus-core .

# ECR용 태그 추가
docker tag nexus-core:latest \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com/nexus-core:latest

# ECR에 업로드
docker push 123456789.dkr.ecr.ap-northeast-2.amazonaws.com/nexus-core:latest
```

업로드 성공하면 ECR 콘솔에서 이미지가 보입니다.

---

## Phase 3 — ECS Fargate로 Backend 실행

ECS Fargate = "Docker 컨테이너를 서버 없이 실행하는 서비스". Cloud Run과 동일한 개념입니다.

### 3-1. ECS 클러스터 생성

클러스터는 여러 서비스를 묶는 논리적 그룹입니다.

1. AWS 콘솔 → `ECS` 이동
2. `클러스터 생성` 클릭
3. 설정:
   - 클러스터 이름: `nexus-cluster`
   - 인프라: `AWS Fargate` 선택 (서버 관리 불필요)
4. `생성` 완료

### 3-2. 태스크 정의 생성

태스크 정의 = 컨테이너 실행 설정 (어떤 이미지, CPU/메모리, 환경변수 등)

1. ECS → `태스크 정의` → `새 태스크 정의 생성`
2. 설정:
   - 태스크 정의 이름: `nexus-core-task`
   - 인프라: `AWS Fargate`
   - OS/아키텍처: `Linux/X86_64`
   - CPU: `0.5 vCPU` (나중에 필요에 따라 조정)
   - 메모리: `1 GB`
3. **컨테이너 추가**:
   - 이름: `nexus-core`
   - 이미지 URI: `123456789.dkr.ecr.ap-northeast-2.amazonaws.com/nexus-core:latest`
   - 컨테이너 포트: `8080` (Protocol: TCP)
4. **환경 변수 추가** (현재 GCP에 설정된 값들):

   | 키                     | 값                              |
   | ---------------------- | ------------------------------- |
   | `DATABASE_URL`         | Supabase 연결 문자열            |
   | `GEMINI_API_KEY`       | Gemini API 키                   |
   | `OPENAI_API_KEY`       | OpenAI API 키                   |
   | `AUTH_JWKS_URL`        | Supabase JWKS URL               |
   | `SUPABASE_URL`         | Supabase 프로젝트 URL           |
   | `SUPABASE_SERVICE_KEY` | Supabase Service Key            |
   | `STORAGE_PROVIDER`     | `supabase` (초기엔 그대로 유지) |
   | `CORS_ORIGINS`         | 새 frontend URL로 변경 예정     |

   > 보안 팁: 민감한 값은 `AWS Secrets Manager`나 `Parameter Store`에 저장하고 참조하는 방식을 권장하지만, 초기에는 직접 입력해도 동작합니다.

5. `생성` 완료

### 3-3. ECS 서비스 생성

서비스 = 태스크를 지속적으로 실행·유지하는 설정

1. ECS → `nexus-cluster` → `서비스 생성`
2. 설정:
   - 컴퓨팅 옵션: `Launch type` → `FARGATE`
   - 태스크 정의: `nexus-core-task` 선택
   - 서비스 이름: `nexus-core-service`
   - 원하는 태스크 수: `1`
3. **네트워킹**:
   - VPC: 기본 VPC 선택
   - 서브넷: 2개 이상 선택 (가용 영역 분산)
   - 보안 그룹: `새 보안 그룹 생성`
     - 인바운드 규칙: TCP `8080` 포트 허용 (소스: `0.0.0.0/0`)
   - 퍼블릭 IP 자동 할당: `켜짐`
4. **로드 밸런서** (선택 사항, 도메인 연결 시 필요):
   - `Application Load Balancer` 생성
   - 리스너: HTTP(80), HTTPS(443)
   - 대상 그룹: 포트 `8080`으로 포워딩
5. `생성` 완료

서비스가 실행되면 태스크 탭에서 퍼블릭 IP를 확인할 수 있습니다.

---

## Phase 4 — GitHub Actions CI/CD 연결

### 4-1. GitHub Secrets 등록

GitHub 저장소 → `Settings` → `Secrets and variables` → `Actions`

추가할 Secrets:
| 이름 | 값 |
|------|-----|
| `AWS_ACCESS_KEY_ID` | Phase 1-2에서 생성한 키 |
| `AWS_SECRET_ACCESS_KEY` | Phase 1-2에서 생성한 시크릿 |

기존의 `GCP_CREDENTIALS` 시크릿은 이관 완료 후 삭제합니다.

### 4-2. 워크플로우 파일 수정

**파일**: `.github/workflows/deploy-backend.yml`

아래 내용으로 전체 교체:

```yaml
name: Deploy Backend to AWS ECS

on:
  push:
    branches: [main]
    paths:
      - "backend/**"

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: nexus-core
  ECS_SERVICE: nexus-core-service
  ECS_CLUSTER: nexus-cluster
  CONTAINER_NAME: nexus-core

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG ./backend
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition nexus-core-task \
            --query taskDefinition > task-definition.json

      - name: Update ECS task definition with new image
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ steps.build-image.outputs.image }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

---

## Phase 5 — S3로 파일 스토리지 이관

### 5-1. S3 버킷 생성

1. AWS 콘솔 → `S3` → `버킷 만들기`
2. 설정:
   - 버킷 이름: `nexus-core-uploads` (전 세계 고유해야 함, 안되면 `nexus-core-uploads-prod` 등)
   - 리전: `ap-northeast-2` (서울)
   - 퍼블릭 액세스 차단: **모두 해제** (파일을 공개적으로 서빙해야 하는 경우)
3. 버킷 생성 완료

### 5-2. 버킷 정책 설정 (퍼블릭 읽기 허용)

업로드한 파일을 누구나 볼 수 있게 설정합니다.

1. 생성된 버킷 클릭 → `권한` 탭 → `버킷 정책` → `편집`
2. 아래 JSON 입력 (`nexus-core-uploads`를 실제 버킷 이름으로 교체):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::nexus-core-uploads/*"
    }
  ]
}
```

### 5-3. Backend에 S3 StorageProvider 추가

**신규 파일**: `backend/app/services/storage/s3.py`

```python
import boto3
from botocore.exceptions import ClientError
import uuid
from app.core.config import settings
from .base import StorageProvider  # 기존 base 인터페이스 사용


class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        )
        self.bucket = settings.AWS_S3_BUCKET_NAME

    async def upload(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        key = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return key

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    async def get_public_url(self, key: str) -> str:
        base_url = settings.AWS_S3_PUBLIC_URL or \
            f"https://{self.bucket}.s3.{settings.AWS_S3_REGION}.amazonaws.com"
        return f"{base_url}/{key}"
```

**파일 수정**: `backend/app/services/storage/factory.py`에 s3 케이스 추가:

```python
# 기존 코드에 추가
elif provider == "s3":
    from .s3 import S3StorageProvider
    return S3StorageProvider()
```

**파일 수정**: `backend/app/core/config.py`에 S3 환경변수 추가:

```python
# S3 Storage
AWS_S3_BUCKET_NAME: str | None = None
AWS_S3_REGION: str = "ap-northeast-2"
AWS_S3_PUBLIC_URL: str | None = None
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY는 boto3가 환경변수에서 자동 읽음
```

### 5-4. 환경변수 변경

ECS 태스크 정의에서 환경변수 업데이트:

```
STORAGE_PROVIDER=s3
AWS_S3_BUCKET_NAME=nexus-core-uploads
AWS_S3_REGION=ap-northeast-2
```

### 5-5. 기존 파일 마이그레이션

Supabase Storage나 R2에 있는 기존 파일들을 S3로 옮겨야 합니다.

```bash
# AWS CLI로 S3에 파일 업로드 (로컬에 다운로드한 파일 기준)
aws s3 cp ./downloaded-files/ s3://nexus-core-uploads/ --recursive
```

---

## Phase 6 — Frontend 이관 (Vercel → AWS Amplify)

AWS Amplify는 Vercel과 거의 동일한 경험을 제공합니다. Next.js SSR도 지원합니다.

### 6-1. Amplify 앱 생성

1. AWS 콘솔 → `AWS Amplify` → `새 앱 생성`
2. `GitHub` 선택 → GitHub 계정 연결
3. 저장소 선택: `nexus-core`
4. 브랜치: `main`
5. **빌드 설정** (frontend-client 기준):
   - 앱 이름: `nexus-core-client`
   - 루트 디렉토리: `frontend-client`
   - 빌드 명령어: `pnpm build`
   - 출력 디렉토리: `.next`
6. **환경 변수 추가**:
   | 키 | 값 |
   |----|-----|
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Anon Key |
   | `NEXT_PUBLIC_API_URL` | ECS 서비스 URL (Phase 3에서 확인한 IP 또는 도메인) |
7. `저장 및 배포`

Admin 프론트엔드도 동일하게 반복 (`frontend-admin`).

### 6-2. next.config.ts 수정

배포 후 Amplify URL을 확인하고 아래 파일들을 수정합니다.

**파일**: `frontend-client/next.config.ts`

```ts
// 변경 전 (Cloud Run URL 하드코딩 제거)
"nexus-core-58481128769.asia-northeast3.run.app";

// 변경 후 (환경변수로 처리)
process.env.NEXT_PUBLIC_API_HOST ||
  "your-ecs-alb-url.ap-northeast-2.elb.amazonaws.com";
```

이미지 도메인도 업데이트:

```ts
remotePatterns: [
  // 기존 supabase, r2 항목 유지 (S3 전환 전까지)
  // S3 전환 후 추가:
  {
    protocol: "https",
    hostname: "nexus-core-uploads.s3.ap-northeast-2.amazonaws.com",
  },
];
```

### 6-3. CORS 설정 업데이트

ECS 환경변수에서 CORS_ORIGINS 업데이트:

```
# 이전
CORS_ORIGINS=https://nexus-core-admin.vercel.app,https://nexus-core-six.vercel.app,...

# 이후 (Amplify 앱 URL로 교체)
CORS_ORIGINS=https://main.xxxxxxxx.amplifyapp.com,https://main.yyyyyyyy.amplifyapp.com,...
```

> Amplify에서 커스텀 도메인을 연결하면 그 도메인을 사용하면 됩니다.

---

## Phase 7 (선택) — RDS + Cognito 이관

> 이 단계는 Supabase를 완전히 탈출하고 싶을 때만 진행합니다.
> 작업량이 매우 많으므로 별도 스프린트로 계획하는 것을 권장합니다.

### 7-1. RDS PostgreSQL 생성

1. AWS 콘솔 → `RDS` → `데이터베이스 생성`
2. 설정:
   - 엔진: `PostgreSQL`
   - 버전: `16.x`
   - 템플릿: `프리 티어` (개발) / `프로덕션` (운영)
   - 인스턴스 이름: `nexus-core-db`
   - 마스터 사용자: `postgres`
   - 암호: 안전한 암호 설정
   - 인스턴스 클래스: `db.t3.micro` (소규모)
   - 스토리지: `20 GB`
   - VPC: ECS와 동일한 VPC 선택 (중요!)
3. `데이터베이스 생성`

> **pgvector 설치**: RDS에 접속 후 `CREATE EXTENSION vector;` 실행 필요

### 7-2. 데이터 마이그레이션

```bash
# Supabase에서 데이터 덤프
pg_dump "postgresql://postgres.oxhhzpzzaewzwqoiffjp:password@aws-1-ap-south-1.pooler.supabase.com:6543/postgres" \
  -n nexus_core \
  -f nexus_core_dump.sql

# RDS에 복원
psql "postgresql://postgres:password@your-rds-endpoint.ap-northeast-2.rds.amazonaws.com:5432/postgres" \
  -f nexus_core_dump.sql
```

### 7-3. Cognito 설정 (Supabase Auth 대체)

1. AWS 콘솔 → `Cognito` → `사용자 풀 생성`
2. 로그인 옵션: `이메일` 선택
3. 앱 클라이언트 생성
4. **JWKS URL 확인**: `https://cognito-idp.ap-northeast-2.amazonaws.com/{user_pool_id}/.well-known/jwks.json`
5. ECS 환경변수 업데이트:
   ```
   AUTH_JWKS_URL=https://cognito-idp.ap-northeast-2.amazonaws.com/{user_pool_id}/.well-known/jwks.json
   ```
6. Frontend에서 Supabase SDK를 `aws-amplify` SDK로 교체 (별도 작업)

---

## 비용 예상 (서울 리전 기준, 월 기준)

| 서비스             | 스펙                      | 예상 비용              |
| ------------------ | ------------------------- | ---------------------- |
| ECS Fargate        | 0.5 vCPU / 1GB, 상시 실행 | ~$15–25                |
| ECR                | 이미지 저장 1GB           | ~$0.1                  |
| S3                 | 저장 10GB + 요청          | ~$1–3                  |
| ALB                | 로드밸런서 1개            | ~$20                   |
| Amplify            | Frontend 빌드/호스팅      | ~$0 (무료 티어) / $1–5 |
| RDS (선택)         | db.t3.micro               | ~$15–25                |
| **합계 (DB 제외)** |                           | **~$36–53/월**         |

> Cloud Run은 요청이 없으면 0원이지만, ECS Fargate는 상시 실행 시 고정 비용이 발생합니다.
> 트래픽이 적다면 **EC2 t3.small (~$17/월)** 에 docker-compose로 실행하는 것이 더 저렴할 수 있습니다.

---

## 문제 해결 (Troubleshooting)

### ECS 태스크가 시작되지 않는 경우

1. ECS → 클러스터 → 서비스 → `태스크` 탭에서 실패한 태스크 클릭
2. `로그` 탭에서 에러 메시지 확인
3. 주요 원인:
   - 환경변수 누락
   - ECR 이미지 Pull 실패 (IAM 권한 확인)
   - 포트 설정 오류

### 컨테이너에 접속이 안 되는 경우

1. ECS 서비스의 보안 그룹에서 8080 포트 인바운드 허용 확인
2. 태스크에 퍼블릭 IP가 할당되었는지 확인

### GitHub Actions 배포 실패

1. AWS Secrets 이름 오타 확인 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. IAM 사용자 권한 확인 (ECR, ECS 권한)
3. ECR 리포지토리 이름과 환경변수 `ECR_REPOSITORY` 일치 여부 확인

---

## 참고 문서

- [AWS ECS 공식 문서](https://docs.aws.amazon.com/ecs/)
- [GitHub Actions - AWS ECS 배포](https://github.com/aws-actions/amazon-ecs-deploy-task-definition)
- [AWS Amplify Next.js 가이드](https://docs.amplify.aws/nextjs/)
- [전략 분석 문서](../architecture/aws-migration.md)
