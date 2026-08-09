# 적응형 재질문 — 열린 PR 정리와 다음 설계 제안 (2026-08-04)

> 대상: 축복 Q&A 봇(운영 1개). 기존 조사문서(`rag-clarification-strategy-research`,
> `manus-adaptive-clarification-pilot-research`)를 대체하지 않고, **PR #51 파일럿이 왜 흔들렸는지**와
> **이 도메인에 맞는 다음 구조**를 더한다. 외부 근거는 문서 끝에 모았다.

---

## 1. 열린 PR 4건

| PR | 상태 | 규모 | base | 한 줄 |
| --- | --- | --- | --- | --- |
| **#51** Add adaptive clarification pilot | Draft | +1575 / 19 files | `agent/admin-clarification-policy` | 서버 소유 5-way 라우팅(answer·optional_ask·blocking_ask·abstain·handoff) + 파일럿 러너. **라우팅 일관성 미달로 draft 고정** |
| **#50** Add admin clarification policies | Open | +3502 / 30 files | `main` | 봇별 관리자 재질문 정책(필수 슬롯·문서 소유 검증·저장 전 테스트 API) + 인라인 프로토타입 |
| **#38** glossary + clarify [스택 2/3] | Open | +1862 / 33 files | `feat/instruction-builder` | 용어집(증강 전용) + 경량 clarify 게이트. 2주 경과, 스택 PR |
| **#32** RAG interactions 단일호출 | Draft | +826 / 12 files | `main` | 실험 종료. **M2(2-호출) 유지가 옳다는 근거 기록용, 머지 금지** |

### 서로 어떤 관계인가

```
main
 ├── #50 정책 계약 (관리자 선언 → 서버 강제)
 │     └── #51 적응형 라우터 (모델 판단 → 서버 검증)
 ├── #38 (feat/instruction-builder 스택) 경량 clarify 분류기
 └── #32 (실험 종료 · 머지 안 함)
```

**#50 → #51 은 "강제 계약"과 "자동 판단"이라는 서로 다른 층이고, 둘 다 필요하다.**
문제는 #51 이 자동 판단 층을 한 번의 LLM 호출에 전부 얹었다는 점이다.

### #32 는 지금 닫아도 된다

목적(검증)을 달성했고 결론이 명확하다 — 단일 interactions 호출은 인용과 품질을 동시에 얻지 못한다
(인용지시 ON: 정확도 50~55% → 46% 회귀 / OFF: 인용 0%). 근거는 `exports/rag_citation_audit_v2/REPORT.md`
에 남아 있으므로 PR 을 계속 열어 둘 이유는 없다.

---

## 2. #51 파일럿이 흔들린 이유

파일럿 결과: 안전 불변식은 지켰으나(`fallback → ready` 0건, 금지된 최종답변 호출 0건),
**기대 경로 대비 30/60 불일치, 카드 누락 13건**.

코드를 읽고 확인한 구조적 원인 넷.

### 2-1. 라우터 한 번의 호출이 다섯 가지 일을 한다

`adaptive_clarification_service.route_message()` 는 단일 `generate_structured_with_rag` 호출에
아래를 전부 요구한다.

1. File Search 검색
2. `[EVIDENCE]` 자연어 근거 서술
3. `[PLAN]` JSON(5-way route + facet + 선택지 + evidence_ids)
4. **봇 페르소나 시스템 프롬프트 전체**(`bot.system_prompt`)를 앞에 붙인 상태로
5. 관리자 정책 후보 매칭(`policy_match`)

CLAMBER(≈12K 케이스)는 LLM 이 **"지금 물어야 하는가"** 판정 자체를 잘 못하고, CoT·few-shot 은
한계 개선에 그치며 오히려 잘못된 확신을 준다고 보고한다. 그 어려운 판정에 검색·페르소나·정책까지
얹으면 분산이 커지는 것이 정상이다.

### 2-2. 페르소나가 라우터를 `answer` 쪽으로 민다

