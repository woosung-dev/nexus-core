# RAG·LLM 맥락 보완 구현 핸드오프 (2026-08-03)

## 다음 작업의 목표

`테스트 봇 D-1 ver2`(봇 ID `11`)의 인라인 맥락 보완 프로토타입을 아래 방식으로 완성한다.

- 첫 요청에서만 **Gemini 3.5 Flash-Lite + File Search**를 호출한다.
- LLM이 RAG 근거와 사용자 요청을 보고 `ask` 또는 `answer`를 스스로 결정한다.
- `ask`이면 필요한 질문을 최대 3개, **한 개의 인라인 카드**로 반환한다.
- 사용자가 카드에 답한 뒤에는 추가 질문용 LLM 호출을 하지 않는다.
- 확정 또는 건너뛴 요약으로 최종 RAG 답변을 한 번 생성한다.
- 질문 여부를 운영 규칙으로 강제하지 않는다. 서버는 출력 형식과 근거만 검증한다.

## 이미 합의된 제품 원칙

1. 문서에 없는 행사·절차·서류·신고·자격 명칭을 LLM이 그럴듯하게 조합해 선택지로 만들면 안 된다.
2. `가정출발이 뭐야?`처럼 현재 질문만으로 문서 기반 일반 설명이 가능한 경우, LLM이 `answer`를 선택할 수 있다.
3. `1세/2세 축복`처럼 사용자 상황에 따라 실제 안내가 달라지는 경우에는 LLM이 `ask`를 선택할 수 있어야 한다.
4. 선택지 기반 질문에는 `기타 / 직접 입력` 경로를 제공한다.
5. 프로토타입에서는 ChatSession/Message를 저장하지 않는다.

## 현재 구현 상태

### 주요 코드

| 파일 | 역할 |
|---|---|
| `backend/app/services/clarification_service.py` | 첫 요청의 LLM `ask/ready` 판정과 질문 생성 |
| `backend/app/services/rag/gemini.py` | `generate_structured_with_rag()` — File Search를 붙인 단일 Gemini 호출 |
| `backend/app/schemas/clarification.py` | 맥락 보완 요청/응답 계약 |
| `backend/app/api/v1/endpoints/clarification_preview.py` | 비영속 프로토타입 API |
| `frontend-client/src/components/chat/ClarificationPrototype.tsx` | 선택된 인라인 카드 UX |
| `docker-compose.prototype.yml` | 격리된 로컬 프로토타입 환경 |
| `docker-compose.prototype.real-bot.yml` | 원격 D-1 DB·기존 File Search Store를 읽기 전용으로 참조하는 프로필 |

### 현재 동작

- `live_decision()`은 이미 봇의 `llm_model`(`gemini-3.5-flash-lite`)과 File Search를 사용해 단일 요청으로 `ask` 또는 `ready`를 받는다.
- 1회차 이후에는 `_ready_response()`로 요약만 만들므로, 카드 답변 후에 질문 생성용 모델 호출은 없다.
- 현재 UI는 `http://localhost:3201/chat/new/11?clarify-prototype=1`에서 로그인 없이 확인할 수 있다.
- 실제 D-1 RAG 답변은 같은 봇의 기존 File Search Store를 사용하며, 원격 DB에는 읽기만 수행한다.

## 확인된 문제

### 1. 정상 `ask` 결과가 폴백으로 사라짐

실제 D-1 요청에서 Gemini가 질문을 반환했지만 현재 Pydantic 계약과 모양이 달랐다.

- 질문 텍스트 필드가 `question`이 아닌 다른 이름(실측상 `title` 계열)으로 반환될 수 있다.
- 선택지가 문자열 배열이 아니라 `{ "label": "…", "value": "…" }` 배열로 반환될 수 있다.
- 이 경우 `_LiveDecision` 검증 실패 → `fallback` → 사용자에게 "LLM 판정이 실패"가 보인다.

다음 구현에서 **원시 모델 결과를 먼저 정규화**해야 한다.

```text
question.title → question.question
option.label   → UI에 표시할 option 문자열
option.value   → 선택값 식별자로 보존하거나, 프로토타입에서는 생략
```

