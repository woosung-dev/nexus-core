# 인계 — 재질문 트리거: 검색 점수는 못 쓴다 (2026-08-11)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 모두 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 선행 문서: `handoff-clarification-2026-08-10.md` · 정답 자: `handoff-evidence-audit-45set-2026-08-10.md`

---

## 0. 30초 요약

**같은 종류의 오류를 두 층에서 찾았다. 둘 다 「재는 것이 다르다」다.**

1. **선행 핸드오프 §9 가 지시한 「검색 점수 임계값 트리거」는 만들 수 없다**(§2).
   검색 점수는 「코퍼스가 이 단어를 다루는가」를 재고, 필요한 건 「이 사안을 결정하는 조문이
   있는가」다. 네 갈래 신호 전부 실패. 자를 지점이 없다는 것이 스윕의 답이다.
2. **그리고 「무주장·지어냄 12건」이라는 표적 자체가 재질문의 표적이 아니다**(§6-②).
   그건 코퍼스 커버리지를 재고, 재질문은 질문 모호성을 고친다. 그 12건은 **덜 적힌 질문이
   아니라 다 적혔는데 규정집에 답이 없는 질문**이라 되물어도 안 고쳐진다.

만든 것: 판정을 **검색 뒤로** 옮긴 트리거(§3, 배선 안 함)와 되물은 뒤 답변 경로 수정(§4).
판정기는 진짜 모호한 질문 6건을 짚어냈다 — 다만 그 6건은 현행 라벨에서 전부 「음성」이라
**이 코퍼스로는 값어치를 증명할 수 없다.** 다음 세션은 라벨부터 만들어야 한다(§6-A).

| | 값 | 확인 |
|---|---|---|
| 브랜치 | `feat/clarification-trigger` | `git log --oneline -1` |
| 새 모듈 | `backend/app/services/clarification_trigger.py` — **호출자 0개** | `grep -rn "clarification_trigger" backend/app \| grep -v "^backend/app/services/clarification_trigger"` |
| 배선 | 안 함. chat_service·프론트 그대로 | `grep -c "clarif\|Clarif" backend/app/services/chat_service.py` → 0 |
| 테스트 | 전체 통과 | `cd backend && uv run pytest -q` |

---

## 1. 양성 라벨 — 숫자를 읽기 전에 이것부터

`_audit.py:677` 정의를 그대로 쓴다. **`fabricated = violation AND not in_prompt`.**
「프롬프트 출처」(규정 원문엔 없지만 시스템 프롬프트엔 있는 주장)는 **양성이 아니다.**
그건 프롬프트 감수의 일이지 재질문의 일이 아니고, 지어냄율 정본도 같은 정의를 쓴다.

lexical(`wiki_budget`) 팔 45문항:

| 구분 | 수 | 문항 |
|---|---|---|
| 무주장 | 6 | 5, 16, 22, 31, 32, 44 |
| 지어냄 ≥1 | 6 | 4, 6, 11, 12, 17, 26 |
| **양성** | **12** | 위 둘의 합집합 (중복 0) |
| 음성 | 33 | 나머지 |
| *(참고) 프롬프트 출처만* | *7* | *1, 25, 28, 29, 30, 34, 35* |

검산: 지어냄 주장 9 + 프롬프트 출처 9 = 위반 18 = `audit_summary.json` 의
`wiki_budget.violations 18 / fabricated 9 / from_prompt 9`.

> **함정:** 「≥1 violation 문항 13개」로 세면 프롬프트 출처 7문항이 섞인다. 양성이 아니다.

```bash
python3 -c "
import json,pathlib
AU=json.loads(pathlib.Path('exports/wiki_eval/audit.json').read_text())['cells']
fab={n for n in range(1,46) for x in AU[f'{n}:wiki_budget']['claims'] if x.get('violation') and not x.get('in_prompt')}
sil={n for n in range(1,46) if not AU[f'{n}:wiki_budget']['claims']}
print(sorted(sil), sorted(fab), len(sil|fab))"
# → [5,16,22,31,32,44] [4,6,11,12,17,26] 12
```

---

## 2. 검색 점수로는 못 만든다 — 근거는 기전이다

