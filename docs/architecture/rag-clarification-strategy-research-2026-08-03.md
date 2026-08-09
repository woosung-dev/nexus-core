# RAG 추가 확인 질문 전략 조사 — 부모동행 적용 제안

> 2026-08-03 조사. 구현 변경 없음. OpenAI·Anthropic·Manus·Azure·AWS·Google의
> 1차 자료와 현재 D-1 v2 PR의 실측 결과를 함께 검토했다.

## 결론

관리자가 모든 질문 정책을 수동으로 정의하는 방법만 있는 것은 아니다. 다만 **개인 상황에
따라 결론이나 다음 행동이 달라질 때, 그 개인 정보를 반드시 받아야 한다는 보장**은 프롬프트
하나로 만들 수 없다. 그 필요 정보는 결국 다음 셋 중 하나로 선언·검수되어야 한다.

1. 관리자 정책(현재 PR 방식)
2. 업무 액션의 필수 파라미터 계약
3. 문서에서 추출하고 관리자가 검수한 결정 스키마

일반 Q&A까지 전부 카드로 막는 것은 권장하지 않는다. 부모동행에는 아래의 **혼합형**이 맞다.

```text
사용자 요청
  ├─ 즉시 안내: 일반 설명·정의 → RAG 근거 답변
  ├─ 동행/맞춤 안내: 선택적으로 1~2회 확인 → 맞춤 RAG 답변
  └─ 고위험·업무 실행: 필수 항목 없으면 서버가 차단 → 카드 또는 담당자 연결
```

정책은 세 번째 경로의 안전장치로 남기고, 두 번째 경로는 `검색 → 충분성 판정 → answer | ask |
abstain`이라는 별도 컨트롤러로 운영하는 것이 현실적이다.

## 이번 실측이 보여 준 것

`E_부모동행v6` 원문, 봇 11, `clarification_policy={"enabled": false, "rules": []}`로 50문항을
실행했다. 결과는 `ready` 49, `ask` 1, `fallback` 21, 오류 0이었다.

- `ask`는 A-304 한 건뿐이며 기존 LLM 카드이고 필수가 아니다.
- 28건은 모델이 직접 `answer`를 골라 `ready`가 됐다.
- 21건은 계획 생성/정정 실패 또는 공급자 실패 뒤 안전 폴백으로 `ready`가 됐다.
- 이 실험은 최종 문서 답변을 호출하지 않았다. `ready`는 “다음 답변 단계로 진행 가능”이라는
  계획 상태이지 최종 답변 자체가 아니다.

현재 [`clarification_service.py`](../../backend/app/services/clarification_service.py)에서는 활성
정책이 없으면 모델의 `ask | answer` 선택만 따른다. 그리고 계획 생성 실패 시
`_ready_response("fallback", ...)`로 넘어간다. 따라서 **현재의 카드 발생률은 ‘사용자에게
정보가 충분한가’가 아니라 모델의 자율 판단과 실패 폴백에 크게 좌우된다.** 50문항 결과로
추가 질문 UX의 품질을 결론 내리기 어렵다.

추가로 현재 한 호출은 자연어 `[EVIDENCE]`와 `[PLAN]` JSON을 함께 요구하고, 후단에서 JSON을
파싱한다. 모델 출력 형식 실패가 그대로 `ready` 폴백으로 이어질 수 있어, 질문 여부의 의미적
판정과 출력 형식 실패를 분리해 계측할 필요가 있다.

## 업계 자료에서 확인한 패턴

### 1. RAG는 ‘사용자에게 묻기’가 아니라 ‘내부 검색을 더 잘하기’에 가깝다

Azure Agentic Retrieval은 대화 이력으로 focused subquery를 만들고, 병렬 검색·semantic
rerank·결과 병합을 수행한다. AWS Bedrock도 복합 질의를 subquery로 분해하고 반복 검색해
근거가 충분한지를 평가한다. 이들은 문서 용어와 복합 질의를 먼저 **내부적으로** 해소하는
검색 전략이다. 사용자의 자격, 실제 진행 단계, 선호처럼 문서에 없는 사실은 검색으로 채울 수
없다.

