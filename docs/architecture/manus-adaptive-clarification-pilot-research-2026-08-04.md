# 적응형 추가 확인 질문 파일럿 — Anthropic·Manus 공식 근거 부록

> 2026-08-04 조사. 코드 변경 없음. 이 문서는 20개 사례 파일럿의 **검증 가능한
> 설계 요건**만 정리한다. ‘20개’라는 표본 수와 세부 성공 기준은 프로젝트의 운영 결정이며,
> 아래 제공사들이 권고한 숫자는 아니다.

## 공식 자료에서 확인한 요건

| 요구사항 | 공식 자료에서 확인한 사실 | 20개 사례 파일럿에서 확인할 산출물 |
|---|---|---|
| 질문은 기본 동작으로 강제하지 않는다 | Manus의 Plan Mode는 사용자가 수동으로 켜는 모드다. 맥락이 부족하면 질문하지만, 경로가 분명하면 바로 계획을 제시한다. | 각 사례에 `즉시 안내` 또는 `함께 정리하기` 진입 방식을 명시하고, 모든 사례에 첫 질문을 강제하지 않는다. |
| 복잡한 작업은 실행 전 사용자의 확인 지점을 둔다 | Manus Plan Mode는 목표·단계·제약을 구조화해 보이고, 사용자가 확인하거나 취소하기 전에는 작업을 시작하지 않는다. | 맞춤 안내/다음 행동이 필요한 사례는 첫 질문 또는 짧은 계획 뒤에 사용자가 계속 진행할지 선택할 수 있어야 한다. |
| 즉답과 자율 작업의 UX를 구분한다 | Manus는 즉답·토론용 Chat Mode와, 지시를 기반으로 계획·완료하는 Agent Mode를 구분한다. | 20개 사례는 ‘문서 기반 일반 안내’와 ‘다단계 개인화 안내’를 구분해 기대 경로를 기록한다. |
| 질문할 공백과 내부적으로 해결할 공백을 구분한다 | Anthropic은 에이전트가 조사로 해결 가능한 공백도 있지만, 사용자만 결정할 수 있는 선호·의도 공백도 있다고 설명한다. 또한 너무 자주 묻는 것과 무조건 진행하는 것 모두 문제라고 명시한다. | 사례별로 `문서 검색으로 해소 가능`, `사용자 의도/선호 필요`, `담당자 판단 필요`를 구분해 기대 경로의 이유로 남긴다. |
| RAG 근거와 사용자 맥락을 같은 신호로 취급하지 않는다 | Anthropic의 검색 결과 기능은 RAG에서 사용자 문서에 출처를 붙여 답변하도록 한다. 이는 문서 근거를 제공하는 기능이다. | 각 사례는 검색 근거 문서와 별도로, 답변을 실제로 바꾸는 사용자 정보가 있는지 기록한다. 인용이 있다는 이유만으로 질문을 생략했다는 판정은 내리지 않는다. |
| 매 턴 전달하는 맥락을 선별한다 | Anthropic은 시스템 지침·도구·외부 데이터·대화 이력을 포함한 전체 맥락을 매 추론에서 선별해야 하며, 컨텍스트는 유한한 자원이라고 설명한다. | 다회차 사례의 트레이스에는 이전 답변 전체를 무분별하게 누적하지 않고, 확정된 사용자 답·현재 질문·관련 근거만 다음 단계 입력으로 전달했는지 기록한다. |
| 프롬프트가 아니라 실행 구조 전체를 평가한다 | Anthropic은 에이전트 평가에서 모델뿐 아니라 도구 호출·오케스트레이션을 포함한 harness, 전체 transcript, 환경의 최종 outcome을 평가 대상으로 정의한다. | 사례별로 최초 라우팅, 검색 근거, 질문/선택지, 사용자 응답 반영, 최종 경로, 오류·폴백을 한 트레이스로 보존한다. |
| 비결정성을 고려해 반복 실행한다 | Anthropic은 모델 출력이 가변적이므로 한 task를 여러 trial로 실행해 더 일관된 결과를 얻는다고 설명한다. | 20개 각 사례를 단일 실행 결과로 합격 처리하지 않고, 반복 trial 수와 경로별 결과를 함께 기록한다. |

## 파일럿의 최소 사례 카드

아래 항목은 위 요구사항을 검증하기 위해 각 사례에 보관해야 하는 최소 기록이다. 의도나
선호의 정답을 모델이 추정하도록 두지 않고, 평가자가 기대 경로를 사전에 판정할 수 있게 한다.

```text
case_id
사용자 최초 요청
선택한 UX: 즉시 안내 | 함께 정리하기
기대 경로: answer | optional_ask | blocking_ask | abstain | handoff
검색으로 해소 가능한 공백
사용자에게만 물어야 하는 공백
답변을 바꾸는 이유
허용 근거 문서/인용
반복 trial별 transcript 및 outcome
```

## 범위 제한

- 이 자료들은 특정 모델이 항상 질문을 생성하거나, RAG가 있을 때 반드시 카드를 띄운다고
  보장하지 않는다.
- 따라서 파일럿의 합격 판단은 카드 발생률이 아니라, 사전 기대 경로와 실제 경로의 일치,
  질문의 필요성, 근거 문서와 최종 outcome을 함께 검토해 내려야 한다.
- 정식 업무에서 반드시 받아야 하는 개인정보·자격·승인 정보의 서버 강제 계약은 위 제품
  설명만으로 대체할 수 없다. 해당 요구는 별도 업무 정책/권한 설계로 명시해야 한다.

## 1차 출처

- [Manus — Introducing Plan Mode](https://manus.im/blog/manus-plan-mode)
- [Manus Help Center — Chat mode와 Agent mode의 차이](https://help.manus.im/en/articles/11711128-what-are-the-differences-between-chat-mode-and-agent-mode)
- [Anthropic — Trustworthy agents in practice](https://www.anthropic.com/research/trustworthy-agents)
- [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Claude Platform — Search results for RAG](https://platform.claude.com/docs/en/build-with-claude/search-results)
- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
