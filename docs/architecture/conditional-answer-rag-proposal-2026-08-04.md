# 조건부 답변 RAG — 케이스가 갈리는데 하나로 뭉개지는 문제 (2026-08-04)

> 문제: "축복"처럼 **케이스별로 답이 달라져야 하는 주제**에서 봇이 분기를 잃고 하나의 산문으로
> 합쳐 답한다. 없는 조건을 끌어와 붙이기도 한다(할루시네이션). 이 문서는 원인을 코드 층위에서
> 짚고, 업계가 이 문제를 어떻게 풀었는지와 우리 적용안을 제안한다.
> 재질문(clarification) 제안서와 별개 축이다 — 그쪽은 "물을까 말까", 이쪽은 "묻지 않고도 안 뭉개기".

---

## 1. 문제 재정의

축복 규정은 **조건이 붙은 규칙문**이다.

```
2세가 · 40일 정성기간 중에 · 부부관계를 가진 경우 → X
1세가 · 같은 조건에서                            → Y
2세가 · 가정출발 이후                            → Z
```

그런데 현재 파이프라인은 이 조건을 **세 곳에서 연달아 잃는다.**

| 층 | 현재 동작 | 조건이 사라지는 지점 |
| --- | --- | --- |
| 색인 | `custom_metadata = [bot_id, content_sha256]` 뿐 | 청크에 **"이 조항이 적용되는 케이스"** 표시가 없다 |
| 검색 | `metadata_filter="bot_id = N"` + flat `top_k=12` | 서로 다른 케이스의 청크가 **한 컨텍스트에 섞여** 들어온다 |
| 생성 | persona + followups 지시, `temperature=0.3`, **자유 산문** | 매끄러운 한 편의 답을 요구 → 모델이 조건을 **평탄화**한다 |
| 검증 | 인용은 사후·근사(`approximate=True`) | 문장이 **어느 조건의 청크**에서 왔는지 대조하지 않는다 |

`_CITATION_MARKER_RE`가 본문의 `[1.2, 1.5]` 마커를 지우는 것도 같은 방향이다(시각 노이즈 제거는
타당하나, 결과적으로 문장 단위 귀속이 본문에서 사라진다 — 프론트가 각주로 복원하고 있으니
분기 단위 귀속에 재활용할 수 있다).

**요약: 조건이 붙은 규정을 조건 없는 검색·조건 없는 생성으로 처리하고 있다.**
할루시네이션도 여기서 파생된다 — 다른 케이스의 문장이 컨텍스트에 같이 있으니, 모델이
그 조각을 현재 케이스의 근거로 오인해 붙인다. 없는 사실을 지어내는 게 아니라
**있는 사실을 잘못된 케이스에 붙이는** 유형이다.

---

## 2. 업계는 이 문제를 어떻게 풀었나

### 2-1. 조건형 QA — "답"이 아니라 "답 + 조건"을 반환한다

`ConditionalQA`(ACL 2022)는 답이 **특정 조건 하에서만 유효한** 질문을 모은 데이터셋이다.
모델은 답과 함께 **그 답이 성립하기 위해 충족돼야 하는 조건**을 문서에서 찾아 반환해야 한다.
논문은 조건 선택·검색이 특히 어렵다고 보고한다. `CondAmbigQA`(EMNLP 2025)가 이를 모호성과
결합해 확장했다.

`Chain of Condition`(2024)은 이걸 3단계 절차로 만들었다.

```
① 구성(construct)  문서에서 조건을 전부 찾아 논리 관계로 조립
② 검증(verify)     사용자가 진술한 내용과 대조해 충족/미충족/미상 판정
③ 해소(solve)      논리식을 풀어 답을 내되, 미상 조건은 명시해 함께 반환
```

핵심은 **미상 조건을 지우지 않고 답과 함께 드러낸다**는 점이다. 우리가 원하는 동작 그대로다.

### 2-2. 모호·다중정답 커버리지 — 해석별로 따로 검색한다

단일 쿼리 벡터는 여러 정답 분포를 담지 못한다. 그래서:

- **Tree of Clarifications** — 해석마다 가지를 쳐서 분기별로 검색
- **DIVA** (diversify → verify → adapt) — 쿼리를 다양화해 검색하고 검증 후 종합
- **AmbigDocs / MADAM-RAG** — 모호한 질의에 **유효한 답을 전부** 제시해야 정답. 다중 에이전트가
  라운드로 토론해 분기별 답을 모으고 오정보·잡음은 버린다. AmbigDocs에서 최대 +11.40%,
  FaithEval에서 +15.80% 개선. 다만 근거 불균형이 커지면 여전히 격차가 남는다고 보고한다.

