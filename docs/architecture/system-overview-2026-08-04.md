# Nexus Core — 아키텍처 & 요청 여정 (main / d37e4f6, 2026-08-04)

사용자가 질문을 보낸 순간부터 화면에 답변·출처·후속질문이 채워지기까지의 전 경로를 코드 기준으로 정리한다.
GitHub 에서 mermaid 가 렌더된다.

---

## 01. 시스템 구성

입구는 웹 채팅 / 관리자 콘솔 / 카카오톡 채널 세 갈래지만, 답변을 만드는 코드는 `ChatService` 한 곳이다.

```mermaid
flowchart LR
  subgraph CH["사용자 채널"]
    W["웹 브라우저"]
    K["카카오톡 채널<br/>i 오픈빌더"]
    A["관리자 브라우저"]
  end

  subgraph FE["Next.js (App Router)"]
    FC["frontend-client :3000"]
    FA["frontend-admin :3001"]
  end

  subgraph BE["FastAPI :8080 — Cloud Run asia-northeast3"]
    RT["api/v1 router"]
    CS["ChatService"]
    FQ["faq_service"]
    RG["rag/gemini"]
    LL["llm/gemini · llm/openai"]
    KW["kakao_worker"]
  end

  subgraph DATA["상태"]
    PG[("Postgres + pgvector")]
    R2[("Cloudflare R2")]
  end

  subgraph EXT["외부 서비스"]
    GEM["Gemini API<br/>generate · file_search<br/>interactions · embedding"]
    HAN["하나로 SSO v2"]
  end

  W --> FC
  A --> FA
  K -->|"skill callback"| RT
  FC -->|"Bearer JWT"| RT
  FA -->|"rewrite /api/v1"| RT
  RT --> CS
  RT --> KW
  KW --> CS
  CS --> FQ
  CS --> RG
  CS --> LL
  FQ --> PG
  FQ --> GEM
  CS --> PG
  RG --> GEM
  LL --> GEM
  RT --> R2
  RT --> HAN
  KW -.->|"1회 콜백 POST"| K
```

- 관리자 프론트: Next `rewrites` 로 `/api/v1/*` 프록시
- 클라이언트 프론트: `NEXT_PUBLIC_API_URL` 절대 주소 직접 호출 (dev 프록시 30초 소켓 절단 회피)

---

## 02. 질문 → 응답 전 구간

웹 클라이언트는 `stream: false` 로 보낸다. 답변은 한 번에 오고, **출처만 나중에** 채워진다.

```mermaid
sequenceDiagram
  autonumber
  actor U as 사용자
  participant FE as ChatProvider
  participant API as FastAPI chats
  participant SVC as ChatService
  participant DB as Postgres + pgvector
  participant G as Gemini API

  U->>FE: 질문 입력 후 전송
  FE->>FE: 내 메시지 즉시 표시, awaiting = true

  opt 새 대화일 때만
    FE->>API: POST /chats?bot_id
    API->>DB: 메시지 0건 빈 세션 재사용, 없으면 생성
    API-->>FE: session_id
    FE->>FE: replaceState 로 URL 만 교체
  end

  FE->>API: POST /chats/completions (stream=false, use_rag=true)
  API->>API: JWT 검증 — 하나로 HS256 또는 외부 JWKS
  API->>DB: 사용자 조회/생성 (30초 캐시)
  API->>DB: 봇 활성 · 세션 소유권 확인
  API->>DB: 첫 메시지면 세션 제목을 질문 앞 20자로
  API->>DB: user 메시지 INSERT (flush)
  API->>SVC: process_chat_request

  Note over SVC,DB: ① FAQ Override
  SVC->>DB: 활성 FAQ 개수 (60초 TTL 캐시)
  alt FAQ 존재
    SVC->>G: 질문 임베딩 768차원
    SVC->>DB: pgvector 코사인 최근접 1건
  end

  alt 유사도 threshold 충족
    SVC->>DB: FAQ 답변 저장 + commit
    SVC-->>API: source = faq_override
  else 생성 경로
    Note over SVC,G: ② RAG
    SVC->>DB: history_window 만큼 최근 메시지 (기본 0)
    SVC->>G: generate_content + FileSearch (bot_id 필터, top_k 12, temp 0.3)
    G-->>SVC: 본문 + grounding_metadata + followups 블록
    SVC->>SVC: followups 분리 · 인용마커 제거 · 청크 중복 병합
    opt strict 봇인데 직접 인용 0건
      SVC->>SVC: 본문 폐기 후 근거 없음 안내
    end
    SVC->>DB: assistant 메시지 + citations + followups → commit
    SVC-->>API: source = rag
  end

  API-->>FE: 200 content citations followups session_id
  FE->>FE: 답변 + 후속질문 칩 렌더
  FE->>API: GET /chats/{id}/messages — 진짜 message_id 확보

  par 서버 백그라운드
    SVC->>G: 인용 비었으면 interactions 재검색 (근사)
    SVC->>G: 인용 있으면 근거 구절 추출 (청크당 1회, 동시 4)
    SVC->>DB: 별도 세션으로 citations UPDATE
  and 프론트 폴링
    FE->>API: 2초 간격 최대 15회 재조회
    API-->>FE: 인용 도착 시 출처 카드 · 형광펜
  end
```