- [Azure Agentic Retrieval 개요](https://learn.microsoft.com/en-us/azure/search/search-agentic-retrieval-concept)
- [AWS Bedrock: retrieval·generation 분리와 agentic retrieval](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-retrieval.html)
- [Google Agent Search: 대화형 답변·query rephrase](https://docs.cloud.google.com/generative-ai-app-builder/docs/answer)

따라서 “RAG를 붙이니 질문을 안 한다”는 현상은 이상하지 않다. 검색 근거가 있으면 모델은
일반 설명을 할 수 있다고 판단하기 쉽다. **문서 근거 충분성**과 **개인화 답변을 위한 사용자
정보 충분성**은 별도의 신호다.

### 2. 질문은 보통 ‘실행 전 정렬’ 또는 ‘모호한 의도’에만 쓴다

Manus는 즉답용 Chat과 자율 작업용 Agent를 구분한다. Plan Mode도 자동으로 모든 대화에
개입하지 않는 수동 모드이며, 맥락이 부족하면 질문하고 경로가 분명하면 계획을 제시한 뒤
사용자 확인 전에는 실행하지 않는다. Claude의 공개 연구 역시 작업이 복잡해질수록 명확화
질문이 늘어나지만, 불필요한 질문은 사용성을 해친다고 명시한다.

- [Manus Plan Mode](https://manus.im/blog/manus-plan-mode)
- [Manus Chat Mode와 Agent Mode](https://help.manus.im/en/articles/11711128-what-are-the-differences-between-chat-mode-and-agent-mode)
- [Anthropic: 실제 에이전트 자율성과 명확화 질문](https://www.anthropic.com/research/measuring-agent-autonomy)

이는 ‘모든 RAG 질문을 먼저 카드로 막는다’보다 **즉답 모드와 동행/계획 모드를 분리**하라는
강한 근거다.

### 3. 모델 출력 구조화는 필요하지만, 질문의 타당성을 보장하지 않는다

OpenAI는 function calling/Structured Outputs로 앱이 모델 출력의 JSON Schema를 엄격히
받고, 앱이 상태 전이·도구 호출·재시도를 소유하는 구조를 제시한다. 그러나 스키마는 형식과
enum을 보장할 뿐 “지금 질문해야 하는가”라는 의미 판단의 정답을 보장하지 않는다.

- [OpenAI: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI: function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI: agent 설계와 guardrail](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)

그러므로 질문 생성 모델과 서버 상태기계는 분리해야 한다. LLM은 후보를 내고, 서버는 근거,
허용 값, 대화 상태 및 위험도를 검증해 카드/답변/연결을 결정한다.

### 4. 검색 품질을 올리는 일과 질문 제어는 함께 필요하다

Anthropic은 contextual retrieval, BM25와 embedding의 결합, reranking을 통해 검색 실패를
낮추는 방법을 제시한다. Azure와 AWS도 query decomposition과 reranking을 제공한다. 검색
품질을 올리면 문서 용어의 모호성으로 생기는 불필요한 사용자 질문은 줄어든다. 반면 개인
상황의 빈칸은 여전히 질문 또는 일반 답변으로 명시해야 한다.

- [Anthropic: Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
- [AWS Bedrock reranking](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank.html)
- [Azure의 hybrid/RRF 점수 임계값 주의](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query)

특히 검색 점수 하나로 카드 여부를 정하면 안 된다. Azure는 hybrid RRF 점수가 작고 변동성이
있어 minimum threshold에 적합하지 않다고 설명한다. 근거 coverage, citation support,
답변 완결성, 위험도, 사용자의 실제 빈칸을 합쳐야 한다.

## 가능한 선택지

| 방식 | 질문 품질/보장 | 운영 부담 | 부모동행에서의 용도 |
|---|---|---:|---|
| 프롬프트만 강화 | 낮음 / 보장 없음 | 낮음 | 저위험 실험용; 이상한 질문 재발 가능 |
| 모델 기반 answerability router | 중간 / 보장 없음 | 중간 | 일반 맞춤 안내의 기본 경로 |
| 수동 관리자 정책 | 높음 / 강제 가능 | 높음 | 고위험·반복 업무 경로 |
| 업무 액션 schema | 높음 / 강제 가능 | 중간 | 신청·서류·자격·상담 연결 |
| 문서 유래 schema 초안 + 승인 | 높음 / 강제 가능 | 초기 중간, 이후 낮음 | 규정집의 반복 절차를 넓게 커버 |
| 수동 ‘동행 모드’ | 사용자 제어가 높음 | 낮음 | 복잡한 개인 상담의 진입점 |

AWS Agents는 action/OpenAPI 파라미터를 required로 선언하고, 누락된 파라미터를 사용자에게
다시 묻는 방식을 제공한다. 이는 질문마다 정책을 쓰는 대신 업무별 계약을 정의하는 방식이다.

- [AWS: action group 정의](https://docs.aws.amazon.com/bedrock/latest/userguide/action-define.html)
- [AWS: 누락 파라미터 사용자 입력](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-user-input.html)

## 부모동행 권장 구조

### A. 먼저 고쳐야 할 기반: `unknown`을 `ready`로 숨기지 않는다

계획 모델의 timeout, provider 오류, JSON 파싱 오류는 의미상 “답변 가능”이 아니다. 응답
상태를 최소한 아래 네 개로 분리한다.

```text
answer   문서·입력만으로 일반/맞춤 답변 가능
ask      문서에 근거한 사실 하나가 빠져 답이나 다음 행동이 달라짐
abstain  검색·계획이 불충분하여 정확한 카드도 만들 수 없음
handoff  민감도·업무 위험도 때문에 담당자 확인 필요
```

`abstain`은 고위험이면 담당자 연결, 저위험이면 “일반 설명만 제공” 또는 “상황에 맞게 확인하기”를
보여 준다. 현재 21건 같은 실패를 최종 답변 경로로 보내지 않는 것이 첫 번째 변경이다.

### B. 정책 없는 기본 경로: retrieval-aware adaptive gate

1. **검색 정제**: 대화 이력으로 query rewrite 또는 2~3개 subquery를 만들고 hybrid retrieval과
   rerank를 수행한다. 이 단계는 문서 내 용어 모호성을 사용자에게 묻기 전에 해소한다.
2. **작은 구조화 컨트롤러**: 검색 근거와 이미 받은 canonical slot을 입력으로 받아 아래만
   출력한다.

   ```json
   {
     "route": "answer | optional_ask | blocking_ask | abstain | handoff",
     "intent": "definition | procedure | personalized_guidance | safety | unknown",
     "missing_facets": [{"id":"...", "why_changes_answer":"...", "evidence_ids":["..."]}],
     "assumptions": ["..."]
   }
   ```

3. **서버 검증**: card는 (a) 근거 문서가 현재 retrieval에 있고, (b) 빠진 값이 실제로 결론이나
   다음 행동을 바꾸며, (c) 사용자가 답할 수 있고, (d) 이미 대화/프로필에 없는 경우에만 허용한다.
4. **한 번에 한 질문**: 정보 가치가 가장 큰 한 항목부터 묻고, 답을 canonical state에 저장한 뒤
   다시 판정한다. 최대 2회 후 answer·handoff 중 하나로 종료한다. 처음부터 3개 카드를 모두
   만들 필요는 없다.

이 방식은 관리자가 50개 문항별 규칙을 쓰지 않아도 되지만, 모델의 분류 오차가 남는다. 따라서
필수 보장이 필요한 경로에는 다음 C를 적용한다.

### C. 강제 보장 경로: ‘주제별 정책’보다 작은 업무 계약

`personalized_guidance`, `application_check`, `document_check`, `counselling_referral`처럼 안정적인
업무 intent 몇 개를 만든다. 각 intent에만 필수 slot과 handoff 조건을 선언한다. 예를 들면
“신청 자격 판단”은 절차 단계와 대상 구분을 받기 전에는 맞춤 결론을 내리지 않는다.

현재 PR의 `clarification_policy`는 이 경로에 적합하다. 다만 문항별로 늘리는 대신,

- 규정 문서에서 ‘결론을 바꾸는 조건·선택지·근거 span’을 추출해 **초안 schema**로 만들고,
- 관리자는 초안을 검수·활성화하며,
- 런타임에는 서버가 문서 소유·선택지·응답을 검증한다.

이렇게 하면 작성 비용을 줄이면서도 강제의 근거와 감사 가능성은 남긴다.

### D. UX: 기본 ‘즉시 안내’ + 선택 ‘함께 정리하기’

일반 질문은 근거 있는 개괄 답변을 즉시 제공한다. 개인 상황 적용이 필요하면 답변 끝에
`내 상황에 맞춰 확인하기`를 둔다. 사용자가 누르면 동행 모드가 시작되어 한 질문씩 받고,
짧은 계획/가정/다음 단계를 보여 준다. Manus의 수동 Plan Mode와 같은 원리로, 단순 질문을
불필요하게 막지 않으면서 복잡한 상담에는 명시적 합의를 만든다.

고위험 업무나 안전 이슈는 이 선택을 기다리지 않고 C의 hard gate 또는 handoff로 보낸다.

## 프롬프트·대화 상태는 어떻게 써야 하나

‘첫 질문에 시스템 프롬프트를 넣고, 둘째·셋째 답변을 따라가게’ 하는 방식은 유효하지만,
프롬프트만으로 결정하지 않는다.

- 시스템 프롬프트는 모든 턴에 역할·안전·말투·답변 근거 기준으로 유지한다.
- controller state는 별도로 보관한다: `intent`, `route`, `filled_slots`, `missing_facets`,
  `pinned_evidence`, `assumptions`, `turn_count`.
- 사용자의 자유 텍스트는 slot extractor가 canonical value로 정규화하고 서버가 허용 값을
  검증한다.
- retrieval은 매 턴 전체를 다시 넓게 검색하기보다, 첫 턴의 근거를 pin하고 변경된 slot에
  필요한 경우만 재검색한다. 비용과 drift를 줄인다.
- 모호한 상황에서 모델이 임의로 가정을 만들어 답하는 대신, 가정을 노출하고 사용자가 수정할
  수 있게 한다.

OpenAI는 다회차를 conversation state와 앱 소유의 loop로 다루며, Anthropic은 매 턴의 지시·도구·
외부 데이터·대화 이력을 선택적으로 구성하는 context engineering을 권고한다.

- [OpenAI: conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [Anthropic: effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

## 검증 계획

카드 발생률을 성공 지표로 쓰지 않는다. 기존 50문항에 각 항목의 기대 경로를 먼저 라벨링한다.

```text
expected_route: answer | optional_ask | blocking_ask | abstain | handoff
answer-changing facets: []
허용 근거 문서/문단: []
```

각 후보 구조를 최소 3회씩 실행하고 다음을 분리해 측정한다.

- blocking ask recall: 반드시 물어야 하는 문항을 놓치지 않는가
- ask precision: 불필요하거나 도메인 밖인 질문을 만들지 않는가
- facet/선택지 근거성: 질문과 선택지가 현재 검색 문서에 실제로 있는가
- answer completeness·faithfulness·citation precision/coverage
- 1·2턴 완료율과 카드 이탈률
- `abstain`/handoff 정당성
- 계획 파싱 실패, provider timeout, fallback 비율 및 p95 latency

AWS도 retrieval context relevance/coverage와 response completeness/helpfulness/faithfulness/citation
precision/coverage를 분리한 RAG 평가 지표를 제공한다. Anthropic도 agent 평가에서 모델뿐 아니라
도구 호출과 orchestration을 포함한 trace 및 여러 trial을 평가하라고 권고한다.

- [AWS Knowledge Base 평가 지표](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-metrics.html)
- [Anthropic: agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

## 권장 실행 순서

1. **현재 generic planner의 실패 상태를 분리**한다. `fallback → ready`를 먼저 없애고,
   원인별 trace를 남긴다.
2. **50문항을 기대 경로로 라벨링**한다. 이 단계 없이 “카드를 많이 띄웠다”는 개선이 될 수 없다.
3. **즉시 안내/동행 모드 UX**를 작은 실험으로 만든다. 사용자 선택이 가능한지와 이탈률을 본다.
4. **retrieval-aware controller**를 shadow mode로 돌려 기존 답변과 비교한다. 아직 카드를
   사용자에게 강제하지 않는다.
5. **고위험 업무 intent만** action schema 또는 현재 정책으로 hard gate한다.
6. 문서 업데이트가 잦거나 절차가 반복되면 **문서 유래 schema 초안 + 관리자 검수**를 도입한다.

이 순서라면 모든 것을 관리자 정책으로 만들지 않고도 질문 품질을 개선할 수 있다. 동시에
정확성이 반드시 필요한 업무에서는 선언적 계약으로 안전한 강제를 유지한다.
