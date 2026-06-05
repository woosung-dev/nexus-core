<!-- 카카오톡 채널 챗봇 연동 설계 명세 (브레인스토밍 산출물) -->

# 카카오톡 채널 챗봇 연동 — 설계 명세 (Design Spec)

> 작성일: 2026-06-05 · 브랜치: `feat/kakao-channel-integration`
> 선행 자료: 내부 가이드 `docs/guides/kakao-channel-integration.md`, 가능성 검토 플랜 `~/.claude/plans/wiggly-meandering-trinket.md`(codex 리뷰 반영본)

## 1. 목적 / 배경

기존 nexus-core 챗봇 서비스의 봇을, 사용자가 **카카오톡 채널을 친구 추가만 하면 별도 앱 없이 Q&A** 할 수 있게 확장한다. 봇 응답 로직(`ChatService.process_chat_request`)은 재사용하고, 카카오 ↔ 우리 서비스 사이의 어댑터 레이어를 새로 만든다.

핵심 제약상 **유일하게 성립하는 방식은 "스킬 서버 + 콜백 비동기 응답"** 이다. 카카오 스킬 서버는 5초 안에 응답해야 하는데 우리 LLM은 ~30초가 걸리므로, 5초 안에 `useCallback:true`만 반환하고 실제 답변은 백그라운드에서 만들어 1분 유효한 콜백 URL로 1회 전송한다.

## 2. 확정된 의사결정

| 항목 | 결정 |
|------|------|
| 카카오 제품 | 카카오 i 오픈빌더 스킬 서버 + AI 챗봇 콜백 |
| 봇 ↔ 카카오 매핑 | 요청 본문 `bot.id`(오픈빌더 봇 ID) 기준 1:1. 어드민에서 `kakao_bot_id` 등록 |
| 카카오 사용자 | JIT 자동 가입. `clerk_user_id='kakao:{kakao_bot_id}:{botUserKey}'`, synthetic email, `provider='kakao'`, FREE |
| 세션 | **카카오 사용자당 1개 지속 세션**. `(user_id, bot_id)`로 get-or-create |
| 헤더 시크릿 | **전역 `.env` `KAKAO_SKILL_SECRET`** 1개. 모든 카카오 스킬 헤더에 동일 값 |
| 긴 답변 | **최대 3개 simpleText 말풍선 분할**(문장 경계, 초과분은 마지막 말풍선 `...`) |
| 결제 정책 | 무시. 카카오 경로는 전부 FREE, `plan_required` 가드 없음 |
| 응답 형태(MVP) | simpleText + quickReplies(followup 버튼) |
| 보안(MVP 필수) | 인바운드 헤더 시크릿 검증 + 아웃바운드 callbackUrl host allowlist(SSRF 차단) |

## 3. 카카오 제약 (공식 문서 검증 완료)

- 스킬 서버 초기 응답 **5초** SLA → 즉시 `useCallback:true` 반환.
- 콜백 URL **1분 유효 · 1회만 사용** → 실패 재시도 불가. fallback은 **첫 콜백 전 실패에만** 가능.
- simpleText **최대 1000자**(500자 초과 시 "전체 보기"), quickReplies **최대 10개**, outputs **1~3개**.
- 콜백 사용은 **봇 마스터가 신청 → 영업일 1~2일 승인**, 그리고 **대상 블록에서 Callback API 활성화 + 스킬 데이터 사용 설정**까지 해야 요청 본문에 `callbackUrl`이 들어온다.
- 카카오 봇테스트 콘솔은 콜백 미지원 → **배포된 봇 + 실제 연결 채널**에서 검증.

## 4. 아키텍처 / 데이터 흐름

```
카카오 사용자 → 오픈빌더 → POST /api/v1/kakao/callback
  [핸들러 endpoints/kakao.py]
    ├─ 헤더 시크릿 검증(hmac.compare_digest) — 불일치 시 401
    ├─ callbackUrl 존재 확인 — 없으면 즉시 동기 simpleText 에러(미설정 안내)
    ├─ BackgroundTasks 예약(kakao_worker)
    └─ 즉시 반환 {"version":"2.0","useCallback":true}        ← 5초 SLA

  [백그라운드 kakao_worker — 새 AsyncSession]
    └─ asyncio.wait_for(_process(...), timeout=50)            ← 절대 deadline
         ├─ bot.id → crud_bot_kakao_channel.get_by_kakao_bot_id → 내부 bot
         ├─ get_or_create_kakao_user(kakao_bot_id, botUserKey)
         ├─ get_or_create_kakao_session(user_id, bot_id)
         ├─ crud_chat.create_message(role=USER, content=utterance)   ← 직접 저장
         ├─ ChatService.process_chat_request(stream=False, use_rag=True)
         │      (bot.use_rag가 RAG 최종 결정, assistant 메시지 저장 + commit은 내부에서)
         ├─ response.content/.followups → simpleText(≤3) + quickReplies(≤10)
         └─ callbackUrl host 검증 → httpx.post(payload)
       (예외/타임아웃 시 fallback simpleText 콜백 1회 — 첫 콜백 전이면)
```