교훈: **분기를 살리려면 검색부터 분기별로** 해야 한다. 한 번의 flat top-k로는 소수 분기가 밀린다.

### 2-3. 충돌 처리 — 탐지·분류·해소를 분리한다

`ConflictRAG`는 충돌을 **탐지 / 분류 / 해소** 세 모듈로 나누는 설계를 제안한다.
`Conflict-Aware RAG`(WWW 2026)는 소스별 생성확률 차이로 충돌 인지도(ConScore)를 계산한다.
`RAMDocs`는 충돌 유형을 **모호성 / 오정보 / 잡음**으로 구분한다 — 처리 방법이 각각 다르기 때문이다.

우리 상황에 그대로 대응된다: 2026 정본 vs 공문 vs 구버전 문서가 상충할 때
"모호(둘 다 유효)"인지 "구버전(무효)"인지 구분해야 한다.

### 2-4. 할루시네이션 — 문장 단위로 쪼개 근거와 대조한다

생산 환경의 공통 패턴은 **atomic claim 분해 후 개별 검증**이다. 답변을 원자 주장으로 쪼개고
각 주장을 검색 청크와 대조(entailment 또는 문자열/의미 일치)한 뒤, 통과 못한 주장을 제거하거나
전체를 게이팅한다. 단순 문자열 대조만으로도 오류의 상당 부분이 잡히고 지연은 거의 없다는 보고가 있다.

우리는 이미 **절반을 갖고 있다** — `grounding_supports`(답변 구간 ↔ 청크 매핑)와
`evidence.py`의 원문 스냅(모델이 낸 구절을 청크 원문 위치로 되돌리는 로직). 여기에
**"조건 일치"** 검사만 추가하면 된다.

### 2-5. Manus의 기여는 다른 층이다 — 컨텍스트 엔지니어링

Manus 블로그의 교훈은 조건 처리 기법이 아니라 **긴 작업에서 모델을 궤도에 유지하는 법**이다.

| 기법 | 내용 | 우리에게 쓸모 |
| --- | --- | --- |
| **Recitation** | todo를 계속 다시 써 목표를 컨텍스트 끝으로 밀어 넣음 (lost-in-the-middle 완화) | 분기 목록을 생성 직전에 다시 제시해 누락 방지 |
| **Logit masking + state machine** | 도구를 지우지 않고 **상태에 따라 마스킹**해 스키마 위반·환각 차단 | 분기 배열 스키마를 강제할 때 동일 원리 (structured output) |
| **File system as context** | 컨텍스트를 외부 저장소로 빼고 복원 가능하게 압축 | 규정 원문을 프롬프트에 다 넣지 않고 참조로 유지 |
| **오류 보존** | 실패를 지우지 않고 남겨 재시도 편향을 줄임 | 검증 실패한 분기를 로그로 남겨 회귀 추적 |
| **few-shot 모방 회피** | 예시가 균일하면 모델이 패턴을 흉내 냄 → 의도적 변주 | 분기 예시를 한 형태로 고정하지 말 것 |

즉 **Manus는 "어떻게 안 잊게 하나", ConditionalQA 계열은 "무엇을 남겨야 하나"** 를 답한다. 둘 다 필요하다.

### 2-6. 규제 도메인의 정석 — Rules as Code

공공 급여(SNAP·Medicaid) 자격 판정에서는 정책 문서를 **실행 가능한 규칙**으로 옮기고
LLM은 그 규칙을 생성·설명하는 보조로 쓴다. Georgetown Beeck Center 실험 결론은 명확하다 —
LLM은 정책→코드 변환을 **지원**할 수 있지만 복잡한 논리에서는 외부 검증과 사람의 검수가 필수다.

축복 규정도 같은 성격이다. **판정 로직을 프롬프트 안에 두지 말고 밖으로 꺼내야 한다.**

---

## 3. 제안 — 조건을 세 층에서 각각 보존한다

### L1. 색인 시점 — 청크에 케이스 표시를 박는다

Gemini File Search는 **문서당 여러 개의 custom_metadata 키**를 지원하고 쿼리 시
`metadata_filter`로 거를 수 있다. 현재는 `bot_id` 하나만 쓰고 있다.

