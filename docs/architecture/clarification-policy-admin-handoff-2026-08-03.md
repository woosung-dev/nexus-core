# D-1 v2 맥락 보완 2차 — 관리자 정책 화면 핸드오프 (2026-08-03)

## 이 문서의 목적

현재 D-1 v2의 1차 목표는 LLM + File Search가 문서 근거를 읽고 추가 질문 카드를 생성하는 것이다. 2차 목표는 **어떤 경우에 반드시 질문해야 하는지**를 개발자가 코드로 추가하지 않고, 봇 관리자가 관리자 화면에서 설정하는 것이다.

다음 세션은 이 문서를 읽고 2차 설계·구현을 이어 간다. 현재 작업 트리는 다른 사용자 변경을 포함해 dirty 상태이므로, 관련 없는 변경을 되돌리거나 정리하지 않는다.

## 1차 구현 완료 상태

### 현재 코드 흐름

```text
사용자 최초 요청
  → POST /api/v1/clarification-preview
  → ClarificationService.live_decision (첫 요청에서만 계획 생성)
  → GeminiRAGService.generate_structured_with_rag
  → Gemini Interactions + File Search 1회 + store=false
      → [EVIDENCE] 자연어 문서 근거
      → [PLAN] JSON 계획
      → same-call file_citation annotations
  → 계획 정규화·근거 검증
      ├─ ask: 인라인 카드 표시
      └─ ready/fallback: 결정적 요청 요약

카드 제출/건너뛰기
  → 모델 계획 재호출 없이 요청 요약 생성
  → POST /api/v1/clarification-preview/answer 1회
  → 일반 RAG 최종 답변
```

주요 파일:

| 파일 | 역할 |
|---|---|
| `backend/app/services/rag/gemini.py` | 계획용 Interactions 호출, same-call annotation 인용 파싱 |
| `backend/app/services/clarification_service.py` | ask/answer 정규화·검증·결정적 요약 |
| `backend/app/api/v1/endpoints/clarification_preview.py` | 비영속 프로토타입 API |
| `frontend-client/src/components/chat/ClarificationPrototype.tsx` | 인라인 카드 및 최종 답변 UX |
| `frontend-admin/src/features/bots/components/bot-edit-form.tsx` | 현재 봇 설정 화면; 2차 설정 UI의 진입점 후보 |

### Interactions 구현상 중요한 발견

- D-1 (`gemini-3.5-flash-lite`)에서 native JSON `response_format` + File Search는 실제로 `file_citation=0`을 반환했다.
- JSON 형식을 `[EVIDENCE]` 자연어 근거 + `[PLAN]` JSON envelope로 바꾸면, 같은 Interaction 호출에서 인용과 유효한 계획을 함께 받을 수 있었다.
- 따라서 현재 계획 호출은 native JSON schema가 아니라 Pydantic 사후 검증을 사용한다. 이 선택은 D-1 실측 근거에 따른 것이다.
- `store=false`를 사용하므로 Gemini의 Interaction 객체도 서버 상태로 저장하지 않는다.

### D-1 실환경 검증

실행 페이지:

`http://localhost:3201/chat/new/11?clarify-prototype=1`

읽기 전용 Compose 프로필:

```bash
set -a; source backend/.env; set +a
NEXUS_REAL_BOT_DATABASE_URL="$DATABASE_URL" \
NEXUS_REAL_BOT_FILE_SEARCH_STORE_NAME="${FILE_SEARCH_STORE_NAME:-nexus-core-knowledge-base}" \
docker compose -p nexus-clarification \
  -f docker-compose.yml \
  -f docker-compose.prototype.yml \
  -f docker-compose.prototype.real-bot.yml \
  up -d --force-recreate api client
```

원격 D-1 DB와 File Search Store에는 읽기만 수행한다. 마이그레이션·문서 업로드·ChatSession/Message 저장을 하지 않는다.

최종 코드 기준 10문항 결과:

| 번호 | 요청 축약 | 결과 |
|---:|---|---|
| 1 | 축복헌금 환불 | ask, 질문 1개, 인용 2건 |
| 2 | 배우자 성화 후 재축복 | ready |
| 3 | 2세-1세 축복 후 자녀 세대 | ready |
| 4 | 출산 후 의례 | ready |
| 5 | 국제축복 준비 서류 | ask, 질문 1개, 인용 3건 |
| 6 | 2세 가정출발 전 의식 | ready |
| 7 | 2세-1세 축복 후 의식 | fallback |
| 8 | 축복정리 후 재축복 | ask, 질문 1개, 인용 2건 |
| 9 | 1세 국제축복 헌금 | ask, 질문 1개, 인용 1건 |
| 10 | 건강 사실 미고지 후 축복 유지 | ready |

합계: `ask 4`, `ready 5`, `fallback 1`, 오류 0.

카드 선택 뒤 최종 답변도 실제 호출했다. 최종 RAG 호출은 1회였고 문서 인용 7건·후속 질문 3개를 반환했다.

검증 명령:

```bash
cd backend
DATABASE_URL='postgresql+asyncpg://test:test@localhost/test' \
GEMINI_API_KEY='test-key' \
.venv/bin/pytest -q

pnpm --dir ../frontend-client lint
```