`_routing_system_prompt()` 는 `bot.system_prompt + 라우팅 규칙`이다. 축복 봇의 페르소나는
"따뜻하게 답하라"는 지시로 가득하다. 이 레포는 이미 **같은 현상을 실측한 적이 있다** —
페르소나가 grounding 보고를 억제해 인용이 0으로 찍히던 문제(`reference_rag_grounding_underreports`).
라우팅도 같은 경로를 탄다. **판정 호출에 페르소나를 넣으면 안 된다.**

### 2-3. 근거 검증 규칙이 ask 경로에만 불리하다

```python
if route in {"answer","optional_ask","blocking_ask"} and not _citation_ids(citations):
    raise AdaptiveRoutingValidationError("retrieval has no evidence")
...
if not evidence or any(item not in citation_ids for item in evidence):
    raise AdaptiveRoutingValidationError("facet evidence does not match retrieval")
```

계획 응답은 사실 문장을 직접 쓰지 않아 grounding 인용이 비기 쉽다(핸드오프 문서 §2 에 이미 기록됨).
즉 **모델이 옳게 `ask` 를 골라도 인용이 안 실리면 `abstain` 으로 떨어진다.** 카드 누락 13건의
유력한 설명이다. 반대로 `answer` 는 인용이 붙기 쉬워 통과한다 — 검증이 비대칭이다.

### 2-4. 하드코딩 가드가 테스트셋에 과적합돼 있다

```python
if _contains_any(message, ("교제축복",)):  # C-01 케이스
if _contains_any(message, ("오늘 서울 날씨", "날씨 어때", ...)):  # C-10 케이스
```

파일럿 20문항의 특정 케이스를 문자열로 잡고 있다. 파일럿 점수는 올라가지만 실트래픽에는 무력하고,
동시에 **파일럿이 측정하려던 것(일반화되는 라우팅)을 측정하지 못하게 만든다.**

---

## 3. 이 도메인에서 다시 봐야 할 전제

파일럿 20문항을 다시 읽으면 중요한 사실이 하나 나온다.

`blocking_ask` 기대였던 6건 중 A-93 · B-230 · B-244 는 **사용자가 이미 필요한 사실을 전부 진술했다.**

> B-244: "22살때 2세 축복을 받고 바로 가정출발… 남편이 교통사고로 성화… 30살에 혼자되어…
> 전도된 1세 청년과 재혼… 그 청년 사이에 자녀도 낳았어. 재혼한 상대와 은사축복을 받을 수 있을까?"

세대·축복 종류·절차 단계·배우자 상태·자녀 유무가 전부 들어 있다. 여기서 봇이 더 물을 것은 없다.
**부족한 것은 사용자 맥락이 아니라 "문서가 이 조합을 다루는가" 이다.**

즉 이 도메인의 지배적 실패는 *underspecification* 이 아니라 **coverage 와 단정 위험**이다.
Manus 식 "맥락이 부족하면 묻는다" 프레임을 그대로 이식하면, 이미 다 말한 사용자에게 다시 캐묻는
봇이 된다. 대화형 검색 연구가 경고하는 바로 그 지점 — **부적절한 질문은 차선의 답변보다 나쁘다.**

### 그래서 필요한 것은 6번째 경로다

| route | 언제 | 사용자에게 보이는 것 |
| --- | --- | --- |
| `answer` | 일반 설명·정의 | 근거 있는 답변 |
| **`conditional_answer`** ⭐신규 | 결론을 가르는 축이 있는데 **물으면 안 되거나 물을 필요가 없을 때** | "A인 경우 …, B인 경우 …" 갈림길 전부 + 각 근거 + 공식 확인 안내 |
| `optional_ask` | 개인 맞춤이 도움되나 일반 답변도 유효 | 답변 후 CTA → 눌러야 질문 1개 |
| `blocking_ask` | **관리자 정책 계약이 있는 업무 경로만** | 필수 카드 (모델 판단 아님) |
| `handoff` | 목회적·공식 판단 영역 | 담당자 연결 |
| `abstain` | 근거 없음 | 안내 불가 + 공식 자료 |