양성 12 · 음성 33 에서 최고 신호(페이지 RRF@1)의 AUC 는 0.674 지만 95% CI 가 대략
[0.49, 0.86] 이라 우연을 포함한다. **통계로는 자를 수 없다. 그래서 AUC 를 근거로 쓰지 않는다.**
근거는 다음 셋이다.

### (a) 반례가 점수 분포의 양 끝에 있다

| n | 원 BM25@1 | 결과 | |
|---|---|---|---|
| 22 | **62.27** (코퍼스 최고) | 주장 0건 | 무주장 |
| 44 | **6.29** (최저) | 주장 0건 | 무주장 |
| 26 | 6.69 (2번째 최저) | 주장 9건 · 지어냄 1 | 지어냄 |
| 19 | 62.81 (최고) | 주장 12건 · 지어냄 0 | 정상 |

같은 라벨이 최고점과 최저점에 동시에 앉는다. 어디를 잘라도 갈리지 않는다.

### (b) 재는 것이 다르다 (구성개념 불일치)

BM25 는 **「코퍼스가 이 단어들을 다루는가」**를 잰다.
필요한 것은 **「이 사안을 결정하는 조문이 있는가」**다.

22번(2세가 1세와 사회결혼 후 기성축복 — 무효인가)은 축복·1세·2세·기성 같은 코퍼스 핵심어가
가득해 점수가 최고로 나온다. 그런데 **그 조합을 결정하는 조문 자체가 규정집에 없다.**
가장 온토픽한 질문이 가장 답할 수 없는 질문일 수 있다 — 이건 점수를 정교하게 만들어서
고쳐지는 문제가 아니다.

### (c) RRF 점수는 구조적으로 범위가 없다

`rrf()` 는 `1/(60+rank)` 의 합이고 `RRF_K = 60` 은 상위 등수의 점수차를 **의도적으로 뭉갠다.**

| 공간 | 융합 순위표 | 천장 | 관측 범위 | 최대/최소 |
|---|---|---|---|---|
| 페이지 | 3 (BM25 전용) | `3/61 = 0.0492` | 0.0403–0.0492 | **1.22배** |
| 유닛 | 2 | `2/61 = 0.0328` | 0.0305–0.0328 | **1.08배** (중앙값 = 천장) |

