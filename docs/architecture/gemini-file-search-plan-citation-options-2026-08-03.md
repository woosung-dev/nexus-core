# Gemini File Search 계획·인용 경로 조사 (2026-08-03)

## 질문

D-1 v2의 첫 맥락 보완 계획 호출은 `ask | answer` JSON과 File Search 근거를 한 호출에서 얻어야 한다. 현재는 `generate_structured_with_rag()`가 `generate_content`의 `candidate.grounding_metadata`에서 인용을 읽고, `ask`는 인용 제목이 하나라도 없으면 무효 처리한다. 실제 요청에서는 일반 `generate_with_rag()`보다 이 경로의 인용이 빈 경우가 많아 질문 카드가 사라진다.

## 공식 자료에서 확정되는 사실

1. File Search 인용은 보장값이 아니다. Google 문서는 File Search 응답이 인용을 **포함할 수 있다**고 설명한다. legacy `generateContent`에서는 `response.candidates[0].grounding_metadata`에서, Interactions에서는 `model_output`의 텍스트 content block `annotations`에서 읽는다. 즉 `citations == []`만으로 검색 미실행이나 계획의 무근거를 단정할 수 없다. [generateContent File Search: citations](https://ai.google.dev/gemini-api/docs/generate-content/file-search?hl=en#citations) · [Interactions File Search: citations](https://ai.google.dev/gemini-api/docs/file-search?hl=en#citations)

2. Gemini 3 계열은 File Search와 구조화 출력을 함께 쓰는 구성을 공식 지원한다. legacy 문서는 File Search tool + `response_format` 예시를, Interactions 문서는 `interactions.create` + `file_search` + JSON Schema `response_format` 예시를 제공한다. 다만 구조화 출력은 JSON 형식을 강제할 뿐 값의 의미적 정확성까지 보장하지 않으므로 서버 검증은 여전히 필요하다. [legacy File Search structured output](https://ai.google.dev/gemini-api/docs/generate-content/file-search?hl=en#structured-output) · [Interactions structured outputs with tools](https://ai.google.dev/gemini-api/docs/structured-output?hl=en#structured-outputs-with-tools) · [structured-output validation guidance](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en#best-practices)

3. Interactions API는 2026-06부터 GA이며 새 프로젝트에 권장되는 API다. `response_format`으로 JSON Schema를 적용할 수 있고, File Search 인용은 같은 interaction의 `file_citation` annotation에 `file_name`, `document_uri`, `source`, `page_number` 등을 담을 수 있다. [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview?hl=en) · [Interactions API: response format](https://ai.google.dev/api/interactions-api?hl=en) · [FileCitation fields](https://ai.google.dev/api/interactions-api?hl=en#FileCitation)

4. Interactions는 기본적으로 요청·응답을 저장한다. D-1 프로토타입의 비영속 원칙을 유지하려면 계획 호출에 반드시 `store=False`를 지정해야 한다. 이 경우 `previous_interaction_id` 기반 서버 상태는 사용할 수 없지만, 이 프로토타입은 첫 요청 단발 계획 호출이므로 필요하지 않다. [Interactions storage and retention](https://ai.google.dev/gemini-api/docs/interactions-overview?hl=en#data-storage-and-retention)

5. 현재 고정 버전 `google-genai==2.10.0`에는 legacy structured-output 설정(`response_mime_type`, `response_schema`, `response_json_schema`), `Candidate.grounding_metadata`, 그리고 비동기 `interactions` client가 모두 있다. 하지만 현재 `generate_structured_with_rag()`는 전달받은 `response_schema`를 Gemini config에 넣지 않고 프롬프트 JSON을 Pydantic으로 사후 검증한다. 따라서 관측된 현상만으로 “구조화 출력이 인용을 지운다”고 결론 내릴 수는 없다. [SDK 2.10.0 `GenerateContentConfig`](https://github.com/googleapis/python-genai/blob/v2.10.0/google/genai/types.py#L5912-L6049) · [SDK 2.10.0 `Candidate.grounding_metadata`](https://github.com/googleapis/python-genai/blob/v2.10.0/google/genai/types.py#L7713-L7747) · [SDK 2.10.0 async Interactions client](https://github.com/googleapis/python-genai/blob/v2.10.0/google/genai/client.py#L72-L97)

## 현재 코드에 주는 진단

- `backend/app/services/rag/gemini.py`의 일반 답변과 계획 경로는 모두 legacy `generate_content`와 같은 File Search filter를 사용하지만, 계획 경로만 JSON 프롬프트를 직접 파싱한다.
- `backend/app/services/clarification_service.py:_validate_ask_plan()`은 인용 제목이 없으면 `ask`를 실패시킨다. 공식 계약에서 인용은 optional이므로 이 규칙은 정상적인 `ask`까지 `fallback → ready`로 바꿀 수 있다.
- 저장소에는 이미 `search_citations()`가 `aio.interactions.create()`의 `file_citation` annotations를 `RAGCitation`으로 변환하는 코드가 있다. 단, 이것은 현재 별도의 두 번째 생성이므로 계획 근거로 재사용하면 안 된다. 계획 호출 자체를 Interactions로 바꿔 같은 응답의 annotations를 읽어야 한다.

## 선택지

### A. 계획 호출만 Interactions 단일 패스로 교체 — 권장

`generate_structured_with_rag()`의 내부만 `aio.interactions.create()`로 교체한다.

```python
interaction = await client.aio.interactions.create(
    model=model_name,
    input=prompt,
    system_instruction=system_prompt,
    tools=[{
        "type": "file_search",
        "file_search_store_names": [store_name],
        "metadata_filter": f"bot_id = {bot_id}",
        "top_k": settings.RAG_TOP_K,
    }],
    response_format={
        "type": "text",
        "mime_type": "application/json",
        "schema": response_schema.model_json_schema(),
    },
    generation_config={"temperature": 0.0, "max_output_tokens": 1200},
    store=False,
)
```

`interaction.output_text`를 Pydantic으로 검증하고, **같은** `interaction.steps[*].content[*].annotations`의 `file_citation`만 `RAGCitation`으로 변환한다. 기존 `search_citations()`의 annotation parser는 추출 helper로 분리해 재사용할 수 있다.

- 장점: Google이 문서화한 JSON + File Search + citation 표면을 한 호출에서 사용한다. 현재 이미 프로젝트에 있는 Interactions parser를 활용하며, 답변 본문과 무관한 두 번째 생성이 추가되지 않는다.
- 한계: File citation도 optional이므로 `ask`에 0건이 절대 발생하지 않는다고 보장하지 않는다. D-1의 실제 모델 `gemini-3.5-flash-lite`에서 schema + File Search + annotation을 함께 반환하는지는 출시 전에 프로브로 확인해야 한다.
- 범위: 계획 경로만 바꾸므로 최종 답변·스트리밍·기존 인용 백필은 건드리지 않는다.

### B. legacy `generateContent`를 유지하되 실제 structured-output config를 사용해 재프로브

현재 구현은 schema 인자를 받지만 `GenerateContentConfig`에 설정하지 않는다. SDK 2.10.0의 `response_mime_type="application/json"`과 `response_schema`/`response_json_schema`를 명시한 호출을 별도 feature flag에서 측정한다. 최신 공식 File Search 문서도 legacy 경로의 구조화 출력 결합을 안내한다.

- 장점: 가장 작은 코드 변경이며 기존 `grounding_metadata → RAGCitation` 변환을 그대로 쓴다.
- 한계: 과거 D-1에서 이 조합이 약 150초 뒤 timeout 난 기록이 있어, 즉시 기본 경로로 바꾸면 안 된다. 또한 `grounding_metadata` 자체가 optional이므로 형식을 고쳐도 “인용 0이면 ask 무효” 정책은 그대로 실패한다.
- 판정: 같은 D-1 입력 10개를 (a) 현재 프롬프트 JSON, (b) legacy actual schema, (c) A의 Interactions schema로 실행해 raw response·latency·citation/annotation 수·`ask` 보존율을 비교한 뒤 결정한다.

### C. 인용 제목을 `ask`의 하드 게이트에서 검증 신호로 낮추기

`ask`의 JSON 형식·질문 수·중복·선택지·모델이 낸 evidence title의 실제 Store 문서명 일치는 계속 강제하되, 같은 호출의 citation title 부재만으로 카드 전체를 버리지는 않는다. citation이 있으면 retrieval-result와 evidence title의 일치를 강하게 검증하고, 없으면 `citation_missing` 진단만 남긴다.

- 장점: 제공자 문서의 optional citation 계약과 맞고, 지금의 0/10 카드 문제를 즉시 완화한다. Store 목록은 읽기 전용으로 조회할 수 있으므로 D-1의 DB·문서 변경도 없다.
- 한계: Store에 존재하는 제목과 일치한다는 사실은 해당 chunk가 이번 요청에서 실제 검색됐다는 증명은 아니다. 따라서 고위험 절차에서의 근거 보증은 A의 same-call annotation보다 약하다.
- 안전장치: 사용자에게는 이 진단을 노출하지 않고, `ask`/`answer`별 citation-missing 비율과 표본 근거 검수를 관찰한다. Store 제목 일치조차 실패하면 지금처럼 카드를 버린다.

## 권장 순서

1. 우선 A를 작은 실험 경로로 만든다. `store=False`, 단일 호출, 현재 `bot_id` metadata filter, 읽기 전용 Store를 모두 유지한다.
2. 위 세 가지 arm을 D-1의 10개 `expected=ask` 입력과 일반 설명 입력에 실행한다. 성공 기준은 JSON parse율, `ask` 유지율, same-call `file_citation` 제목 일치율, p95 latency, 추가 모델 호출 수(정상 1회)다.
3. A에서 same-call citation이 충분히 나오면 기존 하드 검증을 유지한다. 여전히 optional citation 빈도가 높다면 C를 명시적인 제품 위험 수용안으로 검토한다. B는 A가 모델/SDK 제약으로 막힐 때의 최소 변경 대안이다.

## 비목표

- 이 조사는 질문을 반드시 만들어야 하는 도메인 정책을 정의하지 않는다.
- API만으로 File Search 검색 청크를 별도 retrieve하고, 그 결과를 계획 생성에 주입하는 설계는 여기서 확인하지 못했다. 제안은 모두 현재 관리형 File Search tool 호출을 유지한다.
- File Search Store 생성·업로드·삭제, D-1 DB 마이그레이션, ChatSession/Message 저장은 포함하지 않는다.