> ⚠️ 제약: 메타데이터는 **문서 단위**다(청크 단위 메타데이터는 지원되지 않음).
> 따라서 아래 두 가지를 병행한다.

**(a) 조건 단위 문서 분할**
규정집 한 덩어리 대신 조건 축이 균질한 단위로 쪼개 업로드하고 축 값을 메타데이터로 박는다.

```python
custom_metadata=[
  {"key": "bot_id",        "numeric_value": 5},
  {"key": "generation",    "string_value": "2세"},
  {"key": "blessing_type", "string_value": "은사"},
  {"key": "stage",         "string_value": "40일정성중"},
  {"key": "doc_class",     "string_value": "정본2026"},   # 정본 / 공문 / 구버전
  {"key": "effective_from","string_value": "2026-01-01"},
]
```

`replace_document`가 이미 있으니 교체 경로는 확보돼 있다.

**(b) 조건 문맥 프리픽스 (Contextual Retrieval)**
분할이 어려운 문서는 각 절 앞에 적용 조건 한 문장을 덧붙여 재업로드한다.

```
[적용 대상: 2세 · 은사축복 · 40일 정성기간 중]
원문 …
```

이러면 임베딩 자체가 조건을 담아 검색 단계에서 케이스가 섞이는 양이 줄어든다.

### L2. 검색 시점 — 분기별로 나눠 검색한다

사용자가 자기 케이스를 밝히지 않은 것이 정상이다. 그러니 **필터로 좁히지 말고 분기로 넓힌다.**

```
사용자 케이스 진술 있음  → metadata_filter 로 해당 케이스만 검색 (정밀)
사용자 케이스 진술 없음  → 후보 축 값마다 subquery 1회씩 병렬 검색 후 병합 (커버리지)
                          ← Tree of Clarifications / DIVA 의 branching retrieval
```

flat `top_k=12` 한 방으로는 소수 분기가 항상 밀린다. 분기별 검색은 **각 분기에 최소 근거를
보장**하는 것이 목적이다.

### L3. 생성 시점 — 산문이 아니라 분기 배열을 강제한다

지금은 자유 산문이라 모델이 뭉갤 자유가 있다. 출력 스키마로 그 자유를 없앤다.

```json
{
  "shared_context": "모든 경우에 공통되는 설명",
  "branches": [
    {
      "condition": {"generation": "2세", "stage": "40일정성중"},
      "condition_text": "2세가 40일 정성기간 중인 경우",
      "conclusion": "…",
      "evidence_ids": ["정본2026 §…"],
      "confidence": "문서명시 | 유추 | 불명"
    }
  ],
  "unknown_conditions": ["stage"],
  "conflicts": [{"a": "정본2026 §…", "b": "공문 2024-…", "resolution": "정본 우선"}]
}
```

**Chain of Condition의 3단계를 이 스키마가 그대로 구현**한다 — 구성(branches), 검증
(condition vs 사용자 진술), 해소(unknown_conditions 명시).

> 주의: File Search 도구와 `response_schema` 동시 사용은 이 레포에서 과거에 타임아웃을 겪었다
> (`clarification-plan-handoff` §3). 그러면 **2단 호출**로 간다 —
> ① 검색·초안(현행 그대로) → ② 초안+청크를 입력으로 **검색 없이** 분기 구조화(가볍고 빠름).
> 두 번째 호출엔 **페르소나를 넣지 않는다**(평탄화 압력 제거).

### L4. 검증 시점 — 분기 단위로 게이팅한다

현행 strict 모드는 **답변 전체**를 인용 유무로 차단한다. 이를 분기 단위로 내린다.

```
각 branch 에 대해:
  ① evidence_ids 가 이번 검색 결과에 실재하는가
  ② 그 청크의 조건 메타데이터가 branch.condition 과 일치하는가   ← 핵심 추가
  ③ conclusion 의 핵심 주장이 청크 원문으로 스냅되는가 (evidence.py 재사용)
  실패 → 그 분기만 제거 (전체 차단 아님)
전 분기 실패 → 기존 STRICT_EVIDENCE_MESSAGE
```

②가 **"있는 사실을 잘못된 케이스에 붙이는"** 유형을 정확히 잡는다. 지금은 이 검사가 없다.

### L5. 충돌 규칙 — 선언적으로 정한다

```
정본2026 > 공문(최신) > 공문(구) > 구버전 규정집
같은 등급에서 상충 → 두 근거를 모두 노출하고 담당자 확인 안내 (임의 선택 금지)
```