| 단계 | 위치 |
| --- | --- |
| 낙관적 렌더 · 세션 확보 · 인용 폴링 | `frontend-client/src/app/(protected)/chat/ChatProvider.tsx` |
| 봇·세션 검증, 제목 갱신, user 메시지 flush | `backend/app/api/v1/endpoints/chat.py` |
| alg 분기 JWT 검증 + JIT 사용자 | `backend/app/api/deps.py` |
| FAQ → RAG → LLM 분기, strict 게이트, 백필 예약 | `backend/app/services/chat_service.py` |
| 임베딩 + pgvector 최근접 + threshold | `backend/app/services/faq_service.py` |
| File Search 생성 · 인용 추출 · 근사 인용 | `backend/app/services/rag/gemini.py` |
| 근거 구절 추출 후 원문 스냅 | `backend/app/services/rag/evidence.py` |

---

## 03. 응답 경로 분기

응답 JSON 의 `source` 가 어느 갈래였는지 그대로 알려준다.

```mermaid
flowchart TD
  Q(["사용자 질문"]) --> F1{"활성 FAQ 존재?"}
  F1 -->|"없음"| H["대화 히스토리 로드"]
  F1 -->|"있음"| E["임베딩 + pgvector 검색"]
  E --> F2{"유사도 >= threshold"}
  F2 -->|"미달"| H
  F2 -->|"충족"| F3{"strict 봇인가"}
  F3 -->|"아니오"| FAQOUT["source = faq_override"]
  F3 -->|"예, 거절문 아님"| BLK1["source = policy_block"]
  F3 -->|"예, 거절문 FAQ"| FAQOUT

  H --> R1{"use_rag AND bot.use_rag"}
  R1 -->|"거짓 · strict"| BLK2["source = policy_block"]
  R1 -->|"거짓 · 일반"| LLM["순수 LLM + 후속질문 별도 호출<br/>source = llm"]
  R1 -->|"참"| S1{"stream 요청?"}

  S1 -->|"false — 현재 웹·카카오"| RAGB["generate_with_rag<br/>본문+인용+후속 1회"]
  S1 -->|"true, 일반 봇"| SSE1["SSE 청크 스트리밍"]
  S1 -->|"true, strict 봇"| SSE2["검증 후 한 덩어리 전송"]

  RAGB --> G1{"strict 인데 직접 인용 0건?"}
  G1 -->|"예"| BLK3["본문 폐기 · 근거 없음 안내"]
  G1 -->|"아니오"| OUT["source = rag"]
```

`use_rag` 는 **요청값 AND 봇 설정**. 문서 없는 봇은 `use_rag=false` 로 꺼야 빈 검색 비용이 사라진다.

---

## 04. 인용 파이프라인 (출처가 늦게 뜨는 이유)

```mermaid
flowchart TB
  subgraph P1["① 답변 경로 — 사용자 대기 구간"]
    A1["generate_content + FileSearch"] --> A2["grounding_chunks"]
    A2 --> A3["grounding_supports<br/>답변 구간 ↔ 청크 매핑"]
    A3 --> A4["중복 청크 병합 · cite_count 누적"]
    A4 --> A5["messages.citations 저장"]
  end

  A5 --> D{"이번 인용이 비었는가"}

  subgraph P2["② 인용 백필 — 응답 이후"]
    B1["interactions.create<br/>페르소나 + 인용 지침"] --> B2["file_citation 어노테이션"]
    B2 --> B3["approximate = true"]
  end

  subgraph P3["③ 근거 구절 — 응답 이후"]
    C1["청크당 LLM 1회, 동시 4"] --> C2["모델이 제시한 구절"]
    C2 --> C3["원문 대조 스냅 · 겹침 0.8 미만 폐기"]
    C3 --> C4["evidence = 원문의 부분문자열"]
  end

  D -->|"비었음"| B1
  D -->|"있음"| C1
  B3 --> W["별도 DB 세션 UPDATE"]
  C4 --> W
  W --> FEP["프론트 폴링 → 출처 카드 · 형광펜"]
```