마지막 결과: 백엔드 `102 passed`, 클라이언트 lint 통과.

## 왜 2차 정책이 필요한가

LLM + RAG는 문서에 있는 분기를 읽고 질문할 수 있지만, “조건부 설명으로 바로 답해도 되는가”와 “먼저 물어야 하는가”의 임계값을 일관되게 정하지 못한다. 위 10문항에서도 카드 4건만 생성됐다.

보장하려면 중요한 업무에서 아래 결정을 서버가 결정적으로 내려야 한다.

```text
해당 정책 규칙이 매칭되고, required_slots 중 하나가 비어 있음
  → ask (LLM이 ready를 골라도 카드 우선)
모든 required_slots가 채워짐
  → 최종 RAG 답변
정책이 없거나 문서 근거가 없음
  → 현행 LLM 계획 경로 또는 안전한 담당 확인 경로
```

LLM/RAG는 계속 사용한다. LLM은 요청을 규칙에 연결하고, 사용자가 이미 제공한 slot 값을 추출하며, 문서 근거의 질문 문구와 선택지를 만든다. 단, **필수 slot의 누락 여부**는 관리자가 승인한 정책으로 서버가 판단한다.

## 관리자에게 요청할 정보

관리자에게 “모든 답변을 미리 작성해 달라”고 요청하지 않는다. 업무별로 아래 7가지만 받는다.

1. **규칙 이름**: 예) `축복헌금 환불 가능 여부`
2. **사용자 요청 예시**: 실제 표현 2~5개
3. **바로 답하면 안 되는 이유**: 결과/절차/금액이 어떤 사실에 따라 달라지는지
4. **반드시 확인할 항목**: 한 번에 최대 3개
5. **각 항목의 선택지**: 2~5개 + 직접 입력 허용 여부
6. **관련 공식 문서**: 업로드된 문서 또는 조항/페이지
7. **정보가 없을 때 처리**: 카드 질문, 담당자 연결, 또는 일반 설명 허용 중 하나

관리자에게 보낼 요청문 예시:

> 챗봇이 개인 상황에 따라 달라지는 절차를 바로 단정하지 않도록, 업무별 필수 확인 항목을 등록하려고 합니다. 각 업무에 대해 (1) 사용자가 흔히 하는 질문, (2) 결과가 달라지는 조건, (3) 반드시 먼저 물어야 하는 항목과 선택지, (4) 근거 문서/조항, (5) 알 수 없을 때의 안내 방식을 적어 주세요. 모든 답변을 작성하실 필요는 없고, ‘무엇을 먼저 확인해야 하는지’만 정리해 주시면 됩니다.

## 관리자 UI/UX 제안

### 화면 진입점

관리자 봇 편집 화면의 `AI 응답 설정` 아래에 **`추가 확인 질문 정책`** 섹션을 만든다.

```text
봇 편집
 ├─ 기본 정보
 ├─ 문서 지식베이스
 ├─ AI 응답 설정
 └─ 추가 확인 질문 정책  ← 신규
     ├─ 정책 사용 토글
     ├─ 등록된 규칙 목록
     ├─ 새 규칙 만들기
     └─ 테스트 패널
```

### 목록 화면

상단:

- `필수 확인 질문 사용` 토글
- `새 규칙 만들기` 버튼
- `테스트하기` 버튼

규칙 카드는 다음만 보여 준다.

```text
[활성] 축복헌금 환불
사용자 요청 예시 3개 · 필수 확인 3개 · 근거 문서 1개
누락 시: 질문 카드 표시
편집   복제   비활성화
```

한 화면에 “정책 JSON”, 모델명, RAG 같은 내부 구현 용어는 노출하지 않는다.

### 규칙 작성: 4단계 wizard

1. **언제 확인할까요?**
   - 규칙 이름
   - 사용자가 실제로 쓰는 질문 예시 2~5개
   - `이 요청에서 바로 답변하면 안 되는 이유` 자유 서술

2. **무엇을 확인할까요?**
   - 필수 확인 항목을 최대 3개 추가
   - 각 항목: 질문 문구, 단일/복수 선택, 선택지 2~5개, `직접 입력 허용`
   - 드래그로 질문 순서 변경

3. **어떤 문서를 근거로 하나요?**
   - 이 봇에 연결된 업로드 문서 목록에서 선택
   - 선택 후 조항/페이지 메모를 선택적으로 입력
   - 문서가 없으면 저장 경고: `근거 문서를 먼저 연결해 주세요.`

4. **검토와 공개**
   - 요약 미리보기: “사용자가 이 질문을 하면 이 세 항목을 먼저 확인합니다.”
   - 예시 요청 입력 → 예상 카드 미리보기
   - `초안 저장`과 `사용 시작`을 분리

### 테스트 패널

관리자가 실제 문장을 넣으면 다음을 한 화면에 보여 준다.

