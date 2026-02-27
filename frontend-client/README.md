# Nexus Core - Frontend Client

이 디렉토리는 **Nexus Core** 프로젝트의 사용자용 프론트엔드(Client) 애플리케이션 코드를 포함하고 있습니다.
AI 협업 및 Vibe Coding에 최적화된 엄격한 규칙과 최신 프론트엔드 기술 스택을 바탕으로 구축되었습니다.

---

## 🏗️ 기술 스택 (Tech Stack)

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript (Strict Mode)
- **Package Manager:** `pnpm`
- **Styling:** Tailwind CSS + `shadcn/ui` (Radix UI 기반)
- **State Management:**
  - **Server State:** React Query (`@tanstack/react-query`)
  - **Client State (UI):** Zustand
- **API Client:** Axios (Custom Instance with Interceptors)
- **Authentication:** Supabase Auth (SSR 연동)

---

## 🚀 시작하기 (Getting Started)

### 1. 환경 변수 설정

루트 디렉토리에 있는 `.env.example` 파일을 복사하여 `.env.local` 파일을 생성하고 적절한 값을 채워 넣습니다.

```bash
cp .env.example .env.local
```

**.env.local 필수 항목:**

- `NEXT_PUBLIC_SUPABASE_URL`: Supabase 프로젝트 URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase 익명 API 키
- `NEXT_PUBLIC_API_URL`: 연동할 백엔드(FastAPI) 주소 (로컬 시 기본값: `http://localhost:8080/api/v1`)

### 2. 패키지 설치

`pnpm`을 사용하여 의존성을 설치합니다.

```bash
pnpm install
```

### 3. 개발 서버 실행

```bash
pnpm dev
```

터미널에 표시된 `http://localhost:3000` 으로 접속하여 앱을 확인합니다.

---

## 📐 핵심 개발 규칙 (Global Constraints)

프론트엔드 작업 시 다음 규칙을 항상 최우선으로 준수해야 합니다:

1.  **Next.js App Router 최적화**
    - **RSC Default:** 기본적으로 모든 컴포넌트는 서버 컴포넌트(Server Component)로 작성합니다.
    - **Client Boundary 최소화:** `useState`, `useEffect` 등 클라이언트 훅이 필요한 경우에만 `"use client"`를 명시하고, 클라이언트 컴포넌트를 트리의 말단(Leaf Node)으로 분리합니다.

2.  **상태 관리의 철저한 분리**
    - **서버 상태 (API 데이터):** 무조건 `React Query`에 위임하여 페칭 및 캐싱을 처리합니다.
    - **자사 클라이언트 상태 (UI 전역 상태):** 모달 열림 상태, 테마, 로컬 입력값 등은 `Zustand`로 관리합니다.

3.  **UI / UX 일관성**
    - 모듈 CSS나 개별 CSS 작성은 극도로 지양하며, **Tailwind CSS** 유틸리티 클래스를 사용합니다.
    - 기본 UI 컴포넌트는 `shadcn/ui`를 활용하여 일관된 디자인 시스템을 구축합니다.
    - 모든 타입 추론은 `any`를 엄격히 금지하며, TS의 `strict` 모드 하에 작성됩니다.