`doc_class` + `effective_from` 메타데이터가 있으면 서버에서 결정론으로 판정 가능하다.
(기존 메모에 남아 있는 **"2026 정본과 공문을 동시에 보유한 봇이 없음"** 이슈부터 해소해야
충돌 판정이 의미를 갖는다.)

---

## 4. 화면 — 분기를 접이식으로

```
[공통] 40일 정성기간은 …입니다.  ← shared_context

▸ 2세 · 40일 정성기간 중인 경우          [정본2026 §12]
▸ 1세 · 40일 정성기간 중인 경우          [정본2026 §8]
▸ 가정출발 이후인 경우                    [공문 2025-03]

⚠ 확인이 필요한 조건: 현재 절차 단계
   → [내 상황에 맞게 확인하기]   ← 재질문 제안서의 optional_ask 와 연결
```

분기가 1개면 지금과 동일한 단일 답변으로 렌더한다(UI 변화 없음).
분기가 2개 이상일 때만 접이식이 뜬다.

---

## 5. 평가 — 분기 재현율을 지표로

카드 발생률이나 답변 길이는 지표가 아니다.

| 지표 | 정의 | 측정법 |
| --- | --- | --- |
| **branch recall** | 정답 분기 중 답변에 등장한 비율 | 케이스 분기 문항 30~50개에 사람이 정답 분기 라벨 |
| **branch precision** | 답변 분기 중 문서에 실재하는 비율 | 근거 대조 |
| **조건-근거 일치율** | 분기 조건과 인용 청크 메타데이터가 일치하는 비율 | 자동 (L4 ②) |
| **flattening rate** | 정답 분기 ≥2인데 답변이 1분기인 비율 | 자동 |
| **오귀속률** | 다른 케이스 청크를 근거로 제시한 비율 | 자동 (L4 ②) |
| p95 지연 | 2단 호출 추가분 | 기존 관측 인프라 |

**기존 회귀 하네스(`exports/regression/` L1·L2·L3 50문항)에 분기 라벨을 추가**하면
새 데이터셋을 만들지 않고 시작할 수 있다.

---

## 6. 실행 순서

| 단계 | 할 일 | 왜 이 순서인가 | 규모 |
| --- | --- | --- | --- |
| 0 | 케이스 분기 문항 30개에 **정답 분기 라벨** 부여 | 라벨 없이는 개선을 증명할 수 없다 | 도메인 반나절 |
| 1 | 현행 파이프라인 **flattening rate 측정** | 기준선 없이 고치면 체감으로 논쟁하게 된다 | 반나절 |
| 2 | **L3 분기 구조화만** 먼저 (2단 호출, 색인 손 안 댐) | 색인 재작업 없이 개선폭을 먼저 확인 | 2일 |
| 3 | L1 조건 메타데이터 + 문서 분할/프리픽스 | 2단계 결과로 필요성이 입증된 뒤 | 도메인 2~3일 |
| 4 | L2 분기별 검색 | 메타데이터가 있어야 의미가 있다 | 1~2일 |
| 5 | L4 분기 게이팅 + L5 충돌 규칙 | 정확도 방어선 | 2일 |
| 6 | UI 접이식 분기 | 백엔드 안정화 후 | 1~2일 |

**2단계가 핵심 분기점이다.** 색인을 갈아엎기 전에 "출력 형식만 바꿔도 분기가 살아나는가"를
먼저 본다. 살아나면 L1은 정밀도 향상용 투자가 되고, 안 살아나면 원인이 검색에 있다는 뜻이라
L1을 먼저 해야 한다는 근거가 된다.

---

## 7. 재질문 제안서와의 관계

| 축 | 이 문서 | 재질문 제안서 |
| --- | --- | --- |
| 질문 | 묻지 않고도 어떻게 안 뭉개나 | 언제 물어야 하나 |
| 산출 | `conditional_answer` 의 **내부 구현** | route 결정 구조 |
| 공유 | **결정축 사전**(generation·blessing_type·stage·…)을 양쪽이 함께 쓴다 | 동일 |

결정축 사전 하나가 두 제안의 공통 기반이다. 이것만 먼저 만들면 양쪽이 동시에 진행된다.

---

## 8. 근거