```text
입력한 요청
  “국제 축복 준비시 필요한 서류를 알려줘”

적용된 규칙
  국제축복 준비 · 필수 확인 1/2개 누락

사용자에게 보일 카드 미리보기
  “준비하시는 국제 축복의 대상 유형을 선택해 주세요.”

근거
  신한국 축복가정행정 규정집 개정초안 2026 · p.15
```

이 화면은 규칙의 “왜 질문이 나왔는지”를 설명해야 하며, 원시 LLM 로그·내부 오류를 노출하지 않는다.

## 데이터 모델 제안

초기 구현은 봇마다 JSON 컬럼 하나로 충분하다. 이후 검색/감사 요구가 생기면 정규화 테이블로 분리한다.

```json
{
  "enabled": true,
  "rules": [
    {
      "id": "blessing_refund",
      "name": "축복헌금 환불",
      "enabled": true,
      "priority": 100,
      "request_examples": ["축복헌금 환불 가능한가요?"],
      "why_ask": "축복 유형과 진행 단계에 따라 환불 기준이 달라집니다.",
      "document_refs": [{"document_id": "...", "label": "규정집 p.52"}],
      "required_slots": [
        {
          "id": "blessing_type",
          "label": "축복 유형",
          "question": "어떤 축복 유형에 해당하시나요?",
          "selection_mode": "single",
          "options": ["축복자녀", "미혼 1세", "기타"],
          "allow_custom": true
        }
      ],
      "when_missing": "ask",
      "when_unknown": "handoff"
    }
  ]
}
```

주의:

- `request_examples`는 단순 키워드 일치가 아니라 LLM 분류 후보 또는 향후 임베딩 검색의 예시다.
- 서버는 LLM이 매칭한 규칙 ID가 실제 활성 규칙인지, 선택지가 정책과 일치하는지 검증한다.
- 정책 자체가 문서 근거를 가지지 않으면 관리자에게 경고하고 공개를 막는다.
- `when_unknown=handoff`는 근거 부족인데도 일반 답변을 만들어 내지 않도록 한다.

## 다음 구현 권장 순서

1. 관리자 UI와 API 스키마의 정책 JSON 계약을 합의한다.
2. Bot에 `clarification_policy` JSON 컬럼을 추가하는 마이그레이션과 CRUD를 만든다.
3. 관리자 화면에 목록 + 4단계 rule editor + 초안/활성 상태를 만든다.
4. `ClarificationService`에 정책 evaluator를 넣는다.
   - 첫 요청에서 LLM/RAG가 규칙 후보와 현재 제공된 slot 값을 낸다.
   - 활성 규칙의 required slot이 비었으면 서버가 카드 상태를 강제한다.
   - 최대 3개 질문 제한은 현재 UI 계약을 유지한다.
5. 규칙 매칭·누락 slot·문서 참조를 응답의 진단 필드 및 서버 로그에 남긴다. 사용자 화면에는 보여 주지 않는다.
6. 현재 10문항 중 관리자가 `expected=ask`로 승인한 문항을 회귀 테스트에 넣는다.

## 다음 세션용 프롬프트

```text
이 저장소의 D-1 v2 맥락 보완 2차 작업을 이어서 구현해줘.

먼저 docs/architecture/clarification-policy-admin-handoff-2026-08-03.md를 끝까지 읽고, 현재 dirty worktree의 관련 없는 변경은 절대 되돌리거나 정리하지 마.

목표는 관리자가 관리자 봇 편집 화면에서 “추가 확인 질문 정책”을 직접 설정하게 만드는 것이다. 개발자가 업무별 필수 질문을 하드코딩하지 않도록 한다.

구현 범위:
1. Bot별 clarification_policy JSON 계약·DB 마이그레이션·백엔드 CRUD/API를 만든다.
2. frontend-admin의 봇 편집 화면에 정책 사용 토글, 규칙 목록, 4단계 rule editor, 초안/사용 시작, 테스트 미리보기 UI를 만든다.
3. 정책 규칙은 이름, 요청 예시, 질문이 필요한 이유, 문서 참조, required_slots(최대 3), 각 질문의 선택지/직접입력, when_missing/when_unknown을 지원한다.
4. ClarificationService는 첫 요청에서 정책 후보를 평가하고, 활성 규칙의 required slot이 비었으면 LLM이 ready를 선택해도 ask 카드를 우선한다. 정책이 없는 일반 요청은 현행 Interactions + File Search 계획 경로를 유지한다.
5. 문서 근거·정책 무결성·권한·최대 질문 수를 서버에서 검증하고, 단위/API/UI 테스트를 추가한다.
6. D-1 원격 프로필은 읽기 전용으로 유지한다. 마이그레이션은 로컬 개발 DB에서만 검증하고 원격 DB에는 적용하지 않는다.

관리자 UI 문구에는 LLM/RAG/JSON 같은 내부 표현을 노출하지 말고, “추가 확인 질문”, “필수 확인 항목”, “근거 문서”, “테스트하기” 같은 표현을 사용한다.

작업 전 간단한 구현 계획과 마이그레이션 영향 범위를 먼저 설명하고, 구현 후 backend/.venv/bin/pytest -q 및 pnpm --dir frontend-admin lint, pnpm --dir frontend-client lint를 실행해줘.
```

