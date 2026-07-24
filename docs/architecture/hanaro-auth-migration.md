# Clerk 제거 · 하나로 SSO 단독 인증 전환 계획

작성일 2026-07-23 · 대상 브랜치 `feat/hanaro-sso` (PR #40 확장)

## 1. 목표

Clerk을 완전히 걷어내고 하나로 SSO를 **유일한 인증 수단**으로 삼는다. 이메일·소셜(Google/Apple) 로그인과 회원가입 경로는 폐기한다.

## 2. 현황 실측 (2026-07-23)

| 항목 | 값 | 출처 |
|---|---|---|
| 라이브 유저 | 18명 (clerk 15 · kakao 3), 전원 활성 | Neon `users` 집계 |
| 사용자 데이터 | `chat_sessions` 721행 (clerk 15명) · 3행 (kakao 3명) | Neon 집계 |
| clerk 유저 15명 성격 | **전부 테스트 계정 — 삭제 가능** (이관 불필요) | 사용자 확인 2026-07-23 |
| Clerk 참조 파일 | frontend-client 12개 | `grep -rli clerk` |
| `useAuthStore` 소비처 | 2곳 (`Header.tsx`·`UserMenu.tsx`) | grep |
| `serverFetch` 소비처 | 2곳 | grep |
| frontend-admin | Clerk **미사용** | grep (0건) |
| 카카오 봇 | HMAC 헤더 시크릿 인증 — Clerk **무관** | `endpoints/kakao.py:36` |

### 백엔드는 이미 플랫폼 독립적이다

`app/api/deps.py`는 Clerk SDK를 쓰지 않고 JWKS 기반 표준 JWT 검증만 한다. 파일 docstring에도 "인증 플랫폼(Clerk, Auth0 등)에 독립적인 구조"라고 명시돼 있다. 백엔드가 요구하는 것은 JWT payload의 `sub`·`email`(필수), `provider`·`avatar_url`·`is_official`(선택)뿐이다.

`clerk_user_id` 컬럼도 이름만 Clerk이다. 카카오 봇이 이미 이 컬럼을 `kakao:{bot_id}:{user_key}` 형식으로 재활용 중이므로(`crud_user.py:114`), 하나로는 `hanaro:{userid}`를 넣으면 된다. **스키마 변경 불필요.**

## 3. 설계

### 3.1 인증 소유권 — 백엔드가 갖는다

로그인 검증과 토큰 발급을 백엔드로 옮긴다.

```
브라우저 ──POST /api/v1/auth/hanaro/login (id·pw)──▶ FastAPI
                                                      │ ① 하나로 officialLoginCheck2 호출 (서버↔서버)
                                                      │ ② users upsert (sub=hanaro:{userid}, is_official)
                                                      │ ③ HS256 JWT 발급
                                                      ▼
브라우저 ◀──Next 서버 라우트가 httpOnly 쿠키로 저장──── JWT
```

**왜 프론트가 아니라 백엔드인가.**
- 하나로 발급 키가 백엔드 한 곳에만 존재한다 (Vercel 프론트에 비밀이 남지 않음)
- 규격서 §8 "서버↔서버 통신 권장" 충족
- JWT 서명 시크릿이 두 곳에 복제되지 않는다
- admin·향후 클라이언트가 같은 인증 엔드포인트를 재사용할 수 있다

### 3.2 세션 — httpOnly 쿠키 + 기존 인터셉터 구조 유지

- 발급된 JWT는 Next 서버 라우트가 `httpOnly`·`Secure`·`SameSite=Lax` 쿠키에 저장한다 (브라우저 JS에 토큰 미노출)
- `api.ts`의 인터셉터 구조(cached/fresh getter, 401 재시도)는 **그대로 둔다.** 토큰 getter만 Clerk `getToken` → Next 경량 라우트 `/api/auth/session` 호출로 교체
- `middleware.ts`는 쿠키 존재 여부로 `/chat`·`/mypage`를 보호
- 만료는 우선 단순하게 간다 — exp 12시간, 만료 시 재로그인. refresh 토큰은 도입하지 않는다 (하나로 비밀번호를 다시 받아야 하므로 무의미)

### 3.3 이메일 문제

규격서 §8에 따라 하나로는 개인정보를 반환하지 않는다 — `authenticated`·`isOfficial` boolean뿐이다. 그런데 `deps.py:118`은 email이 없으면 401로 막고 `UserMenu`도 email을 표시한다.

→ **합성 이메일 `{userid}@hanaro.sso`를 쓴다.** DB의 email unique 제약을 만족시키는 게 목적이고, 화면 표시는 userid를 쓰도록 `useAuthStore`를 바꾼다. (Clerk이 `@hanaro.local`을 422로 거부했던 문제는 Clerk이 사라지면서 함께 없어진다 — 우리 DB는 email 형식을 검증하지 않는다.)

### 3.4 폐기 대상

`SignupForm.tsx` · `/signup` · `sso-callback/` · OAuth 버튼 · `@clerk/nextjs` 패키지 · Clerk env 4종 · `LoginForm`의 이메일 탭

## 4. 단계별 계획

각 단계는 검증 기준을 통과해야 다음으로 넘어간다.

### Phase 0 — 준비
- v2 발급 키 확보 (IT팀 김정래) · 기존 15명의 하나로 아이디 수집
- **검증**: 키로 v2 호출 시 `invalid_key`가 사라짐

> 키 확보 전에도 Phase 1~3 개발은 가능하다. 현재 키가 **v1 주소에서는 정상 동작**하므로 개발·검증은 v1으로 하고, 배포 직전 URL만 v2로 바꾼다. 규격서 §7이 "URL과 keyValue 값 2가지만 교체하면 그대로 동작"이라고 보장한다.

### Phase 1 — 백엔드 인증 엔드포인트
- `app/core/hanaro.py` — 하나로 v2 호출 (프론트 `lib/hanaro.ts`의 `checkOfficial` 이식, httpx 사용)
- `app/api/v1/endpoints/auth.py` — `POST /auth/hanaro/login`, 유저 upsert + JWT 발급
- `crud_user.get_or_create_by_clerk_id`에 하나로 경로 재사용 (`sub=hanaro:{userid}`)
- `deps.py` — `AUTH_JWT_SECRET`이 있으면 HS256 대칭키 검증, 없으면 기존 JWKS (알고리즘 목록에 HS256이 이미 있음)
- **검증**: curl로 로그인 → JWT 수신 → 그 JWT로 기존 보호 API 호출 200

### Phase 2 — 프론트 세션 레이어
- `/api/auth/login`(쿠키 세팅) · `/api/auth/session`(토큰 반환) · `/api/auth/logout`(쿠키 삭제) Next 라우트
- `middleware.ts` 쿠키 기반으로 재작성
- `api.ts` 토큰 getter 교체 (인터셉터 구조는 유지)
- `api-server.ts` `auth()` → `cookies()` 로 교체
- `useAuthStore` Clerk 훅 제거, `LogoutButton` 교체
- **검증**: 로그인 → `/chat` 진입 → 백엔드 API 200 → 로그아웃 → `/chat` 접근 차단

### Phase 3 — Clerk 제거
- `layout.tsx` `ClerkProvider` 제거 · `sso-callback`·`SignupForm`·`/signup` 삭제 · 이메일/OAuth 탭 삭제
- `npm rm @clerk/nextjs` · Clerk env 정리
- **검증**: `grep -ri clerk frontend-client/src` 0건 · tsc 0 · eslint 0 · 빌드 성공

### Phase 4 — 기존 테스트 유저 정리
clerk 유저 15명은 **전부 테스트 계정으로 확인됨(2026-07-23 확인) — 이관 불필요, 삭제 가능.**
- 하나로는 email을 주지 않아 자동 매칭이 불가능한데, 삭제로 결정되면서 이 문제 자체가 사라졌다
- `provider='clerk'` 15명과 딸린 `chat_sessions` 721행 삭제. **`provider='kakao'` 3명은 반드시 보존** (카카오 봇 실사용자, Clerk 무관)
- 삭제는 되돌릴 수 없으므로 실행 전 Neon 백업/스냅샷 확보 후 사용자 승인을 받고 실행한다
- **검증**: 삭제 후 `users` 3행(kakao)만 남음 · 카카오 봇 응답 정상

### Phase 5 — 배포 검증
- `OFFICIAL_CHECK_URL`을 v2로 전환 · 호스트 env 설정
- **검증**: 라이브에서 공직자/비공직자 계정 각 1건 로그인, `is_official` 값 확인

## 5. 리스크

| 리스크 | 영향 | 대응 |
|---|---|---|
| v2 키 미확보 | 배포 불가 | 개발은 v1으로 진행, 배포 직전 URL 교체 |
| 카카오 유저 3명 오삭제 | 봇 실사용자 유실 | Phase 4 삭제 시 `provider='clerk'` 조건 필수, 백업 선행 |
| 하나로 API 장애 | 로그인 전면 중단 (단독 인증이라 우회 경로 없음) | 관리자용 비상 계정 필요 여부 결정 |
| rate limit (아이디당 실패 15회 → 429) | 테스트 중 계정 잠김 | 실패 반복 금지, 5분 대기 |

## 6. 미결 사항

1. 하나로 장애 시 대비할 관리자 비상 계정을 둘 것인가
2. `clerk_user_id` 컬럼명을 `external_user_id` 등으로 rename 할 것인가 (기능 무관, 가독성만)
3. `is_official`을 실제 권한 분기에 쓸 것인가, 저장만 할 것인가
