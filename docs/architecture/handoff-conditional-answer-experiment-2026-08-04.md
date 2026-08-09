# 핸드오프 — 조건부 분기 답변 2×2 절제 실험 (2026-08-04)

> **다음 세션 전용.** 이 문서만 읽고 실험을 실행할 수 있게 쓴다.
> 설계 근거는 `conditional-answer-rag-proposal-2026-08-04.md` (§9 후속 논의 반영 포함).
> 이 세션에서는 **코드 변경 없음** — 실행은 다음 세션에서 한다.

---

## 0. 30초 요약

축복 봇이 **케이스별로 갈려야 할 답을 하나로 뭉쳐서** 답한다. 원인 후보는 둘이다.

- **재료 문제** — 검색된 청크에 애초에 조건(1세/2세, 절차 단계 등)이 안 붙어 있다
- **생성 문제** — 조건이 있는데도 모델이 매끄러운 한 편으로 평탄화한다

**어느 쪽인지 모르는 채로 비싼 투자(규정 카드 코퍼스 재작성)를 하면 안 된다.**
이 실험은 반나절로 그것을 가른다.

---

## 1. 확정된 사실 (재조사 불필요)

### 현재 파이프라인

| 항목 | 값 | 위치 |
| --- | --- | --- |
| RAG 호출 | `generate_with_rag` 단일 호출 (본문 + 인용 + 후속질문 동시) | `backend/app/services/rag/gemini.py:405` |
| system_instruction | `bot.system_prompt` + `_FOLLOWUPS_INSTRUCTION` | 같은 파일 `:438` |
| `RAG_TOP_K` | **12** | `backend/app/core/config.py` |
| `RAG_TEMPERATURE` | **0.3** | 같은 파일 |
| `chunking_config` | **설정 안 함 (기본값)** | `upload_document` `:284` |
| `custom_metadata` (업로드 시) | `bot_id`(numeric) + `content_sha256`(string) **둘뿐** | 같은 위치 |
| `metadata_filter` (검색 시) | `f"bot_id = {bot_id}"` **뿐** | `:448` |
| 인용 추출 | `_citations_from_grounding` — chunks + supports 파싱, 중복 병합 | `:168` |
| 분기 총괄 | `ChatService.process_chat_request` | `backend/app/services/chat_service.py:194` |
| 본문 후처리 | `[1.2, 1.5]` 인용 마커 제거, `<followups>` 블록 분리 | `gemini.py:88` |

### SDK 실측 (`google-genai` 2.10, `backend/.venv`)

```
GroundingChunkRetrievedContext:
    title / text / uri / page_number / custom_metadata / document_name / rag_chunk / file_search_store
GroundingChunkCustomMetadata:
    key / string_value / numeric_value / string_list_value
    ※ "not supported in Vertex AI" → Developer API 전용 = 우리 클라이언트에서 사용 가능
GroundingSupport:
    segment / grounding_chunk_indices / confidence_scores
```

- ✅ **업로드 시 붙인 `custom_metadata`가 grounding으로 회수될 수 있다** — 조건 다양성 판정을
  결정론으로 만들 수 있는 근거. **단, 실제로 채워져 오는지는 이 실험에서 확인한다(체크 A).**
- ❌ **검색 관련도 점수는 없다.** `confidence_scores`는 *답변 구간의 뒷받침 신뢰도*지 검색 점수가 아니다.
  → 점수 임계값 기반 모호성 판정은 이 스택에서 불가.
- ⚠️ `document_name` / `rag_chunk`는 Vertex 전용이라 우리 클라이언트에선 항상 `None`.

### 하지 않기로 한 것

| 안 | 기각 사유 |
| --- | --- |
| 유사도/Reranker 점수 기반 판정 | File Search가 점수를 반환하지 않음 |
| LLM 5-way route 판정 | PR #51에서 기대경로 **30/60 불일치** 실측 |
| Pre-RAG 민감 키워드 슬롯 체크 | 하드코딩 가드가 파일럿 문항에 과적합된 이력. 종교 도메인은 민감어가 닫혀 있지 않음 |
| 분기 답변을 FAQ로 | strict 봇에서 FAQ는 거절문만 통과 (`is_refusal_faq`) |
| 되묻기를 기본 종착점으로 | 파일럿에서 사용자가 이미 다 진술한 경우가 다수 |

---

## 2. 실험 설계

### 2×2 절제

| | 현행 프롬프트 | 분기 프롬프트 |
| --- | --- | --- |
| **현행 코퍼스** | **A** 기준선 | **B** ← 이번 세션 실행 대상 |
| 카드 코퍼스 | C (나중) | D (나중) |

**이번 세션은 A / B 만 돌린다.** C·D는 카드 코퍼스가 있어야 하고, 그 투자 여부가 이 실험의 산출물이다.

### 두 개의 관측

- **P0 — 청크 덤프**: A 실행 시 받은 `grounding_chunks`를 그대로 저장해 눈으로 본다
- **P0b — 프롬프트 대조**: 같은 문항을 B로 다시 돌려 A와 비교한다

