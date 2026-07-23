# 체크리스트 — Clerk 제거 · 하나로 단독 인증

계획서 [hanaro-auth-migration.md](./hanaro-auth-migration.md) · 진행하며 체크한다.

## Phase 0 — 준비
- [ ] IT팀에 v2 발급 키 요청 (현재 키는 12자 = v1용, 규격서 §3은 20자 이상 요구)
- [ ] v2 키 수령 후 `OFFICIAL_CHECK_KEY` 교체 → **검증**: 서버 로그에서 `invalid_key` 소멸
- [x] 기존 유저 성격 확인 → clerk 15명 전부 테스트 계정, 삭제 가능
- [ ] 하나로 장애 시 관리자 비상 계정을 둘지 결정 (미결 #1)

## Phase 1 — 백엔드 인증 엔드포인트 ✅ 완료 (2026-07-23)
- [x] `app/core/hanaro.py` — v2 호출 (`keyValue`/`userid`/`password`, form-urlencoded, httpx, timeout 8s)
- [x] 응답 매핑 — `authenticated`/`isOfficial`/`error`(`invalid_key`·`missing_parameter`·`rate_limited`)
- [x] 429는 그대로 전파 (규격서 §5 — 아이디당 실패 15회, 5분 후 자동 해제)
- [x] `app/api/v1/endpoints/auth.py` — `POST /auth/hanaro/login`
- [x] 유저 upsert — `clerk_user_id='hanaro:{userid}'`, email=`{userid}@hanaro.sso`, `is_official` 반영
- [x] HS256 JWT 발급 (`sub`·`email`·`provider`·`is_official`·`exp` 12h)
- [x] `deps.py` — alg=HS256 이면 `AUTH_JWT_SECRET` 검증, 그 외는 기존 JWKS 경로
- [x] `config.py` — `AUTH_JWT_SECRET`·`OFFICIAL_CHECK_KEY`·`OFFICIAL_CHECK_URL` 추가
- [x] alembic head 정리 — `8f3d7a1c9e5b` 를 main head 뒤로 재배치, 라이브 적용 완료
- [x] **검증**: 로그인 200 → JWT 발급 → `/users/me` 200 (`is_official=true`)
- [x] **검증**: 잘못된 자격 401 · 토큰 없음 401 · 변조 토큰 401
- [ ] **미검증**: 기존 Clerk 토큰(JWKS 경로) 회귀 — alg 라우팅이 401을 주는 것까지만 확인했고
      실제 Clerk 세션으로는 확인하지 못했다. Phase 2에서 Clerk 이 걷히면 무의미해진다.

## Phase 2 — 프론트 세션 레이어
- [ ] `/api/auth/login` — 백엔드 호출 후 JWT를 httpOnly·Secure·SameSite=Lax 쿠키로 저장
- [ ] `/api/auth/session` — 쿠키의 토큰 반환 (api.ts getter용)
- [ ] `/api/auth/logout` — 쿠키 삭제
- [ ] `middleware.ts` — `clerkMiddleware` 제거, 쿠키 유무로 `/chat`·`/mypage` 보호
- [ ] `api.ts` — 토큰 getter만 교체, 인터셉터·401 재시도 구조는 유지
- [ ] `api-server.ts` — `auth()` → `cookies()`
- [ ] `useAuthStore` — Clerk 훅 제거, 표시 이름은 userid 기반 (소비처 `Header`·`UserMenu` 2곳)
- [ ] `LogoutButton` — `useClerk().signOut` → `/api/auth/logout`
- [ ] **검증**: 로그인 → `/chat` 진입 → 백엔드 API 200 → 로그아웃 → `/chat` 차단

## Phase 3 — Clerk 제거
- [ ] `layout.tsx` `ClerkProvider` 제거
- [ ] `sso-callback/` · `SignupForm.tsx` · `/signup` 삭제
- [ ] `LoginForm` 이메일 탭 · OAuth(Google/Apple) 버튼 삭제 → 하나로 폼 단독
- [ ] `lib/hanaro.ts` · `/api/auth/hanaro/route.ts` 삭제 (백엔드로 이관됨)
- [ ] `npm rm @clerk/nextjs` · Clerk env 4종 정리 (`.env.example` 포함)
- [ ] **검증**: `grep -ri clerk frontend-client/src` 0건
- [ ] **검증**: tsc 0 · eslint 0 · `npm run build` 성공

## Phase 4 — 기존 테스트 유저 정리
- [ ] Neon 스냅샷/백업 확보
- [ ] 삭제 대상 재확인 — `provider='clerk'` 15명 + 딸린 `chat_sessions` 721행
- [ ] **`provider='kakao'` 3명 보존 확인** (카카오 봇 실사용자)
- [ ] 사용자 승인 후 삭제 실행
- [ ] **검증**: `users` 3행(kakao)만 잔존 · 카카오 봇 응답 정상

## Phase 5 — 배포 검증
- [ ] `OFFICIAL_CHECK_URL`을 v2로 전환
- [ ] 호스트 env 설정 (`OFFICIAL_CHECK_KEY`·`AUTH_JWT_SECRET`)
- [ ] **검증**: 라이브에서 공직자 계정 1건 → `is_official=true` 저장 확인
- [ ] **검증**: 라이브에서 비공직자 계정 1건 → `is_official=false` 저장 확인
- [ ] PR #40 설명 갱신 (Clerk 브리지 → 하나로 단독으로 범위 변경)

## 선행 정리 (현재 미커밋 4건)
- [ ] `LoginForm.tsx` 401/그 외 에러 문구 분리 — 유지, 커밋
- [ ] `.env.example` 하나로 v2 블록 정리 — 유지, 커밋
- [ ] `lib/hanaro.ts` `invalid_key` 진단 로그 — 백엔드 이식 시 함께 이관
- [ ] `route.ts` Clerk 에러 펼침 로그 — Phase 3에서 파일째 삭제
