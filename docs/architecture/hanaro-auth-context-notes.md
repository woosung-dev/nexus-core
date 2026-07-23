# 컨텍스트 노트 — Clerk 제거 · 하나로 단독 인증

작업 중 내린 결정과 그 근거를 계속 덧붙인다. 다음 세션이 재추론 없이 이어받기 위한 기록.

## 2026-07-23

### 하나로 v2가 거부한 이유 — 코드가 아니라 키
v2(`officialLoginCheck2`) 호출이 500으로 실패해 원인을 추적했다. 서버 로그에 업스트림 에러코드를 남기도록 하고 나서야 `invalid_key`임이 드러났다.

- 업스트림이 `missing_parameter`가 아니라 `invalid_key`를 반환했다 → 파라미터 이름(`keyValue`/`userid`/`password`)과 form-urlencoded 형식은 v2가 정상 파싱했다는 뜻. **요청 형식은 이미 규격에 맞다.**
- 같은 키로 v1(`officialLoginCheck`)을 호출하면 `kjl51555` 계정이 정상 인증된다 → 계정도 코드도 문제없다.
- 보유 키는 12자. 규격서 §3의 v2 키 조건은 "20자 이상 무작위 문자열"이고, §7 대비표는 구버전 키를 "고정 문자열"로 적는다 → **받은 키는 v1용이다.**

**결론**: v2 전환에 필요한 코드 변경은 없다. 규격서 §7이 "URL과 keyValue 값 2가지만 교체하면 그대로 동작"이라고 보장한다. IT팀에 v2 키를 요청하는 것 외에 할 일이 없다.

**활용**: 키를 기다리는 동안 개발·검증은 v1 주소로 진행할 수 있다. 배포 직전 URL만 v2로 바꾼다.

### 요청이 새는지 의심 → 아님 (추적 완료)
500이 라우팅 문제일 가능성을 배제했다.
- `next.config` rewrites는 `/api/v1/*`·`/static/uploads/*` 둘뿐 — `/api/auth/hanaro`는 매칭되지 않는다
- 응답 헤더 `x-middleware-rewrite: /api/auth/hanaro`는 **자기 자신으로의 rewrite**로, Clerk 미들웨어가 통과시키며 붙이는 정상 헤더다 (같이 오는 `x-clerk-auth-status: signed-out`은 보호 대상 라우트가 아니라는 뜻)
- 응답 본문 `{"error":"server_config"}`는 우리 Next 라우트의 형식이다. FastAPI였다면 `{"detail": ...}`가 왔을 것 → 백엔드(8080)로 새지 않았다

### 에러 문구·사유 뭉갬 — 같은 계열의 버그 2건
1. `LoginForm.tsx`가 `!res.ok`를 전부 "아이디 또는 비밀번호가 올바르지 않습니다"로 표시했다. 키 미설정(500)·업스트림 장애(502)까지 자격증명 오류로 오진된다. PR #40 설명의 "초기 테스트 계정 인증 실패"도 실은 이 오진이었을 가능성이 크다. → 401만 자격증명 문구, 나머지는 서버 문제 문구로 분리했다.
2. `checkOfficial`의 `server_config` 한 값이 "우리 서버에 키가 없음"과 "하나로가 키를 거부함"을 뭉갠다. 성격이 다르고 대응 주체도 다르다(우리 vs IT팀). 백엔드 이관 시 `upstream_key_rejected`를 별도 사유로 분리한다.

**교훈**: 외부 연동 실패는 사유를 뭉개는 순간 진단 불가능해진다. 로그에 업스트림 에러코드를 남기는 한 줄이 이번 원인 규명의 전부였다.

### 인증 소유권을 백엔드로 옮기는 이유
프론트에서 JWT를 발급하는 대안(Next가 서명 → 쿠키)도 가능하지만 백엔드 소유로 정했다.
- 하나로 발급 키가 백엔드 한 곳에만 존재하게 된다 (Vercel 프론트에 비밀이 남지 않음)
- 규격서 §8이 서버↔서버 통신을 권장한다
- JWT 서명 시크릿이 프론트·백엔드 양쪽에 복제되지 않는다
- `deps.py`가 이미 `HS256`을 허용 알고리즘에 포함하고 있어 백엔드 변경이 작다

### 백엔드는 손댈 게 거의 없다 (다행)
`deps.py`는 Clerk SDK가 아니라 JWKS 기반 표준 JWT 검증만 한다. docstring에도 "인증 플랫폼에 독립적인 구조"라고 적혀 있다. `clerk_user_id` 컬럼도 이름만 Clerk이고, **카카오 봇이 이미 `kakao:{bot_id}:{user_key}` 형식으로 같은 컬럼을 재활용 중**이다. 하나로는 `hanaro:{userid}`를 넣으면 되므로 스키마 변경이 없다.