**코퍼스를 바꿔도 안 넓어진다.** 등수 기반이라 원래 그렇게 설계됐다.
인접 등수 차이는 0.0003 수준이다(`wiki/service.py:36-38` 이 Q#12 사례로 기록).

```bash
grep -n "RRF_K" backend/app/services/wiki/retrieval.py       # → 103
grep -n "rrf(" backend/app/services/wiki/store.py            # → 507(page), 508(unit)
```

### 재본 신호 넷 (서술 통계 — 결론은 (a)(b)(c))

페이지 RRF@1 · 유닛 RRF@1 · 원 BM25@1 · 질의어 IDF 커버리지. 전부 AUC 0.48–0.68.

> **함정 둘.**
> `Retrieved.top_score`(`store.py:89-91`)는 **레포 전체 호출자 0개인 죽은 속성**이다. 되살리지 마라.
> `WIKI_DENSE_SCALES` 를 켜면 순위표가 배로 늘어 모든 RRF 점수가 대략 2배가 된다 —
> 상수로 박은 임계값은 의미가 조용히 뒤집힌다.

---

## 3. 만든 것 — 판정을 검색 뒤로 옮겼다

`backend/app/services/clarification_trigger.py` (**호출자 0개**, 배선 안 함)

### B — 되물을지 (`judge_answerability`)

검색이 끝나고 **주입될 4~8건 원문을 읽은 뒤** 한 번의 구조화 호출로 판정한다.

```
answerable: true | false
missing:    [짧은 명사구]   # 무엇을 몰라서 못 정하는가 (최대 3)
evidence:   [src_id]        # 판정 근거가 된 주입 원문 id
```

- **검증**: `evidence` 의 모든 src_id 가 실제 주입 목록 안에 있어야 한다.
  `answerable=false` 인데 `missing` 이 비면 무효.
- **검증 실패 → 답변 진행(fail-open).** 판정기가 고장 나서 제품이 벙어리가 되는 쪽이 더 나쁘다.
- 모델은 `CLARIFICATION_MODEL = "gemini-3.5-flash-lite"`.

**PR #51 과 뭐가 다른가.** #51 은 검색 **전** 원질문만 보고 경로를 골랐고 60문항 중 30건이
어긋나 클로즈됐다. 여기는 검색 **후** 실제 원문을 보고 이진 판정만 하며, 판정이 댄 근거를
주입 목록과 대조한다. 그리고 어휘팔은 이미 이 판정을 6/45 회피·모순 0건으로 해내고 있다 —
없는 능력을 새로 요구하는 게 아니라 이미 일어나는 판정을 구조화해 꺼내는 것이다.

### A — 무엇을 되물을지 (`match_policy_rule`, LLM 0)

정책 규칙의 `request_examples` 를 레포 자체 BM25 로 매칭하고, 이긴 규칙의
`required_slots` 를 `_policy_questions` 로 그대로 카드화한다. **문구는 관리자가 쓴 것 그대로다.**

- 여기서의 임계값은 정당하다 — 질문 대 관리자 예시질문이라는 **같은 어휘 공간**의 매칭이지
  근거 충분성의 대리 지표가 아니다.
- 1위가 2위를 `MIN_RULE_DOMINANCE = 1.5` 배 이상 이겨야 채택한다. 애매하면 안 고른다.
- **절대 하한(`min_score`)은 기본 0 이다.** BM25 원점수는 질문이 길수록 커져서(45문항 4.4–58.7)
  길이 편향이 있다. 하한을 정하려면 스윕한 근거가 있어야 한다.
- 매칭 실패 → `handoff`. 문구를 지어내지 않는다.

### 시드 정책 4종

`docs/architecture/clarification-policy-seed-2026-08-11.json` (DB 에 안 쓴다 — `policy_override` 로 주입)

| 규칙 | 슬롯 | 겨냥한 문항 |
|---|---|---|
| `blessing-type-generation` | 축복 종류 | 22, 11 |
| `family-start-stage` | 현재 단계 | 31, 32 |
| `eligibility-age` | 연령 · 축복식 | 16 |
| `required-documents` | 축복 종류 · 국내/국제 | 17 |

5(하늘이 정해준 인연)·44(Blessing4u 등록)·26(성폭력)·6(구원)은 슬롯형이 아니다 — handoff 가 맞다.

---

## 4. 되물은 뒤 답변 경로 — §8 이 지목한 진짜 병목을 고쳤다

고치기 전 `clarification_preview.py:140-145` 는 여섯 줄로 세 가지를 동시에 깨고 있었다.

| 깨진 것 | 고친 것 |
|---|---|
| 「[요청 요약]」 한글 불릿 덩어리를 **그대로 검색어**로 넣었다 | `retrieval_query_from_summary()` — 검색 질의는 **원질문 + 고른 값**, 생성 컨텍스트만 요약 |
| `retrieval_mode` 무시하고 File Search 하드코딩 | `_effective_retrieval_mode(bot)` 를 타서 라운드0과 같은 경로 |
| strict 게이트·표기 치환을 통째로 우회 | `has_direct_citation` · `apply_term_rules` 적용 |

```bash
grep -n "retrieval_query_from_summary\|_effective_retrieval_mode\|has_direct_citation" \
  backend/app/api/v1/endpoints/clarification_preview.py
cd backend && uv run pytest tests/test_clarification_preview_api.py -q   # 7 passed
```

**파서는 형식 바로 옆에 뒀다** — `retrieval_query_from_summary` 를 `_ready_response`
아래에 둔 이유다. 형식과 파서가 다른 파일에 있으면 갈라진다.

> **남은 것 하나 — 0라운드 근거 재사용은 못 했다.**
> `/answer` 요청(`ClarificationAnswerRequest`)에 `bot_id` 와 `message` 밖에 없어서
> 라운드0의 인용이 서버로 돌아오지 않는다. 넣으려면 요청 스키마 + 클라이언트 변경이 필요하다.
>
> 다만 **「재검색 자체가 낭비」라는 진단은 틀렸다.** 사용자가 「2세 축복」을 고른 뒤에는
> 그 정보를 넣어 **다시 검색하는 게 맞다.** 진짜 결함은 재검색이 일어난 것이 아니라
> ① 질의가 형식어 덩어리였고 ② 다른 코퍼스(File Search)로 갔다는 것이었다. 둘 다 고쳤다.
> 라운드0 인용은 **버리지 말고 합치는** 방향이 맞다 — 다음 세션의 일이다.

---

## 5. 배선 안 함 — 삽입점만 남긴다

다음 세션이 다시 유도하지 않게 박아 둔다.

- **삽입점: `backend/app/services/chat_service.py:213`**
  ```python
  rag_response, _ = await answer_with_wiki(...)   # ← 이 `_` 가 Retrieved 다
  ```
  `answer_with_wiki` 는 `tuple[RAGResponse, Retrieved]` 를 돌려주는데(`wiki/service.py:144`)
  두 번째를 버린다. **점수가 이미 살아 있는 유일한 줄이다.**
- **누수 없음**: `stream_ok = request.stream and retrieval_mode == "file_search"`(`chat_service.py:390`)
  때문에 `lexical` 요청은 7개 종착 경로 중 **483 하나만** 도달한다. 213~483 사이에 넣으면
  어휘 경로 100%를 덮고 나머지 6경로로 새지 않는다.
- **프론트가 안 읽는다**: `frontend-client/.../ChatProvider.tsx` 는 완성 응답에서 `content` 와
  `followups` 둘만 읽는다. `source="ask"` 를 넣어도 **화면엔 아무것도 안 뜬다.**
  `ChatCompletionResponse.source` 가 `Literal` 이 아닌 맨 `str` 이라 백엔드 추가는 스키마 변경
  없이 되지만, 실제 비용은 `ClarificationPrototype.tsx:382` 의 ask/ready/handoff 렌더를
  `ChatArea` 로 올리는 프론트 작업이다.
- **`both` 는 삽입점이 없다**: `build_hybrid_turns`(`wiki/service.py:73-94`)가 `Retrieved` 를
  함수 안에서 버린다. 시그니처를 바꿔야 한다.
- **어휘 경로에서 strict 는 사실상 죽어 있다**: `_citations()`(`wiki/service.py:114-131`)가
  주입 유닛마다 `approximate=False` 인용을 만들어 `has_direct_citation` 이 항상 참이다.
- **배선하면 전 응답이 비스트리밍이 된다** — `lexical` 은 `stream_ok` 가 거짓이다. UX 결정이다.

---

## 6. 측정 — 두 번째 구성개념 불일치를 찾았다

### ① 판정기 3회 · 45문항

| 판정 질문 | ask | handoff | answer | 양성 12 발동 | 음성 33 오발동 |
|---|---|---|---|---|---|
| **v1** 「원문이 이 사안을 결정하는가」 | 23 | 12 | 10 | 11 | **24 (73%)** |
| **v2** 「질문자만 아는 것이 빠졌는가」 | 0 | 0 | 45 | 0 | 0 |
| **v3** = v2 + 스키마 강제 해제 | 2 | 4 | 39 | **0** | 6 (18%) |

- **v1** 은 재현율은 높지만(11/12) 음성 넷 중 셋에서 발동한다. 뱉은 결손을 보면 이유가 보인다 —
  「당해 연도 공문의 참석 기준」, 「기성축복 무효화 여부 규정」. **질문자가 모르는 것들이다.**
  되물어도 안 나온다. v1 은 코퍼스 결손을 질문 모호성으로 오인했다.
- **v2 는 결과가 아니라 사고다.** 45건 중 **31건이 판정도 못 하고 죽었다.**
  모델이 항목 하나일 때 배열 대신 문자열을 준다(`evidence: "reg-90"`). Pydantic 이 거절했고
  전부 fail-open 됐다. `_normalise_plan` 과 같은 규약(너그럽게 받고 계약은 코드에서 세운다)을
  안 쓴 대가다. 고친 뒤가 v3.
- **v3 은 양성 12건에서 한 번도 발동하지 않는다.** 그리고 이게 **판정기의 결함이 아니다.**

### ② 라벨이 틀렸다 — 이게 이번의 핵심 발견

v3 이 발동한 6건(라벨상 전부 「음성」)을 읽어 보면 **전부 진짜로 덜 적힌 질문**이다.

| n | 질문 | 판정기가 짚은 결손 |
|---|---|---|
| 33 | 2세 가정 12일 가정출발의식 절차가 뭐야? | 축복 유형(축복자녀 간 / 축복자녀-1세) |
| 34 | 2세도 가정출발 하기전에 해야되는 의식이 있어? | 축복 상대방 유형 |
| 36 | 축복정리 과정은 어떻게 되나요? | 본인 세대(1세/축복자녀) |
| 39 | 축복 받고 1년도 안 되었는데 상대가 성화했습니다. 재축복 되나요? | 가정출발(3일행사) 진행 여부 |
| 45 | B4U 등업 기준이 뭐야? | 회원등급 또는 세대 구분 |
| 18 | 축복자녀이고 1세 식구와 교제 중… 2세-1세 축복으로 준비 가능? | 가정 편성 유형 |

반대로 「양성」 12건은 **덜 적힌 질문이 아니다.** 16번은 나이를 이미 말했고, 22번은 축복
종류를 이미 말했고, 31·32번은 진행 단계를 이미 말했다. **다 적혀 있는데 규정집에 답이 없을 뿐이다.**
5번(하늘이 정해준 인연)은 애초에 규정으로 갈리는 질문이 아니고, 44번(Blessing4u 등록)은 코퍼스 밖이다.

> **무주장·지어냄은 「코퍼스 커버리지」를 재고, 재질문은 「질문 모호성」을 고친다. 둘은 다른 축이다.**
> §2-(b) 에서 검색 점수가 실패한 것과 **같은 종류의 불일치가 한 층 위에서 반복됐다.**
> 이 45문항 코퍼스로는 재질문 트리거의 값어치를 증명할 수 없다 — 실패 12건 중
> 되물어서 고쳐지는 것이 하나도 없기 때문이다.

### ③ 되물은 뒤 답변 품질 — 증명 못 했다

ask 로 걸린 2문항 × 슬롯 조합 8개를 되물어 다시 답하고 같은 자로 감사했다.

| 팔 | 셀 | 주장 | 지어냄 | 지어냄율 |
|---|---|---|---|---|
| baseline (되묻기 전, 냉동본) | 2 | 16 | 1 | 6.2% |
| clarify (되물은 뒤) | 8 | 44 | 3 | **6.8%** |

문항별로는 갈렸다 — 34번은 주장 11→1~3건으로 줄고 지어냄 1→0 이 됐지만,
33번은 4개 분기 중 2개에서 없던 지어냄이 생겼다.

**성공 기준 3(지어냄이 줄어든다)은 충족되지 않았다.** 다만 이 숫자로 실패를 선언해서도 안 된다:
n 이 2문항 8분기로 너무 작고, 분기를 **선택지 전수**로 만들었기 때문에 질문자의 실제 상황이
아닌 조합이 섞여 있다. 「2세 축복이라고 가정하고 정확히 답한 것」은 지어냄이 아니지만
주장 수를 늘린다. **사용자를 지어내지 않으려다 측정이 흐려졌다** — 다음 세션의 설계 문제다.

### ④ 성공 기준 대비

| 기준 | 목표 | 결과 |
|---|---|---|
| 무주장 6건 중 ask 전환 | ≥4 | **0** — 다만 §6-② 대로 이 6건은 되물을 거리가 없다 |
| 음성 33건 오발동 | ≤3 | 6 — 그런데 그 6건은 읽어 보면 진짜 모호한 질문이다 |
| 되물은 뒤 지어냄 감소 | 감소 | **증명 못 함** (6.2% → 6.8%, n=2문항) |

세 기준 모두 **이 라벨 위에서는 해석이 안 된다.** 라벨을 바꾸는 것이 먼저다.

---

## 6-A. 다음 세션이 할 일 — 순서대로

1. **재질문용 라벨을 만든다.** 45문항을 「되물으면 답이 갈리는가」로 사람이 직접 표시한다.
   무주장·지어냄에서 유도하지 마라 — 다른 축이다(§6-②). v3 이 짚은 6건이 출발점이다.
2. **그 라벨 위에서 v3 을 다시 잰다.** 지금 있는 하네스로 재실행만 하면 된다(§8).
3. **분기 설계를 고친다.** 선택지 전수 대신, 질문에 이미 적힌 정보로 정답 분기를 정하고
   그 분기만 재답변한다. 그래야 「되물은 뒤 품질」이 흐려지지 않는다(§6-③).
4. 시드 규칙은 **틀린 표적(12건)을 보고 썼다.** 라벨을 고친 뒤 다시 써야 한다.
   지금 규칙으로 36·39·45·18 이 handoff 로 빠진 건 규칙이 없어서지 판정이 틀려서가 아니다.
5. 배선은 그 다음이다(§5).

---

## 7. 함정

1. `wiki_eval/_run.py` 를 `--retry-failed` 없이 돌리면 `answers.json` 이 `audit.json` 과 어긋난다
2. `Retrieved.top_score` 는 호출자 0개 · 범위 1.22배 — 되살리지 마라 (§2-c)
3. `WIKI_DENSE_SCALES` 를 켜면 RRF 점수가 대략 2배 — 상수 임계값의 의미가 뒤집힌다
4. 냉동 기준선은 `system_prompt + GUIDE` 로 생성됐다. 재답변에서 GUIDE 를 빼면
   **프롬프트가 다른 두 시스템을 비교**하게 된다 (`clarify_eval/_run.py:GUIDE`)
5. Gemini 일일 쿼터(리셋 KST 16:00). 소진 이력 있음 — 단계를 나눠 돌리고 재개는 `--retry-failed`
6. `exports/` 는 gitignore(`.gitignore:25`). 하네스는 `git add -f` 로 추적시켰다 —
   안 그러면 다음 세션이 재현할 수 없다
7. **모델은 항목 하나일 때 배열 대신 문자열을 준다**(`evidence: "reg-90"`). 구조화 출력 스키마를
   새로 만들 때마다 물린다 — 45건 중 31건이 이걸로 죽었다. `field_validator(mode="before")` 로
   받아라. `_normalise_plan`(clarification_service.py) 이 같은 이유로 존재한다
8. `_audit.py` 의 요약 출력은 `ARM_LABEL` 에 없는 팔 이름에서 `KeyError` 로 죽는다.
   **감사 자체는 다 끝난 뒤**라 `audit.json` 은 멀쩡하다 — 요약은 따로 계산하면 된다
9. **⚠ 로컬 docker 와 Neon 은 같은 `bots.id` 에 서로 다른 봇이 들어 있다.**
   로컬 봇 11 = `opus2_v4`(5,608자) / 라이브 봇 11 = **테스트 봇 D-1 ver2**(1,341자).
   `.env` 의 활성 `DATABASE_URL` 은 localhost 라 하네스를 그냥 돌리면 로컬 봇을 잰다.
   판별법은 `_run.py` 가 찍는 프롬프트 길이 — **1341자가 아니면 라이브가 아니다.**
   상세와 검증은 `handoff-evidence-audit-45set-2026-08-10.md` §6-A

---

## 8. 재현

```bash
# ① 판정 45문항 (Gemini 45회 · 약 12분)
cd backend && uv run python -u ../exports/clarify_eval/_run.py --stage judge --retry-failed

# ② 되물은 뒤 재답변 (ask 로 걸린 문항 × 슬롯 조합, 문항당 최대 4)
cd backend && uv run python -u ../exports/clarify_eval/_run.py --stage reanswer --retry-failed

# ③ 감사 — 기존 자 그대로. codex, Gemini 0회
cd backend && AUDIT_DIR="$PWD/../exports/clarify_eval" AUDIT_ARMS=baseline,clarify \
  uv run python -u ../exports/wiki_eval/_audit.py --stage all

# 테스트 · 부팅
cd backend && uv run pytest -q
git archive HEAD | tar -x -C /tmp/bootcheck && cd /tmp/bootcheck/backend && uv run python -c "import app.main"
```