`conditional_answer` 는 종교 도메인에서 특히 중요하다. 성별실패 여부·건강 은폐·이혼 사유를
카드로 캐묻는 것은 정보 수집이 아니라 **정죄로 읽힌다.** 묻지 않고 갈림길을 다 보여주면
사용자가 스스로 자기 경우를 고르며, 봇은 개인을 단정하지 않는다.

---

## 4. 제안 구조 — LLM 은 추출만, 판정은 서버

### 4-1. 결정축 사전 (관리자 1회 정의)

규정집에서 **결론을 가르는 축**만 뽑아 닫힌 어휘로 만든다. 이 도메인은 축이 많지 않다.

| 축 ID | 값(enum) | 질문 정책 |
| --- | --- | --- |
| `generation` | 1세 / 2세 / 3세 | 물어도 됨 |
| `blessing_type` | 기성 / 독신 / 영육계 / 은사 / 재축복 | 물어도 됨 |
| `stage` | 매칭전 / 약혼 / 축복식후 / 40일정성중 / 가정출발후 | 물어도 됨 |
| `nationality` | 국내 / 국제 | 물어도 됨 |
| `children` | 있음 / 없음 | 물어도 됨 |
| `spouse_status` | 생존 / 성화 / 축복정리 / 이혼 | **민감** — 조건부 우선 |
| `condition_breach` | 40일 / 3일행사 / 없음 | **묻지 않음** |
| `health_disclosure` | 해당 / 비해당 | **묻지 않음 → handoff** |

각 축에는 **근거 문서 span** 을 붙이고 관리자가 승인한다. 이것이 기존 조사문서의
"문서 유래 schema 초안 + 관리자 검수"를 이 도메인 크기로 축소한 형태다.

### 4-2. 판정 파이프라인

```
1) 안전·경계 가드            결정론 (위기 / 프롬프트 추출 / 범위 밖)
2) 관리자 정책 매칭          결정론 (#50 의 계약 그대로)
3) 결정축 추출               LLM 1회 · 페르소나 없음 · closed enum · structured output
                             출력: {질문이 의존하는 축[], 사용자가 이미 말한 축:값[]}
4) 문서 커버리지 조회        축 조합 → 규정 span 존재 여부
5) 서버 규칙으로 route 결정  ← 여기서 LLM 을 쓰지 않는다
6) 질문이 필요하면 1개만     정보가치 최대 축 1개 (SAGE-Agent 의 EVPI 취지)
```

**5단계 규칙표**

| 의존 축 | 사용자 진술 | 문서 커버리지 | route |
| --- | --- | --- | --- |
| 없음 | — | 있음 | `answer` |
| 있음 | 전부 진술됨 | 있음 | `answer` (진술값 반영) |
| 있음 | 일부 미진술, 축이 **질문 가능** | 있음 | `optional_ask` (CTA 뒤 1개) |
| 있음 | 일부 미진술, 축이 **묻지 않음** | 있음 | `conditional_answer` |
| 있음 | — | 없음 | `handoff` |
| 정책 룰 매칭 | 필수 슬롯 누락 | — | `blocking_ask` |
| 근거 자체 없음 | — | 없음 | `abstain` |

### 4-3. 이 구조가 30/60 불일치를 구조적으로 없애는 이유

route 를 **LLM 이 고르지 않는다.** LLM 은 "이 질문이 어떤 축에 의존하는가 / 사용자가 무엇을
말했는가"만 닫힌 어휘로 추출한다. 이건 CLAMBER 가 어렵다고 한 판정이 아니라 **추출**이라
정확도가 훨씬 높고, 사람이 정답을 라벨할 수 있어 측정 가능하다.
같은 입력 → 같은 route 가 보장되므로 재현성 문제 자체가 사라진다.

---

## 5. 종교 도메인 전용 요구사항

### 5-1. 교리 층과 행정 층을 분리한다

