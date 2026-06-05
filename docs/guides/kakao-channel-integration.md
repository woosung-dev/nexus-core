# 카카오톡 채널 봇 Q&A 연동 가이드

> 사용자가 카카오톡 채널을 친구 추가하기만 하면 별도 앱 설치 없이 특정 봇과 Q&A 할 수 있게 만드는 작업.
> 작성일: 2026-05-21

## 1. 핵심 결론 (요약)

- 기술적으로 **가능**. `/api/v1/kakao/callback` 라우터와 스키마는 이미 stub 으로 존재 (현재는 echo 응답만).
- 카카오 i 오픈빌더 스킬 서버 제약은 **5초 동기 응답**이지만, **콜백 비동기 응답(useCallback)** 으로 **최대 1분**까지 응답을 지연시킬 수 있음.
- 우리 서비스 LLM 응답이 약 30초 걸려도 1분 콜백 유효시간 안에 들어와서 **안전**.
- 봇 응답 생성 로직(`ChatService.process_chat_request`)은 그대로 재사용 가능. 카카오 어댑터 레이어만 새로 짜면 됨.

## 2. 의사결정 사항 (확정됨)

| 항목 | 결정 |
|------|------|
| 카카오 제품 | **카카오 i 오픈빌더 스킬 서버** (친구 추가 기반 Q&A) |
| 봇 ↔ 채널 매핑 | **채널 1개 = 봇 1개**. 어드민이 봇별로 카카오 채널 ID 등록 |
| 카카오 사용자 처리 | **JIT 자동 가입**. `User` 테이블에 `provider='kakao'`, `clerk_user_id='kakao:{kakao_user_id}'` 로 자동 레코드 생성. 별도 OAuth 불필요 |
| 응답 시간 처리 | **콜백 비동기 응답**. 5초 안에 `useCallback:true` 응답 → 백그라운드에서 LLM 호출 → 콜백 URL 로 POST |

## 3. 아키텍처 흐름

```
[카카오 사용자]
    ↓ (메시지 전송)
[카카오 i 오픈빌더]
    ↓ POST /api/v1/kakao/callback/{channel_id}
[FastAPI 라우터]
    ├── ① 즉시 응답: {"useCallback": true}  ← 5초 안에 반환
    └── ② BackgroundTasks
         ├── BotKakaoChannel → bot_id 조회
         ├── get_or_create_kakao_user(kakao_user_id)
         ├── ChatSession get-or-create
         ├── ChatService.process_chat_request(streaming=False)  ← ~30초
         ├── 응답 → 카카오 simpleText 포맷 변환
         └── httpx.post(callback_url, payload)  ← 1분 안에 전송
```

## 4. 변경 대상 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/api/v1/endpoints/kakao.py` | echo → 콜백 비동기 응답 로직 |
| `backend/app/schemas/kakao.py` | `useCallback`, `callbackUrl` 필드 추가 |
| `backend/app/services/kakao_service.py` (신규) | 응답 포맷 변환 + 콜백 POST |
| `backend/app/models/bot_kakao_channel.py` (신규) | 봇 ↔ 채널 매핑 모델 |
| `backend/app/crud/crud_user.py` | `get_or_create_kakao_user` 추가 |
| `backend/app/crud/crud_bot_kakao_channel.py` (신규) | 채널 CRUD |
| `backend/app/api/v1/endpoints/admin/bots.py` 또는 신규 | 채널 매핑 어드민 API |
| Alembic 마이그레이션 (신규) | `bot_kakao_channels` 테이블 |
| `frontend-admin/...` | 봇 상세 페이지에 카카오 채널 ID 입력 UI |

> 브랜치 제안: `feat/kakao-channel-integration` (기존 어드민 피드백 브랜치와 별개 작업)

## 5. TODO 체크리스트

### 5.1 데이터 모델 & 사용자 매핑

- [ ] `backend/app/models/bot_kakao_channel.py` 신규 — `BotKakaoChannel` 모델 (`id`, `bot_id`, `kakao_channel_id` unique, `signing_secret?`, `is_active`, `created_at`)
- [ ] Alembic 마이그레이션 생성 — `bot_kakao_channels` 테이블
- [ ] `bot` 모델과의 relationship 추가
- [ ] `backend/app/crud/crud_bot_kakao_channel.py` 신규 — get/create/list/update/delete
- [ ] `backend/app/crud/crud_user.py` — `get_or_create_kakao_user(db, kakao_user_id)` 추가
  - `provider='kakao'`, `clerk_user_id=f'kakao:{kakao_user_id}'`, `plan_type=FREE`
- [ ] 마이그레이션 적용 및 로컬 DB 확인

### 5.2 카카오 콜백 핸들러 (핵심)