## 5. 컴포넌트 (단일 책임 단위)

### 5.1 스키마 — `backend/app/schemas/kakao.py` (수정)
실제 카카오 페이로드 구조로 교정한다. **현재 스키마는 최상위 `user`를 필수로 받아 실요청이 422가 된다.**
- `KakaoUserRequest`: `utterance`, `user`(KakaoUser), `callbackUrl: str | None`, `lang`, `timezone`.
- `KakaoCallbackRequest`: `userRequest`, `bot`(KakaoBot, `id`), `intent`/`action`(dict|None).
- 응답: `KakaoCallbackResponse`에 `useCallback: bool | None`, `data`/`context` 옵션. `KakaoOutput`에 `simpleText` + `quickReplies` 지원. `KakaoQuickReply(label, action="message", messageText)`.

### 5.2 매핑 모델 — `backend/app/models/bot_kakao_channel.py` (신규)
`BotKakaoChannel(id, bot_id FK→bots.id, kakao_bot_id str unique index, is_active bool=True, created_at)`. 한 오픈빌더 봇(`bot.id`)을 내부 봇 1개에 매핑. (채널은 운영/개발 2개라 봇 기준이 정확)

### 5.3 매핑 CRUD — `backend/app/crud/crud_bot_kakao_channel.py` (신규)
`get_by_kakao_bot_id`, `create`, `list_by_bot`, `delete`. 함수형(기존 컨벤션).

### 5.4 사용자 — `backend/app/crud/crud_user.py` (추가)
`get_or_create_kakao_user(session, kakao_bot_id, bot_user_key) -> User`
- `clerk_user_id = f"kakao:{kakao_bot_id}:{bot_user_key}"`
- `email = f"kakao_{kakao_bot_id}_{bot_user_key}@kakao.local"` (≤255자, unique 충족)
- `provider="kakao"`, plan_type 기본 FREE.
- 동시 최초 요청 대비: select 후 없으면 insert, **IntegrityError 시 재조회**(race).

### 5.5 세션 — `backend/app/crud/crud_chat.py` (추가)
`get_or_create_kakao_session(session, user_id, bot_id) -> ChatSession`
- `(user_id, bot_id)`로 가장 최근 세션 조회, 없으면 `create_chat_session(title="카카오 대화")`.
- 기존 `find_recent_empty_session`은 "빈 세션 조회"라 부적합 → 별도 함수.

### 5.6 어댑터 서비스 — `backend/app/services/kakao_service.py` (신규, 순수 변환 + 전송)
- `to_simple_text_outputs(content: str) -> list[dict]` — 1000자 기준 문장 경계로 ≤3 말풍선 분할, 초과 시 마지막 `...`.
- `to_quick_replies(followups: list[str]) -> list[dict]` — ≤10개, `action="message"`.
- `build_callback_payload(content, followups) -> dict` — version 2.0 template.
- `is_allowed_callback_host(url: str) -> bool` — `urlparse().hostname`이 허용 도메인(설정값, 카카오 도메인)인지. SSRF 차단.
- `send_callback(url, payload)` — httpx async, 짧은 타임아웃, 실패 로깅.
- `fallback_payload(text)` — 실패용 simpleText.

### 5.7 워커 — `backend/app/services/kakao_worker.py` (신규, 오케스트레이션)
`process_kakao_callback(kakao_bot_id, bot_user_key, utterance, callback_url)`
- `app.core.database`의 async session factory로 **새 AsyncSession** 생성(요청 세션 재사용 금지).
- `asyncio.wait_for(_inner, timeout=50)`. 5.4~5.6 흐름 수행.
- 미등록 봇 / 예외 / TimeoutError → `is_allowed_callback_host` 통과 시 fallback 콜백 1회.
- **비내구성**: 프로세스 재시작 시 작업 유실(MVP 한계, 문서화). 1차 출시 이후 큐 도입 후보.

### 5.8 핸들러 — `backend/app/api/v1/endpoints/kakao.py` (재작성)
- 헤더(`X-Kakao-Skill-Secret`, 이름은 설정값) ↔ `settings.KAKAO_SKILL_SECRET` `hmac.compare_digest`. 불일치 401.
- `userRequest.callbackUrl` 없으면 즉시 동기 simpleText("콜백 미설정/미승인") 반환.
- 있으면 `BackgroundTasks.add_task(kakao_worker.process_kakao_callback, ...)` + 즉시 `useCallback:true` 반환.