정규화 후에만 `ClarificationQuestion` Pydantic 모델로 검증한다. 유효하지 않은 결과는 한 번만 재생성하도록 할 수 있으며, 재시도도 실패하면 카드 대신 원 요청의 RAG 답변으로 안전 전환한다.

### 2. `ask`가 카드로 이어지지 않는 조건

현재 `live_decision()`은 아래 조건을 만족할 때만 질문 카드를 반환한다.

```python
if decision.status == "ask" and decision.questions and citations:
```

구조화된 계획 응답은 사실 문장을 직접 답하지 않아 `grounding_metadata` 인용이 비어 있을 수 있다. 이 조건 때문에 LLM이 `ask`를 선택해도 `ready`로 바뀔 수 있다.

다음 구현에서는 질문별 근거를 계약에 포함하고, 응답의 grounding metadata와 대조하는 검증을 설계한다. 근거를 확인할 수 없는 `ask`는 임의의 질문을 노출하지 않는다.

### 3. Gemini SDK 호환성

현재 프로젝트의 `google-genai==2.10.0` + `generateContent` 경로에서 File Search와 `response_schema`/JSON MIME 설정을 함께 사용한 실제 요청은 약 150초 뒤 시간 초과됐다. 그래서 현재는 프롬프트로 JSON을 요청하고, 코드 펜스를 벗긴 뒤 Pydantic으로 검증한다.

Google 최신 문서는 Gemini 3 계열에서 File Search와 Structured Output 결합을 안내한다. 다음 구현에서 SDK 업그레이드 또는 Gemini Interactions API 전환을 별도로 검토할 수 있지만, 현재 작업의 필수 조건은 아니다.

## 권장 구현 설계

### `ClarificationPlan` 계약

현재의 `ClarificationPreviewResponse`에 바로 모델 결과를 맞추지 말고, 아래와 같은 계획 계약을 둔다.

```json
{
  "decision": "ask",
  "reason": "축복 유형과 현재 단계에 따라 문서상 안내가 달라집니다.",
  "questions": [
    {
      "id": "blessing_type",
      "title": "어떤 축복 관련 안내가 필요하신가요?",
      "selection_mode": "single",
      "options": [
        { "label": "1세 축복", "value": "first_generation" },
        { "label": "2세 축복", "value": "second_generation" },
        { "label": "잘 모르겠어요", "value": "unknown" }
      ],
      "allow_custom": true,
      "evidence": ["현재 검색 결과의 인용 식별자"]
    }
  ],
  "answer_outline": null
}
```

`decision = answer`는 **현재 사용자 요청과 검색 문서만으로 정확한 최종 답변을 만들 수 있을 때만** 허용한다. 검색 결과가 약함, 질문을 찾지 못함, JSON 형식 오류는 `answer`의 이유가 아니다.

### 처리 순서

```text
사용자 최초 요청
  → Gemini 3.5 Flash-Lite + File Search (정상 경로 1회)
  → 원시 ClarificationPlan 정규화
  → 스키마·최대 3개·중복·질문별 근거 검증
      ├─ ask    : 질문들을 인라인 카드 한 장에 표시
      ├─ answer : 바로 답변 또는 답변 확인 단계로 진행
      └─ invalid: 1회 교정 재시도 후, 원 요청 RAG 답변으로 안전 전환
  → 사용자 답변/직접 입력
  → 최종 RAG 답변 (1회)
```

정상적인 `ask` 흐름의 최초 계획 호출은 하나다. 재시도는 형식·근거 검증 실패 때만 예외적으로 한 번 허용한다.

## 다음 구현 작업 순서

1. `ClarificationPlan` 원시 스키마와 정규화 함수를 추가한다.
2. `title/question`, 문자열 옵션/`label,value` 옵션을 모두 정규화한 뒤 기존 UI 계약으로 변환한다.
3. 프롬프트를 `ask | answer`, 질문별 이유·근거, 최대 3개라는 계약으로 구체화한다.
4. `ask` 결과의 근거 검증 및 1회 교정 재시도 규칙을 구현한다.
5. UI에서 "LLM 판정 실패", "RAG" 같은 내부 상태 문구는 최종 사용자 노출에서 제거한다. 프로토타입 상태 표시는 개발용으로만 남긴다.
6. 단위 테스트와 실제 D-1 봇 테스트를 수행한다.