- [ ] `backend/app/schemas/kakao.py` 확장 — `useCallback`, `callbackUrl`, simpleText 응답 스키마
- [ ] `backend/app/api/v1/endpoints/kakao.py` 재작성 (echo 제거)
  - 라우트: `POST /api/v1/kakao/callback/{channel_id}` 또는 body 내 채널 식별
  - 채널 조회 → 봇 식별 → 미등록 시 404
  - 카카오 사용자 JIT 생성
  - `ChatSession` get-or-create
  - `BackgroundTasks` 로 LLM 작업 예약
  - 즉시 `useCallback:true` 응답
- [ ] 5초 SLA 측정 — 핸들러 자체가 즉시 응답되는지 단위 테스트

### 5.3 응답 포맷 변환 + 콜백 전송

- [ ] `backend/app/services/kakao_service.py` 신규
  - `to_kakao_simple_text(content: str) -> dict`
  - `to_kakao_quick_replies(followups: list[str]) -> dict`
  - `send_callback(callback_url: str, payload: dict)` — httpx, 3초 타임아웃
- [ ] BackgroundTask 안에서 `ChatService.process_chat_request(streaming=False)` 호출
- [ ] LLM 결과를 카카오 응답 JSON 으로 변환
- [ ] 콜백 URL POST 전송
- [ ] **fallback 응답** — LLM 실패해도 "죄송합니다, 일시적 오류" 같은 fallback 콜백 전송 보장
- [ ] **simpleText 길이 제한** — 응답 너무 길면 잘라서 전송

### 5.4 어드민 UI

- [ ] 어드민 API — `GET/POST/DELETE /api/v1/admin/bots/{bot_id}/kakao-channels`
- [ ] `frontend-admin` 봇 상세 페이지에 "카카오 채널" 섹션 추가
- [ ] 채널 ID 입력, 활성/비활성 토글, 삭제
- [ ] `plan_required` 정책 결정 — PRO/ENTERPRISE 봇을 카카오에 매핑할 수 있는지 (FREE 만 허용? 어드민 경고만?)

### 5.5 테스트 & 실제 연동 검증

- [ ] 단위 테스트 `backend/tests/test_kakao_callback.py`
  - 샘플 카카오 페이로드 → 즉시 useCallback 응답
  - BackgroundTasks mock → 콜백 URL POST 시 simpleText 포맷 검증
  - 알 수 없는 채널 ID → 404
  - 카카오 사용자 JIT 생성 확인
- [ ] `curl` 로 카카오 페이로드 흉내내서 end-to-end 검증
- [ ] **실제 카카오 i 오픈빌더 콘솔 연동**
  - ngrok 으로 로컬 서버 노출
  - 콘솔에 스킬 URL 등록
  - 테스트 채널 친구 추가 → 메시지 → 30초 안에 응답 도착 확인
- [ ] DB 검증 — `chat_session`, `message` 테이블에 카카오 사용자 세션 기록 + 어드민 피드백 UI 에서 보이는지 확인

## 6. 위험 / 제약 사항

- **콜백 URL 은 1회만 사용 가능** — 한 번 실패하면 재시도 불가. 따라서 LLM 실패 시에도 반드시 fallback 텍스트라도 콜백 전송 필수.
- **콜백 URL 1분 유효시간** — LLM 응답이 1분 넘어가면 실패. RAG + Followup 합쳐서 길어질 수 있으니 BackgroundTask 안에서 `asyncio.wait_for(..., timeout=50)` 같은 가드 추가 권장.
- **콜백 응답에 3초 안에 200 OK** — httpx POST 시 카카오 서버가 3초 안에 200 받아야 함. 네트워크 안정성 확보.
- **카카오 simpleText 길이 제한** — 한 응답에 표시 가능한 글자 수 제한(약 1000자 내외). 긴 응답은 잘라서 보내거나 여러 말풍선으로 분할.
- **plan_required 충돌** — 카카오 사용자는 항상 FREE. PRO/ENTERPRISE 전용 봇을 카카오에 매핑하면 정책 충돌. 어드민 UI 에서 막거나, "카카오 채널은 항상 FREE 권한으로 동작" 정책 명시.
- **요청 검증** — 1차 출시는 채널 ID 매칭만으로 가도 되지만 운영 단계에서는 카카오 서명 검증 추가 권장.

## 7. 1차 출시 이후 (선택)

- 카카오 요청 서명/시그니처 검증
- 카카오 사용자 단위 rate limit
- 멀티 말풍선(carousel, listCard) 응답 지원
- 다른 채널(슬랙/디스코드) 로 일반화 — `BotChannel(channel_type='kakao'|'slack'|...)` 추상화

## 8. 참고 자료

- [AI 챗봇 콜백 개발 가이드 (kakao business)](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/ai_chatbot_callback_guide)
- [콜백 개발 가이드 (챗봇 관리자센터)](https://chatbot.kakao.com/docs/skill-callback-dev-guide)
- [스킬 만들기 (kakao business)](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill)
- 내부 계획 원본 — `~/.claude/plans/image-1-federated-seahorse.md`