### 5.9 마이그레이션 — `backend/alembic/versions/*` (신규)
`bot_kakao_channels` 테이블 생성. 기존 마이그레이션 컨벤션 따름.

### 5.10 어드민
- API: `GET/POST/DELETE /api/v1/admin/bots/{bot_id}/kakao` — 카카오봇 ID 등록/목록/삭제. (`endpoints/admin/bots.py` 확장 또는 신규 파일)
- 프론트: `frontend-admin/src/features/bots/components/bot-edit-form.tsx`에 "카카오 채널" 섹션 — `kakao_bot_id` 입력, 활성 토글, 저장. 기존 `useUpdateBot`/api 패턴 재사용.

### 5.11 설정 — `backend/app/core/config.py`
`KAKAO_SKILL_SECRET`, `KAKAO_SKILL_SECRET_HEADER`(기본 `X-Kakao-Skill-Secret`), `KAKAO_CALLBACK_ALLOWED_HOSTS`(기본 `[".kakao.com"]` — 호스트 suffix 매칭. 구현 시 실제 페이로드의 `callbackUrl` host로 검증해 필요하면 도메인 추가).

## 6. 에러 처리 (콜백 1회 원칙)

| 상황 | 처리 |
|------|------|
| 헤더 시크릿 불일치 | 401 거부(정상 카카오는 항상 일치) |
| callbackUrl 없음 | 즉시 동기 simpleText 안내(블록/승인 미설정) |
| 미등록 bot.id | fallback simpleText 콜백 1회 |
| LLM 실패 / 50초 초과 | fallback simpleText 콜백 1회 |
| callbackUrl host 비허용 | POST 안 함(SSRF 차단), 로깅만 |
| 콜백 POST 실패 | 재시도 불가, 로깅만 |

## 7. 테스트 (TDD)

`backend/tests/test_kakao_callback.py`
- 핸들러가 5초 내 `useCallback:true` 즉시 반환(백그라운드 mock).
- 헤더 시크릿 불일치 → 401.
- callbackUrl 없음 → 동기 simpleText 안내.
- 미등록 `bot.id` → fallback 콜백 페이로드 전송.
- JIT 사용자 생성 + 동시성(IntegrityError) 재조회.
- 지속 세션 get-or-create 재사용(같은 user+bot이면 동일 세션).
- user + assistant 메시지 둘 다 저장.
- 변환 포맷 — 1000자 초과 시 ≤3 simpleText, followups ≤10 quickReplies.
- `is_allowed_callback_host` — 카카오 도메인 허용 / 임의 도메인 차단.

검증 — 단위 테스트 통과 → curl로 실제 페이로드 구조 흉내(422 없음, 5초 응답) → 배포 후 실제 채널 친구추가 → 30초 내 답변+후속질문 버튼 → DB·어드민 채팅 목록 확인.

## 8. 사람이 직접 해야 하는 작업 (운영 런북)

> 코드와 별개로 카카오 콘솔에서 사람이 하는 작업. 승인 lead time 때문에 코딩과 병렬로 먼저 시작한다. 거의 전 단계가 **봇 마스터(+연결 채널 권한)** 기준.

1. 카카오비즈니스 채널 개설 → **공개 ON / 검색 허용 확인**, 카테고리 설정.
2. 채널의 **자동응답 메시지 / 채팅방 메뉴 OFF**(챗봇과 동시 사용 불가).
3. 오픈빌더 봇 생성(봇 마스터) → **개발 + 운영 채널 둘 다 연결**.
4. **AI 챗봇 콜백 사용 신청**(봇 마스터, 승인 1~2영업일) — 제일 먼저.
5. 스킬 등록 — URL(우리 콜백 엔드포인트), Test URL, **헤더값에 `KAKAO_SKILL_SECRET`** 입력(우리 `.env`와 동일).
6. **폴백 블록 설정** — ① Callback API 활성화, ② 기본 응답 작성, ③ 스킬 연결, ④ 응답을 스킬 데이터로 사용. (이걸 해야 `callbackUrl`이 옴)
7. 개발 채널 검증 → 오픈빌더 **배포**(최대 30분, 중지 불가) → 실제 채널에서 콜백 검증.
8. 어드민에 해당 봇의 `kakao_bot_id`(요청 본문 `bot.id`) 등록.

> REST API 키 불필요(우리가 카카오로 호출하지 않음). 카카오싱크/개인정보/플러그인 쓸 때만 비즈앱 연결 필요 — MVP 밖.

## 9. 범위 밖 (1차 출시 이후)

카카오 요청 서명 검증 강화, 카카오 사용자 rate limit, 백그라운드 작업 내구화(큐/재시도), 멀티 말풍선(carousel/listCard), 다채널 일반화(`BotChannel(channel_type=...)`).