## 권장 테스트 케이스

| 입력 | 기대 결과 |
|---|---|
| `가정출발이 뭐야?` | LLM이 `answer`를 선택하거나, 질문 없이 바로 문서 기반 답변으로 진행 |
| `축복 이후 가정출발에 대한 절차가 있어?` | 문서만으로 일반 절차가 충분하면 `answer`; 개인 상황이 답을 바꾸면 `ask` |
| `2세 친구와 교류 중인데, 축복을 받기 위해 무슨 절차가 있어?` | 문서상 1세/2세·현재 단계 분기가 있을 때 1~3개 질문. 형식 오류·폴백 없이 카드 표시 |
| LLM이 `title`과 `{label,value}`를 반환 | 정규화 후 질문 카드 표시 |
| LLM이 근거 없는 절차명을 반환 | 카드 미표시, 재시도 또는 안전 전환 |

## 실행 및 검증 명령

### 단위 테스트와 프런트 린트

```bash
cd backend
.venv/bin/pytest -q
pnpm --dir ../frontend-client lint
```

### 실제 D-1 ver2 프로토타입 실행

원격 DB와 실제 File Search Store를 **읽기 전용**으로 사용한다. 마이그레이션, 문서 업로드, 채팅 저장을 하지 않는다.

```bash
set -a
source backend/.env
set +a

NEXUS_REAL_BOT_DATABASE_URL="$DATABASE_URL" \
NEXUS_REAL_BOT_FILE_SEARCH_STORE_NAME="${FILE_SEARCH_STORE_NAME:-nexus-core-knowledge-base}" \
docker compose -p nexus-clarification \
  -f docker-compose.yml \
  -f docker-compose.prototype.yml \
  -f docker-compose.prototype.real-bot.yml \
  up -d --build --force-recreate api client
```

테스트 URL: `http://localhost:3201/chat/new/11?clarify-prototype=1`

격리된 로컬 scratch 프로필로 되돌릴 때:

```bash
docker compose -p nexus-clarification \
  -f docker-compose.yml \
  -f docker-compose.prototype.yml \
  up -d --force-recreate api client
```

## 작업 트리 주의사항

- 현재 작업 트리에는 이번 프로토타입 변경 외에도 사용자의 기존 변경·문서가 섞여 있다.
- 특히 `backend/uv.lock`, `frontend-client/src/components/chat/ChatArea.tsx`, 여러 `syste-prompt-ver/` 문서는 이 작업과 무관한 변경일 수 있다.
- 무관한 변경을 되돌리거나 하나의 커밋에 포함하지 않는다.

## 참고 조사

- [RAG·LLM 기반 맥락 보완 워크플로우 조사](rag-llm-clarification-workflow-research-2026-08-03.md)
- [Gemini File Search 공식 문서](https://ai.google.dev/gemini-api/docs/file-search)
- [Gemini Structured Output 공식 문서](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)

## 다음 세션 재개 프롬프트

```text
docs/architecture/clarification-plan-handoff-2026-08-03.md와
docs/architecture/rag-llm-clarification-workflow-research-2026-08-03.md를 먼저 읽어줘.

D-1 ver2 봇(ID 11)의 인라인 맥락 보완 프로토타입을 이어서 구현해줘.
동일 Gemini 3.5 Flash-Lite + File Search 한 번의 계획 호출에서 LLM이 ask | answer를
결정하게 하고, ask면 최대 3개 질문을 인라인 카드로 반환해야 해.

title/question 필드 차이와 {label, value} 선택지를 정규화하고, 질문별 근거 검증과
형식 오류 시 1회 교정 재시도를 추가해줘. 사용자 답변 뒤에는 추가 질문용 LLM 호출을
하지 말고 최종 RAG 답변만 생성해줘. 원격 DB는 읽기 전용으로 보존하고, 전체 테스트와
실제 D-1 테스트까지 진행해줘.
```