**조건형 QA**
- [ConditionalQA: A Complex Reading Comprehension Dataset with Conditional Answers (ACL 2022)](https://arxiv.org/abs/2110.06884) — 답 + 성립 조건을 함께 반환. 조건 선택·검색이 특히 어려움
- [CondAmbigQA: Conditional Ambiguous Question Answering (EMNLP 2025)](https://arxiv.org/abs/2502.01523)
- [Chain of Condition: Construct, Verify and Solve Conditions for CQA](https://arxiv.org/pdf/2408.05442) — 구성→검증→해소 3단계, 미상 조건을 명시하며 답변. CQA 벤치마크 SOTA
- [CMQA: Conditional QA with Multiple-Span Answers (COLING 2022)](https://aclanthology.org/2022.coling-1.146/)

**모호·다중정답 커버리지**
- [Retrieval-Augmented Generation with Conflicting Evidence (RAMDocs / MADAM-RAG)](https://arxiv.org/abs/2504.13079) — 충돌을 모호성·오정보·잡음으로 구분. AmbigDocs +11.40%, FaithEval +15.80%
- [Agentic Verification for Ambiguous Query Disambiguation](https://arxiv.org/pdf/2502.10352) — diversify→verify→adapt
- [Beyond Single Embeddings: Multi-Query Retrieval](https://arxiv.org/html/2511.02770) — 단일 쿼리 벡터로는 다중 타깃을 못 담는다

**충돌 처리**
- [ConflictRAG: Detecting and Resolving Knowledge Conflicts in RAG](https://arxiv.org/html/2605.17301v1) — 탐지·분류·해소 분리
- [Conflict-Aware RAG (ACM Web Conference 2026)](https://dl.acm.org/doi/10.1145/3774904.3792289) — ConScore
- [Does RAG Know When Retrieval Is Wrong?](https://arxiv.org/abs/2605.14473)

**할루시네이션 — 주장 단위 검증**
- [DnDScore: Decontextualization and Decomposition for Factuality Verification](https://arxiv.org/pdf/2412.13175)
- [Retrieval-Augmented Hallucination Detection](https://openreview.net/pdf?id=96vyGkAO08)
- [What is RAG Evaluation? Frameworks, Metrics, and Gates in 2026](https://futureagi.com/blog/what-is-rag-evaluation-2026/) — 실패 유형별 층위 방어, eval-gated CI

**컨텍스트 엔지니어링 (Manus)**
- [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — recitation, logit masking state machine, 파일시스템 외부화, 오류 보존, few-shot 모방 회피

**규제 도메인 정석**
- [AI-Powered Rules as Code: Experiments with Public Benefits Policy (Beeck Center, Georgetown)](https://beeckcenter.georgetown.edu/report/ai-powered-rules-as-code-experiments-with-public-benefits-policy/) — LLM은 정책→코드 변환을 지원하나 복잡 논리엔 외부 검증·사람 검수 필수

**플랫폼 제약**
- [Gemini API — File Search](https://ai.google.dev/gemini-api/docs/file-search) — 문서당 다중 `custom_metadata` 지원, 쿼리 시 `metadata_filter`. **메타데이터는 문서 단위**(청크 단위 미지원), `chunking_config` 제공

---

## 9. 후속 논의 반영 (같은 날 추가)

이 문서 작성 이후 세 차례 논의로 바뀐 것들. 원문은 그대로 두고 여기에 정정을 모은다.

### 9-1. FAQ 경로 철회

초안이 "고빈도 케이스 분기 답변을 FAQ로"를 제안했으나 **철회한다.**
`chat_service.py`가 strict 봇에서 `is_refusal_faq()`를 통과하지 못한 FAQ를
`STRICT_EVIDENCE_MESSAGE`로 대체한다 — **FAQ는 거절 통로지 답변 통로가 아니다.**
답변은 File Search 경로에서 나와야 한다.

### 9-2. SDK 실측 — `custom_metadata`가 grounding으로 돌아온다

`google-genai` 2.10 `types.py` 확인 결과:

```
GroundingChunkRetrievedContext:
    title / text / uri / page_number / custom_metadata / document_name / rag_chunk / file_search_store
GroundingChunkCustomMetadata:
    key / string_value / numeric_value / string_list_value
    ※ "This data type is not supported in Vertex AI" → Developer API 전용 = 우리 클라이언트
GroundingSupport:
    segment / grounding_chunk_indices / confidence_scores
```

의미하는 것:

- **업로드 시 붙인 조건 메타데이터를 검색 결과에서 그대로 회수할 수 있다.**
  조건 다양성 판정과 §3 L4 ②검사를 **문자열 파싱 없이 결정론으로** 구현 가능.
  → 앞서 제안한 "파일명 규약 근사"는 차선책으로 내려간다.
- **검색 관련도 점수는 존재하지 않는다.** `retrieved_context`에 score 필드가 없다.
  `GroundingSupport.confidence_scores`는 있으나 이는 *답변 구간이 청크에 뒷받침되는 신뢰도*이지
  검색 관련도가 아니다 → **점수 임계값 기반 모호성 판정은 이 스택에서 실행 불가.**
- 제약: `custom_metadata`는 문서 단위다. 카드마다 조건을 붙이려면 **카드 1장 = 문서 1개**여야 하고,
  그러면 문서가 수백 개가 된다. 현재 `list_documents`/`delete_document`가 store 전체를
  `page_size=20`으로 순회하므로 **관리 API가 O(n)으로 느려진다.** 규정 주제 수를 먼저 세고 결정한다.

### 9-3. 규정 카드 코퍼스

§3 L1을 구체화한다. 자동 청킹된 규정집 청크는 조건을 잃는다 —
"…40일 정성기간 중 부부관계를 가진 경우…"에서 *2세*가 빠져 있고, 그건 3페이지 위 제목에 있었다.
그래서 **검색 단위 자체를 조건 자립형으로** 다시 쓴다.

```
[적용] 2세 · 은사축복 · 40일 정성기간 중
[이런 질문] 40일 안에 부부관계를 가졌는데 / 정성기간 중 관계 / 은사 받아야 하나요
[결론] …
[근거 원문] "정본2026 §12 3항 — …"
[다른 경우] 1세는 §8 · 가정출발 이후는 공문 2025-03
```

네 가지를 동시에 해결한다 — ① `[이런 질문]`이 사용자 발화와 임베딩상 가까워 재현율↑
② 카드 1장 = 조건-결론 쌍 1개라 top_k 안에 분기가 나란히 들어옴
③ `[적용]`이 청크 안에 있어 오귀속이 줄고 서버가 검증 가능
④ **`[다른 경우]`가 결정적** — 카드 하나만 검색돼도 "다른 경우가 있다"는 사실이 컨텍스트에 들어온다.

FAQ와 다른 점: **카드는 답을 확정하지 않는다.** FAQ 오류는 즉시 잘못된 답변이지만
카드 오류는 검색 재료 하나가 부정확한 것이고 여전히 RAG가 근거와 함께 종합한다.
작성은 **LLM 초안 + 도메인 검수**(Rules-as-Code 실험의 결론과 같은 구조).

### 9-4. 새로 인지한 실패 유형 — 과분기(over-branching)

분기를 프롬프트로 강제하면 **문서가 나누지 않은 것을 나눈다.** 지금 문제(과소분기)의 거울상이고,
축복 도메인에서는 **과분기가 더 위험하다** — 없는 구분을 만들면 사용자가 자기에게 해당하지 않는
규정을 자기 것으로 읽는다. 그래서 §5 지표에 다음을 추가한다.

| 지표 | 정의 | 목표 |
| --- | --- | --- |
| **문서 미근거 조건 생성률** | 답변 분기의 조건이 검색 청크에 실재하지 않는 비율 | **0** |

### 9-5. 프롬프트 강화의 위치 — 해법이 아니라 대조군

"조건부 분기 프롬프트만 적용"은 **해법으로는 여전히 낮은 우선순위**다(청크에 조건이 없으면
모델이 조건을 지어낸다). 그러나 **대조군으로는 필수**다 — 재료 문제인지 생성 문제인지를
가장 싸게 가른다. §6 실행 순서보다 앞선다.

### 9-6. 확정된 실행 설계

2×2 절제 실험으로 다음 투자를 결정한다. 상세는
`handoff-conditional-answer-experiment-2026-08-04.md` 참조.

| | 현행 프롬프트 | 분기 프롬프트 |
| --- | --- | --- |
| **현행 코퍼스** | A 기준선 | **B** ← 가장 싼 검증 |
| **카드 코퍼스** | C | D |

- **B > A 이고 모든 조건이 청크에 실재** → 재료 충분, 생성 문제. 카드 투자 축소
- **B에서 미근거 조건 발생** → 프롬프트 단독 불가. 카드가 1순위
- **B ≈ A** → 재료 문제 확정. 카드가 1순위