- ②의 인용은 **표시된 답변이 아니라 두 번째 생성 답변** 기준 → `approximate=true`
- ③의 형광펜은 모델 문자열을 쓰지 않고 청크 원문 위치로 스냅 → 환각이 저장될 수 없음

### 대기 시간 구조

| 구간 | 내용 |
| --- | --- |
| BLOCKING | JWT 검증 → 봇·세션 조회 → user msg flush → FAQ 카운트/임베딩/pgvector → Gemini generate_content → 파싱 → commit |
| BACKGROUND | 인용 백필 (프론트 주석 기준 실측 ~15초), 근거 구절 추출 |
| CLIENT | 2초 × 최대 15회 폴링 (확보 즉시 중단) |

코드에 박힌 값: `RAG_TOP_K=12`, `RAG_TEMPERATURE=0.3`, 히스토리 메시지당 500자 컷, followup timeout 5초,
카카오 워커 데드라인 50초, 업로드 상한 50MB.

비스트리밍 경로는 후속질문을 RAG 호출 안 `<followups>` 마커로 같이 받는다(별도 LLM 호출 제거).

---

## 05. 인증

```mermaid
sequenceDiagram
  autonumber
  actor U as 사용자
  participant NX as Next /api/auth/login
  participant BE as FastAPI /auth/hanaro/login
  participant HA as 하나로 판별 API v2
  participant DB as Postgres

  U->>NX: 아이디 · 비밀번호
  NX->>BE: 그대로 전달 (저장·로깅 없음)
  BE->>HA: keyValue + userid + password
  alt authenticated = true
    HA-->>BE: isOfficial
    BE->>DB: hanaro:{userid} 조회 또는 생성
    BE-->>NX: 세션 JWT (HS256, 기본 12시간)
    NX-->>U: httpOnly 쿠키 nexus_session
  else 실패
    HA-->>BE: invalid_credentials · rate_limited · invalid_key
    BE-->>NX: 사유별 상태코드/에러코드 구분
  end

  Note over U,DB: 이후 모든 API 호출

  U->>NX: GET /api/auth/session
  NX-->>U: 쿠키에서 꺼낸 토큰
  U->>BE: Authorization Bearer (30초 메모리 캐시)
  BE->>BE: alg 분기 — HS256 자체 키 / 그 외 JWKS
  BE->>DB: 사용자 조회 또는 JIT 생성 (30초 캐시)
```

미들웨어는 쿠키 존재 여부만 검사(`/chat`, `/mypage`). 서명 검증은 백엔드가 매 요청 수행.

---

## 06. 카카오 채널 (5초 규약 우회)

```mermaid
sequenceDiagram
  autonumber
  actor U as 카카오 사용자
  participant KO as i 오픈빌더
  participant EP as POST /kakao/callback
  participant WK as kakao_worker
  participant SVC as ChatService
  participant DB as Postgres

  U->>KO: 발화
  KO->>EP: skill 요청 + callbackUrl
  EP->>EP: 헤더 시크릿 검증
  alt callbackUrl 없음
    EP-->>KO: 콜백 미설정 안내
  else 정상
    EP-->>KO: useCallback true · "답변을 준비하고 있어요"
    Note right of EP: 여기까지 5초 안에 끝난다
    EP->>WK: BackgroundTasks 예약
    WK->>DB: 카카오 봇 매핑 · 사용자 자동 생성
    WK->>DB: 지속 세션 재사용
    WK->>SVC: 웹과 동일한 process_chat_request
    SVC-->>WK: 답변 + 후속질문
    WK->>WK: 1000자 × 최대 3덩이 분할 · quickReplies 변환
    WK->>WK: callbackUrl 호스트 화이트리스트 (SSRF 차단)
    WK-->>KO: 정확히 1회 POST (재시도 없음)
    KO-->>U: 답변 + 추천 질문 버튼
  end
```