| 층 | 예 | 처리 |
| --- | --- | --- |
| 행정·절차 | 서류, 자격, 기간, 분류 | 문서 근거로 답변 가능 |
| 교리·영적 판단 | "왜 성별실패인가", "하늘부모님의 뜻" | **답하지 않고 목회자 연결** — 질문으로 캐지도 않는다 |

"Detecting doctrinal flattening"(AI and Ethics, 2026)은 LLM 이 교단별 차이를 뭉개 "기독교인은
~한다" 로 일반화하는 경향을 보고했고, 특히 구원론·성례 영역에서 위험이 높았다. 축복 도메인은
그 위험이 더 크다. **강제 인용(strict) 은 이미 걸려 있으니, 교리 질문은 인용이 있어도 답하지 않는
별도 경계**가 필요하다.

### 5-2. 자유 입력은 프롬프트에 원문으로 넣지 않는다

ASPI(2026)는 에이전트가 **재질문 상태로 들어가는 순간** 프롬프트 인젝션 성공률이 급등한다고
보고했다 — o3 1.8% → 34.0%, Gemini-3-Flash 2.2% → 35.7%. 원인은 "에이전트가 스스로 연 입력 채널"
이다. 현재 `#51` 코드는 `allow_custom=True` 가 기본이고 `optional_ask` 는 `options=[]` 로 두어
**자유 입력만 받는다.** 정확히 이 위험 지점이다.

- 카드 응답은 **enum 우선**, 자유 입력은 canonical 값으로 정규화한 뒤에만 다음 턴에 주입
- 정규화 실패한 자유 텍스트는 `handoff` 로 (모델에 원문 전달 금지)

### 5-3. 취약 사용자 · 고지

- 위기 감지는 현재 키워드 기반 — 유지하되 **카드보다 항상 먼저**(현재 코드가 그렇게 되어 있음, 유지)
- 챠플린 윤리 논의의 공통 권고: AI 임을 명시하고 사람 연결 경로를 상시 노출
- **재질문은 상담 대체가 아니다** — `optional_ask` CTA 문구에 "담당자와 상담" 병기

---

## 6. 실행 순서 (봇 1개 운영 기준)

| 단계 | 할 일 | 산출물 | 규모 |
| --- | --- | --- | --- |
| 0 | **#32 close**, #50 리뷰·머지 | 정책 계약 확보 | 반나절 |
| 1 | 결정축 사전 8개 + 근거 span 승인 | `decision_axes.yaml` + 관리자 검수 | 도메인 책임자 반나절 |
| 2 | 축 추출기 구현(페르소나 없음, enum, structured output) | `axis_extractor.py` + 사람 라벨 대비 정확도 | 1~2일 |
| 3 | 서버 규칙표로 route 결정 + `conditional_answer` 렌더 | 결정론 라우터 | 2일 |
| 4 | **shadow mode** — 라우팅만 기록, 사용자에겐 기존 답변 | 20문항 × 3trial + 실트래픽 2주 | 2주 |
| 5 | `optional_ask` CTA 만 우선 활성화 | 이탈률·클릭률 관측 | 1주 |
| 6 | `blocking_ask` 는 정책 룰이 있는 경로에만 개방 | — | — |

**#51 은 머지하지 않고 부품만 재사용한다** — 상태 영속(`ChatSession.clarification_state`),
카드 UI(`ClarificationCard.tsx`), 마이그레이션, 파일럿 러너는 그대로 살린다.
버리는 것은 `_routing_system_prompt`(페르소나 결합)와 하드코딩 가드다.

---

## 7. 성공 지표 (카드 발생률은 지표가 아니다)