**정답 분기 라벨이 아직 없으므로 1차는 정성 스크리닝**이다. `branch recall` 같은 정량 지표는
라벨링 이후 2차에서 계산한다. 그래도 아래 판정 기준은 라벨 없이 결론이 난다.

---

## 3. 문항 선정 (10건)

**기준** — "정답이 케이스별로 갈려야 하는데 하나로 뭉쳐 나온 것"이 확인된 질문.

우선 출처, 위에서부터:

1. **3주차 레드팀에서 분기 오류로 지적된 문항** — `exports/` 의 레드팀 피드백
2. **회귀 하네스** `exports/regression/` L1·L2·L3 50문항 중 조건 의존 문항
3. **적응형 파일럿 20문항** 중 `blocking_ask` 기대였던 6건
   (`next-session-manus-adaptive-clarification-pilot-prompt-2026-08-04.md` 에 원문 있음)
   — A-108 · A-93 · A-107 · B-114 · B-230 · B-244

3번은 원문이 이미 확보돼 있어 **최소 6건은 즉시 시작 가능**하다. 나머지 4건을 1·2번에서 채운다.

> ⚠️ 문항은 **도메인 확인을 거친다.** "이 질문은 실제로 케이스별로 답이 갈리는가"가
> 전제이고, 그게 틀리면 실험 전체가 무의미하다.

---

## 4. 프롬프트 변형 B (그대로 사용)

현행 `system_instruction`(= `bot.system_prompt` + `_FOLLOWUPS_INSTRUCTION`) **뒤에** 아래를 덧붙인다.
`_FOLLOWUPS_INSTRUCTION`과 같은 방식이다.

```text

---
[조건부 분기 원칙]
1. 단정 금지 — 검색된 문서에 상황별로 다른 지침이 있는데 사용자의 상황이 확정되지 않았다면,
   하나의 결론으로 단정하지 마라.
2. 분기 출력 — 조건이 갈리면 조건별로 나누어 쓴다. 각 분기는 아래 한 줄 형식으로 시작한다.
   · ~인 경우: [해당 지침]
3. 근거 밖 조건 금지 — 검색된 문서에 없는 조건이나 구분을 만들지 마라.
   문서가 나누지 않은 것을 나누는 것은, 나누지 않는 것보다 나쁘다.
4. 마감 — 문서에 명시되지 않은 상황은
   "문서에 명시되지 않은 그 밖의 경우는 담당자에게 확인해 주세요"로 닫는다.
```

**3번 규칙이 이 실험의 핵심 안전장치다.** 이게 없으면 B는 없는 분기를 만들어내고,
우리는 개선으로 오독하게 된다.

---

## 5. 덤프 스펙 — 정확히 이 필드들

읽기 전용 스크립트로 문항마다 A·B 각각 1회 실행하고 아래를 JSON으로 저장한다.

```python
resp = await rag.generate_with_rag(bot_id=..., prompt=q, system_prompt=SP_A_or_B,
                                   model_name=bot.llm_model)

g = resp_raw.candidates[0].grounding_metadata      # 원 response 객체가 필요 —
                                                    # generate_with_rag 는 RAGResponse 만 반환하므로
                                                    # 스크립트에서 SDK 를 직접 호출하거나 임시로 raw 를 반환하게 한다

for i, gc in enumerate(g.grounding_chunks or []):
    rc = gc.retrieved_context
    record(chunk_index=i,
           title=rc.title, uri=rc.uri, page_number=rc.page_number,
           text=(rc.text or "")[:1500],
           custom_metadata=[(m.key, m.string_value, m.numeric_value)
                            for m in (rc.custom_metadata or [])])   # ★ 체크 A

for sup in (g.grounding_supports or []):
    record(segment=sup.segment.text,
           chunk_indices=sup.grounding_chunk_indices,
           confidence=sup.confidence_scores)

record(answer=resp.answer, citations=len(resp.citations), followups=resp.followups)
```

산출물: `exports/branch_ablation_2026-08-xx/` 아래 문항별 JSON + 사람이 읽을 Markdown 표.
**PR #51 파일럿 러너 구조를 그대로 재사용한다**(`backend/scripts/run_adaptive_clarification_pilot.py`,
브랜치 `agent/adaptive-clarification-pilot`).

---

## 6. 덤프에서 확인할 네 가지

| # | 확인 | 답이 주는 결론 |
| --- | --- | --- |
| **A** | `custom_metadata`가 실제로 채워져 오는가 (`bot_id`, `content_sha256`이 보이는가) | 채워지면 → **조건 다양성 판정을 결정론으로 구현 가능**. 안 채워지면 → 텍스트 파싱 폴백 |
| **B** | 청크 텍스트에 조건(세대·축복종류·절차단계)이 들어 있는가 | 없으면 → **카드 코퍼스가 1순위**. 있으면 → 생성 문제 |
| **C** | 12개 청크가 몇 개 케이스를 담고 있는가 | 2종 이상이면 → 분기 재료는 있다. 1종이면 → 검색이 한 케이스로 쏠린다 |
| **D** | 정답 분기의 근거가 **애초에 검색되지 않았는가 / Store에 없는가** | Store에 없으면 → **이 로드맵 전체보다 문서 확보가 선행**. 기존 메모의 "2026 정본과 공문 동시 보유 봇 없음"이 정확히 이 위험 |