데드라인 50초는 **생성에만** 걸리고, 전송은 데드라인 밖에서 한 번 → 중복 발송 불가.

---

## 07. 데이터 모델

```mermaid
erDiagram
  users ||--o{ chat_sessions : "소유"
  bots ||--o{ chat_sessions : "응답"
  chat_sessions ||--o{ messages : "포함"
  bots ||--o{ faqs : "오버라이드"
  bots ||--o{ bot_instructions : "지침 버전"
  bots ||--o{ bot_kakao_channels : "채널 매핑"

  users {
    int id PK
    string clerk_user_id "hanaro: / kakao: 네임스페이스"
    string email "하나로는 없음"
    bool is_official
    bool is_active
  }
  bots {
    int id PK
    text system_prompt "페르소나"
    string llm_model
    bool use_rag "봇 단위 토글"
    string evidence_policy_mode "legacy | strict"
    int history_window "0 = 기억 안 함"
    bool is_active
  }
  chat_sessions {
    int id PK
    int user_id FK
    int bot_id FK
    string title "첫 질문 앞 20자"
    datetime updated_at
  }
  messages {
    int id PK
    int session_id FK
    enum role "user | assistant"
    text content
    json citations "청크 출처 + evidence"
    json followups
    string feedback
    string feedback_reasons
    text feedback_comment
  }
  faqs {
    int id PK
    int bot_id FK
    text question
    text answer
    vector question_vector "768차원"
    float threshold "FAQ 마다 개별"
    bool is_active
  }
  bot_instructions {
    int id PK
    int bot_id FK
    text system_prompt
    int version
    bool is_applied
  }
  bot_kakao_channels {
    int id PK
    int bot_id FK
    string kakao_bot_id
    bool is_active
  }
```

RAG 문서 자체는 DB 가 아니라 **Gemini File Search Store 한 곳**에 모이고 `bot_id` 메타데이터로만 갈린다.
그 외 레드팀 운영 테이블군(질문·피드백·리뷰·테스트봇 평가)이 별도로 있다.

---

## 08. 운영 루프

코드 배포 없이 답변을 바꿀 수 있는 손잡이 넷: 문서 / FAQ / 지침·프롬프트 / 봇 설정.

```mermaid
flowchart LR
  subgraph ADM["관리자 콘솔"]
    D1["문서 업로드 (50MB)"]
    D2["FAQ 등록·수정"]
    D3["지침 빌더"]
    D4["봇 설정<br/>모델 · use_rag · strict · 기억"]
  end

  D1 --> S1["R2 원본 보관"]
  D1 --> S2["File Search Store<br/>bot_id + 내용 해시 태깅"]
  S2 --> IDX["Gemini 백그라운드 인덱싱"]
  D2 --> EMB["질문 임베딩 재생성"] --> FQT[("faqs")]
  D3 --> SP["system_prompt 빌드"] --> BOT[("bots")]
  D4 --> BOT

  IDX --> ANS(("사용자 답변"))
  FQT --> ANS
  BOT --> ANS

  ANS --> FB["좋아요·싫어요 + 사유 + 코멘트"]
  FB --> REV["대화 열람 · 레드팀 검토"]
  REV -.->|"문서 보강 · FAQ 추가 · 프롬프트 수정"| ADM
```

업로드 기본은 **추가**다. 정리 목적일 때만 `replace=true` 를 명시해야 구버전이 지워진다.

---

## 09. 읽으며 확인된 것

| 항목 | 내용 |
| --- | --- |
| 관리자 API 인증 | `endpoints/admin/` 어느 라우트에도 `get_current_user` 가 없다. 코드만 보면 무인증 |
| SSE 경로 | 구현 3종 존재하나 웹·카카오 모두 `stream=False` → 현재 미사용 |
| 대화 기억 | `history_window` 기본 0 → 봇별로 켜지 않으면 매 질문 독립 |
| 인용 0건 | RAG 미작동이 아니라 grounding "보고" 누락일 수 있음. 백필 인용은 `approximate` |
| 카카오 세션 | `(user_id, bot_id)` UNIQUE 없음 → 동시 첫 발화 시 세션 중복 가능, 이후 최신 세션으로 수렴 |
| 빈 Store 검색 | 문서 없는 봇도 검색 호출 시간은 그대로 발생 → `use_rag=false` 권장 |