| 지표 | 정의 | 목표 |
| --- | --- | --- |
| 축 추출 정확도 | 사람 라벨 대비 의존축·진술축 F1 | ≥ 0.85 |
| route 재현성 | 동일 입력 3회 동일 route | 100% (결정론이므로) |
| no-ask 위반 | `condition_breach`·`health_disclosure` 를 카드로 물은 횟수 | **0** |
| 자유입력 원문 주입 | 정규화 없이 프롬프트에 들어간 건수 | **0** |
| 교리 질문 단정 | 교리 층 질문에 handoff 아닌 답변을 한 건수 | **0** |
| CTA 전환/이탈 | `optional_ask` 클릭률 · 카드 이탈률 | 관측 후 기준 설정 |
| 질문 수 | ask 경로당 평균 질문 수 | ≤ 1.5 (SAGE-Agent 실측 1.39) |

---

## 8. 근거

**재질문 판정의 어려움**
- [CLAMBER: A Benchmark of Identifying and Clarifying Ambiguous Information Needs in LLMs](https://arxiv.org/abs/2405.12063) — ≈12K 케이스. LLM 은 모호성 식별·질문 시점 판단에 취약하고 CoT/few-shot 은 한계 개선 + 잘못된 확신
- [Structured Uncertainty guided Clarification for LLM Agents (SAGE-Agent)](https://arxiv.org/html/2511.08798v2) — 비구조적 언어 공간의 재질문은 저가치 과잉질문·핵심 누락을 동시에 유발. 구조화 파라미터 belief + **EVPI** 로 질문 선택, 애매 과제당 평균 **1.39개** 질문(베이스라인 대비 45.7~59.4% 감소)
- [IntentRL](https://arxiv.org/pdf/2602.03468) — 정보이득 보상 + 과잉질문 페널티. 적은 수의 정확한 질문이 장황한 심문보다 낫다

**과잉 질문의 비용**
- [Simulating and Modeling the Risk of Conversational Search](https://arxiv.org/pdf/2201.00235) — 재질문을 기본 대안으로 두면 안 되며, **부적절한 질문은 차선의 답변보다 나쁘다**
- [Clarifying the Path to User Satisfaction](https://arxiv.org/pdf/2402.01934) — 질문 품질·순서가 만족도에 미치는 영향

**언제 묻는가 — 제품 사례**
- [Manus — Introducing Plan Mode](https://manus.im/blog/manus-plan-mode) — 수동 모드. 맥락이 부족하면 묻고, 경로가 분명하면 계획 제시. 사용자가 확인하기 전엔 실행 안 함
- [Manus — Chat vs Agent mode](https://help.manus.im/en/articles/11711128-what-are-the-differences-between-chat-mode-and-agent-mode)
- [OpenAI Deep Research API](https://developers.openai.com/api/docs/guides/deep-research) — **비싼 작업 직전 1회 선행 질문**. 사용자가 긴 대기를 감수할 때만 묻는다

**보안**
- [ASPI: Seeking Ambiguity Clarification Amplifies Prompt Injection Vulnerability](https://labs.scale.com/papers/aspi) — 재질문 상태 진입 시 공격 성공률 o3 1.8%→34.0%, Gemini-3-Flash 2.2%→35.7%

**종교 도메인**
- [Detecting doctrinal flattening in AI generated responses (AI and Ethics, 2026)](https://link.springer.com/article/10.1007/s43681-026-01051-0) — 11개 전통 576개 교리 명제. 교단 차이를 뭉개는 경향, 구원론·성례에서 위험 최대
- [Sacred or Synthetic? Evaluating LLM Reliability and Abstention for Religious Queries](https://arxiv.org/pdf/2508.08287) — 교리 질문 오답률이 사실 질문보다 높고 abstention 이 불안정. 신뢰 가능한 기권 메커니즘 권고
- [Chaplains' Reflections on the Design and Usage of AI for Conversational Care (CHI 2026)](https://dl.acm.org/doi/full/10.1145/3772318.3790468)
- [Not Human Enough? Rethinking AI's Place in Pastoral Care (Pastoral Psychology)](https://link.springer.com/article/10.1007/s11089-026-01351-6)
- [Ethics of AI in Spiritual Care — Chaplaincy Innovation Lab](https://chaplaincyinnovation.org/2026/06/ethics-ai-spiritual-care)