컬럼명 rename은 기능과 무관해 보류했다 (미결 #2).

### 하나로는 이메일을 주지 않는다
규격서 §8 — 응답은 `authenticated`·`isOfficial` boolean뿐이고 개인정보를 포함하지 않는다. 그런데 `deps.py:118`은 email이 없으면 401이고 `UserMenu`도 email을 표시한다.

→ 합성 이메일 `{userid}@hanaro.sso`를 쓰기로 했다. DB의 email unique 제약 충족이 목적이고, 화면 표시는 userid를 쓰도록 `useAuthStore`를 바꾼다.

참고로 Clerk은 `{userid}@hanaro.local`을 422 `form_param_format_invalid`로 거부했다("Email address must be a valid email address"). Clerk 제거와 함께 이 제약도 사라진다 — 우리 DB는 email 형식을 검증하지 않는다.

### 기존 유저 — 이관에서 삭제로
처음엔 최대 리스크로 봤다. 라이브에 clerk 유저 15명과 `chat_sessions` 721행이 있고, 하나로가 email을 주지 않아 자동 매칭이 원천 불가능했기 때문이다.

사용자 확인 결과 **15명 전부 테스트 계정**이라 삭제하기로 했다. 매핑 문제 자체가 소멸했고 Phase 4가 이관에서 정리로 축소됐다.

**주의**: `provider='kakao'` 3명은 카카오 봇 실사용자다. 삭제 조건에 `provider='clerk'`를 반드시 넣어야 한다. 카카오 경로는 HMAC 헤더 시크릿 인증(`endpoints/kakao.py:36`)이라 Clerk과 무관하고, 이번 작업의 영향을 받지 않는다.

### 영향 없음을 확인한 것들
- `frontend-admin` — Clerk 참조 0건
- 카카오 봇 — HMAC 인증, Clerk 무관
- `useAuthStore` 소비처가 2곳(`Header`·`UserMenu`)뿐이라 훅 내부만 갈아끼우면 컴포넌트는 안 건드려도 된다. 이 추상화가 있어서 프론트 작업량이 예상보다 작다.

### Phase 1 결과 — 하나로 연동 실증 성공 (2026-07-23)
백엔드 로그인 엔드포인트로 `kjl51555` 로그인이 성공했다. **`is_official=true`** — 공직자 판별까지 실제로 동작한다. 발급된 HS256 JWT 로 `/users/me` 가 200을 반환해 `deps.py` 의 새 검증 경로도 확인됐다.

### 라이브 DB 스키마가 브랜치보다 앞서 있었다
로그인 500의 실제 원인은 `column users.is_official does not exist` 였다. PR #40 의 마이그레이션이 로컬에만 적용돼 있었고 Neon 에는 없었다.

더 큰 문제가 딸려 나왔다 — 브랜치가 `e7d9c3b1a5f2` 에서 갈라졌는데 그 사이 main 이 `f8a4c2d9e1b7`(지침 빌더)까지 나아가 있었다. 두 마이그레이션이 같은 부모를 가리켜 **alembic head 가 2개**가 되는 상태였다. PR #40 본문이 예고한 그 상황이다.

→ main 을 브랜치에 병합하고 `8f3d7a1c9e5b.down_revision` 을 `f8a4c2d9e1b7` 로 옮겨 선형화했다. 라이브가 이 마이그레이션을 적용한 적이 없어 재배치가 안전했다. 이후 Neon 에 `alembic upgrade head` 로 컬럼 1개만 추가 적용(사용자 승인).

**교훈**: 브랜치가 오래 떠 있으면 마이그레이션 부모가 낡는다. 라이브 적용 전에 `alembic heads` 가 1개인지부터 본다.

### 개발 중에는 v1 주소를 쓴다
`backend/.env` 의 `OFFICIAL_CHECK_URL` 은 v1(`officialLoginCheck`)로 두었다. 보유 키가 v1 전용이라 v2 주소로는 `invalid_key` 가 나기 때문이다. v2 키를 받으면 URL 만 `officialLoginCheck2` 로 바꾸면 된다 — 규격서 §7 이 요청·응답 형식 동일을 보장한다.

### 라이브 DB에 테스트 유저 1건 생성됨
검증 과정에서 Neon 에 `hanaro:kjl51555`(users.id=21) 가 생성됐다. Phase 4 정리 대상에 포함한다.