---

## 7. 판정 기준 (라벨 없이 결론 남)

문항별로 A·B 답변을 나란히 놓고 사람이 기록한다.

```
분기 수(A) / 분기 수(B)
B의 각 분기 조건 문구
  → 그 조건이 검색 청크 텍스트에 실제로 등장하는가   (Y/N)   ← 과분기 판정
B가 원 질문에 답했는가 (분기만 늘고 내용이 빈약해지지 않았는가)
```

| 관측 | 결론 | 다음 투자 |
| --- | --- | --- |
| B에서 **청크에 없는 조건이 1건이라도** 등장 | 프롬프트 단독 불가. 과분기 위험 실증 | **카드 코퍼스 1순위**, B는 카드 이후 재시도 |
| B의 분기 수 > A **이고 모든 조건이 청크에 실재** | 재료는 충분했다. **생성 문제** | 카드 투자 **대폭 축소**. `<branches>` 구조화로 직행 |
| B ≈ A (분기 안 늘어남) | 재료 문제 | **카드 코퍼스 1순위** |
| 체크 D에서 근거가 Store에 없음 | 문서 결손 | **문서 확보가 모든 것에 선행** |

---

## 8. 주의사항

- **라이브 호출이다.** 실 Gemini API 비용이 발생하고 실 봇 문서를 읽는다. 문항 10건 × 2조건 = 20회.
- **읽기 전용.** DB 에 쓰지 않는다. 프롬프트 변형은 스크립트 안에서만 적용하고
  `bots.system_prompt` 를 수정하지 않는다.
- **모델을 고정한다.** `bot.llm_model` 을 그대로 쓰고 A·B 사이에 바꾸지 않는다.
- **비결정성.** 같은 조건을 **최소 2회** 돌려 분기 수가 흔들리는지 본다
  (1회 결과로 판정하지 않는다 — PR #51의 교훈).
- **결과 해석에 가설을 섞지 않는다.** 먼저 관측만 기록하고, 판정표는 그 뒤에 적용한다.
- 리포트는 `exports/` 에 두고 커밋 여부는 민감도 검토 후 결정한다(레드팀 문항 원문 포함 가능).

---

## 9. 실행 준비물

```bash
cd backend
# .venv 사용 (python 3.14)
.venv/bin/python --version

# DB 는 필요 시에만 (문항을 DB 대화에서 뽑는 경우)
# 라이브 = Neon 직결, 개발 = localhost — memory 의 reference_local_stack_against_neon 참조

# 필요한 환경변수
#   GEMINI_API_KEY   (필수)
#   DATABASE_URL     (봇/문항 조회 시)
```

봇 선택: **현재 운영 중인 축복 봇 1개**. `bot.use_rag=True`, `evidence_policy_mode` 확인 후 기록.

---

## 10. 다음 세션 재개 프롬프트

```text
docs/architecture/handoff-conditional-answer-experiment-2026-08-04.md 를 읽고 시작해줘.

목표: 조건부 분기 답변 2×2 절제 실험의 A/B 조건만 실행해서, 케이스 분기가 뭉개지는 원인이
'재료 문제(청크에 조건이 없음)'인지 '생성 문제(있는데 평탄화)'인지 가른다.

순서:
1. 문항 10건 확정 — 파일럿 6건(A-108·A-93·A-107·B-114·B-230·B-244)은 핸드오프 §3 참조,
   나머지 4건은 회귀 하네스/레드팀에서 뽑아 나에게 확인받고 진행
2. 읽기 전용 러너 작성 — §5 덤프 스펙 그대로. PR #51 러너 구조 재사용
3. A/B × 10문항 × 2회 실행 (라이브 Gemini, DB 쓰기 없음)
4. §6 네 가지 체크 결과를 표로 정리
5. §7 판정 기준 적용 → 카드 코퍼스 투자 여부 결론

주의: 프롬프트 변형은 스크립트 안에서만. bots.system_prompt 수정 금지.
관측을 먼저 기록하고 판정은 그 뒤에.
```

---

## 11. 이 실험이 결정하는 것

| 산출 | 영향 |
| --- | --- |
| 재료 문제 vs 생성 문제 | **규정 카드 코퍼스(도메인 수일)** 투자 여부 |
| `custom_metadata` 회수 여부 | 조건 다양성 판정을 결정론으로 갈지 LLM 폴백으로 갈지 |
| 과분기 발생 여부 | 분기 프롬프트를 운영에 켤 수 있는지 |
| 청크당 케이스 수 | `chunking_config` · `top_k` 조정 필요성 |
| Store 결손 여부 | 문서 확보를 앞으로 당길지 |

**결론이 나기 전까지 카드 코퍼스 작성을 시작하지 않는다.**
