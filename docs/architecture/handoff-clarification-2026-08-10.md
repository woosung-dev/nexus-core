# 인계 — 맥락 부족 시 재질문(clarification) 트랙 (2026-08-10)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 모두 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 아래와 다르면 **그 사이에 코드가 바뀐 것이다.** 문서가 아니라 코드를 따르라.

---

## 0. 지금 상태 (30초)

| | 값 | 확인 |
|---|---|---|
| 브랜치 | `main` = `6cddfa8` | `git log --oneline -1 main` |
| alembic 헤드 | `2e7f2e0417ec` (로컬·라이브 동일) | 아래 §1-① |
| 라이브 봇 | **11개, 전부 `retrieval_mode='file_search'`** | 아래 §1-① |
| `ops_facts` | **0행** (로컬·라이브 모두) | 아래 §1-① |
| `redteam_goldens` | 40행, 전부 초안 | 아래 §1-① |
| 미배선 | PR #50 재질문 레이어가 **본 채팅 경로에 안 붙어 있음** | 아래 §2-① |

**다음 세션의 목적:** 사용자 질문에 근거가 부족할 때 **답을 지어내지 말고 되묻는** 트리거를 만든다.
프롬프트는 `next-session-clarification-prompt-2026-08-10.md`.

---

## 1. 데이터 상태

### ① 테이블 행수 · 봇 모드 · alembic 헤드

```bash
cd backend
cat > /tmp/cnt.py <<'PY'
import asyncio, asyncpg, sys
async def main(dsn, label):
    c = await asyncpg.connect(dsn, timeout=25)
    print(f"--- {label} ---")
    for t in ["wiki_source_units","wiki_pages","ops_facts","redteam_goldens","faqs","bots"]:
        print(f"{t:20}", await c.fetchval(f"select count(*) from {t}"))
    print("retrieval_mode:", [(r['m'], r['c']) for r in await c.fetch(
        "select coalesce(retrieval_mode,'(null)') m, count(*) c from bots group by 1")])
    print("alembic:", await c.fetchval("select version_num from alembic_version"))
    await c.close()
asyncio.run(main(sys.argv[1], sys.argv[2]))
PY
# 로컬(docker compose db 필요)
uv run python /tmp/cnt.py "postgresql://nexus_user:nexus_pass@localhost:5432/nexus_core" 로컬
# 라이브 — .env 11행의 Neon URL을 pooler 제거·ssl 파라미터 제거해서 직결
```

확인된 값 (2026-08-10):

| 테이블 | 로컬 | 라이브 |
|---|---|---|
| `wiki_source_units` | 250 | 250 |
| `wiki_pages` | 138 | 138 |
| `ops_facts` | **0** | **0** |
| `redteam_goldens` | 40 | 40 |
| `faqs` | 70 | **71** |
| `bots` | 21 | **11** |
| `retrieval_mode` | file_search 21 | **file_search 11** |
| alembic | `2e7f2e0417ec` | `2e7f2e0417ec` |

> **함정:** 로컬 21봇 / 라이브 11봇이다. 예전 문서·대화에서 "라이브 봇 21개"라고 쓴 곳은 **틀렸다.**

### ② `wiki_facts` 테이블은 **없다**

"위키 사실문장 971건"은 테이블이 아니다. 인덱스를 만들 때 `wiki_pages` 본문의 「사실」 섹션을
줄 단위로 파싱해 **메모리에만** 올린다.

```bash
grep -n "_scale_fact" backend/app/services/wiki/store.py     # → 307, 328
sed -n '328,361p' backend/app/services/wiki/store.py         # page.facts.split("\n")
```

→ SQL 로 사실문장을 조회할 방법은 없다. 필요하면 인덱스를 빌드해야 한다.

### ③ 봇마다 보는 원본 판본이 다르다 — DB에는 그 사실이 없다

Gemini File Search 스토어의 문서는 `bot_id` custom metadata 로 구분되고,
**봇 11 = 규정집 v20 + 대사전**, **봇 4·6·7·8·9 = 2022년판**이다.
이 정보는 우리 DB 어디에도 없다.

```bash
cd backend && set -a; source .env; set +a
uv run python ../exports/_rag_snapshot.py     # 읽기전용, 봇ID별 문서 목록·버전 덤프
```

> **함정:** 봇 대 봇 비교를 할 때 원본 판본 차이를 통제하지 않으면 프롬프트 차이로 오독한다.

---

## 2. 재질문(clarification) 레이어 — 있는 것 / 없는 것

### ① 본 채팅 경로에 **배선되어 있지 않다** (가장 중요)

```bash
grep -c "clarif\|Clarif" backend/app/services/chat_service.py     # → 0
```

PR #50 이 만든 것은 **별도 프로토타입 경로**다. `process_chat_request` 는 재질문을 모른다.

### ② 이미 있는 것 (재사용 대상, 다시 만들지 말 것)

```bash
git ls-files | grep -i clarif
```

| 파일 | 내용 |
|---|---|
| `backend/app/services/clarification_service.py` (837줄) | 재질문 계획 생성·검증·정책 매칭 전부 |
| `backend/app/schemas/clarification_policy.py` | 관리자가 쓰는 정책 스키마 |
| `backend/app/api/v1/endpoints/clarification_preview.py` | `POST /clarification-preview`, `/answer` |
| `frontend-admin/.../clarification-policy-section.tsx` | 관리자 정책 편집 화면 |
| `frontend-client/.../ClarificationPrototype.tsx` | 클라이언트 프로토타입 UI |
| `backend/tests/test_clarification*.py` | 테스트 22개 |

**정책 스키마의 핵심 필드** (`clarification_policy.py`):
- `required_slots[]` — 되물을 항목. `options[]` + `allow_custom`
- `when_unknown: "ask" | "handoff" | "allow_answer"` — 모를 때 무엇을 할지
- `enabled`, `priority` — 규칙 on/off 와 우선순위

**응답 상태 3종**: `ask`(되묻기) / `ready`(답변 가능) / `handoff`(사람에게)

→ **판정·정책·관리자 UI·클라이언트 UI 는 이미 있다. 없는 것은 "언제 되물을지"를 정하는 신호다.**

### ③ 현재 트리거 방식과 그 한계

```bash
grep -n "generate_structured_with_rag\|evidence_matches_current_retrieval" \
  backend/app/services/clarification_service.py     # → 430, 644
grep -n "CLARIFICATION_MODEL" backend/app/services/clarification_service.py   # → 38
```

- 모델 `gemini-3.5-flash-lite` 가 **계획(plan)을 생성**하고, 그 근거가 File Search 인용과
  일치하는지 검증한다(`_validate_ask_plan`).
- 즉 **LLM 이 "되물을지 말지"를 판단한다.** PR #51(적응형 라우팅)이 이 방식으로 실패했다
  — 60문항 중 **30건 경로 불일치**로 클로즈.

### ④ `clarify_enabled` 는 프로토타입 게이트일 뿐

```bash
grep -rn "clarify_enabled" backend/app
```

`clarification_preview.py:107` 한 곳에서만 읽는다. 켜도 사용자 채팅에는 아무 영향이 없다.

---

## 3. 결정적 사실 — `lexical` 은 점수를 준다, `file_search` 는 안 준다

```bash
grep -n "class Retrieved" -A 25 backend/app/services/wiki/store.py | grep -n "top_score\|ranked_units\|pages:"
grep -rn "score" backend/app/services/rag/*.py     # → 0건
```

| | 검색 점수 | 재질문 트리거로 쓸 수 있나 |
|---|---|---|
| `lexical` (BM25+RRF) | `Retrieved.pages` / `.ranked_units` / `.top_score` | **가능. 결정적 임계값.** |
| `file_search` (Gemini) | **없음** — relevance score 미반환 | 불가. LLM 판단밖에 없음 |

→ **`lexical` 전환과 재질문 트랙은 같은 방향이다.** `file_search` 위에서는 결정적 트리거를 못 만든다.

### RRF 는 두 번 돈다

```bash
grep -n "rrf(" backend/app/services/wiki/store.py     # → 507(page), 508(unit)
```

3개 스케일(page 138 / unit 250→292청크 / fact 971)의 히트가 **페이지 공간**과 **유닛 공간**
두 곳으로 투영돼 각각 융합된다. 임계값을 잡을 때 어느 공간의 점수인지 명시해야 한다.

---

## 4. 실측 — 45문항 225셀 근거감사 (정본)

정본 문서: `docs/architecture/handoff-evidence-audit-45set-2026-08-10.md`
(`handoff-overnight-2026-08-10.md` 의 25문항 표는 **순위가 다르다.** 인용 금지)

| 팔 | 지어냄율 | 모순 | 커버리지 | **무주장 셀** |
|---|---|---|---|---|
| `file_search` (현 기본값) | **14.2%** | 3 | 56.6% | **0 / 45** |
| `both` | 11.4% | **6** | 50.1% | 6 / 45 |
| `lexical` | **3.4%** | **0** | 44.2% | **6 / 45** |

**「무주장 셀」이 재질문 트랙의 자연스러운 지표다.**
`file_search` 는 45문항 전부에서 무언가를 주장했다 — 모를 때 모른다고 하지 않는다.
`lexical` 은 6번 침묵했다. **그 6건이 재질문 후보다.**

목표는 무주장 6건을 「되묻고 → 답한다」로 바꾸는 것이지, 무주장을 0으로 만드는 게 아니다.

---

## 5. 런타임 구조 — 손대기 전에 알아야 할 것

### ① 종착 경로는 7개다

```bash
grep -n "return " backend/app/services/chat_service.py | \
  awk -F: '$1>293 && $1<560'      # → 347, 393, 410, 483, 503, 514, 551
```

| 줄 | 경로 |
|---|---|
| 347 | FAQ 히트 (RAG·운영사실·히스토리 전부 건너뜀) |
| 393 | strict RAG **스트리밍** |
| 410 | RAG **스트리밍** |
| 483 | strict RAG 비스트리밍 |
| 503 | policy_block |
| 514 | LLM **스트리밍** |
| 551 | RAG/LLM 비스트리밍 |

재질문을 넣는다면 **7경로 전부**를 확인해야 한다. 하나만 고치면 나머지 6개로 새어나간다.

### ② `lexical` · `both` 는 스트리밍이 안 된다

```bash
grep -n "stream_ok" backend/app/services/chat_service.py     # → 390
```

```python
stream_ok = request.stream and retrieval_mode == "file_search"
```

→ `lexical` 로 전환하면 **모든 응답이 비스트리밍**이 된다. UX 영향이 있고, 재질문 UI 설계도
스트리밍 없는 전제 위에서 해야 한다.

### ③ 표기 치환이 스트리밍 3경로에 빠져 있다 (기존 결함)

```bash
grep -n "apply_term_rules" backend/app/services/chat_service.py   # → 448, 449, 536 (비스트리밍만)
awk 'NR>=559 && NR<=730' backend/app/services/chat_service.py | grep -c apply_term_rules   # → 0
```

`_generate_strict_rag_stream`(559) · `_generate_rag_stream`(612) · `_generate_llm_stream`(686)
세 생성기 어디에도 없다. **재질문 트랙과 무관한 별개 버그.** 고칠 거면 별도 PR 로.

---

## 6. 아키텍처 채점 결과 (codex, 3시선 독립)

`scratchpad/arch_eval/` 에 원본. 시선별 스키마 강제(`--output-schema`)로 받았다.

| 시선 | 현행 A | 제안 B |
|---|---|---|
| 유지보수(maint) | 3 | 6 |
| 운영(ops) | 3 | 6 |
| 가치(value) | 4 | 5.5 |
| **평균** | **3.33** | **5.83** |

세 시선이 공통으로 지목한 A 의 최대 약점: **`ops_facts` 가 0행이고 공급원이 없다.**
세 시선이 공통으로 지목한 B 의 최대 위험: **제안 어느 것도 지어냄율을 직접 낮추지 않는다**
(그건 `retrieval_mode` 전환의 몫).

### 실행 순서 (채점 반영 후)

1. **`lexical` 전환** — 지어냄율 14.2% → 3.4%. 유일하게 품질을 직접 바꾼다
2. `bot_corpus` 테이블 + 판본 동기화 잡
3. FAQ 71건을 기존 감사기에 입력으로 투입 (신규 코드 아님)
4. `evidence_violations` 테이블 + 반복 위반의 ops_facts 승격
5. 정답지 ↔ 운영사실 연결

**재질문 트랙은 1번과 붙어 있다** — §3 참조.

---

## 7. 참고 산출물

브라우저에서 볼 수 있는 다이어그램(레포 밖):

| 내용 | URL |
|---|---|
| BM25 / RRF / Dense 가 각각 어느 데이터에 쓰이나 | https://claude.ai/code/artifact/5251b7eb-0fe0-4cd9-a6f0-6e6ee6c0da51 |
| 데이터 지형(같은 PDF 2벌) + Postgres 내부 구조 | https://claude.ai/code/artifact/38901f29-ed9a-4391-87ec-5609d5df8926 |
| 백엔드 요청 흐름 — 종착 경로 7개 | https://claude.ai/code/artifact/17b49c49-b6a5-4828-8036-63130b3f5e2e |
| Context Intelligence 조사 + 개선 제안 | https://claude.ai/code/artifact/5fda53ba-9207-49aa-9097-8a287f4a0847 |
| 현행 vs 제안 구조 비교 + codex 점수 | https://claude.ai/code/artifact/36d1ee2a-68c9-47ea-8832-efbdc61a0aa3 |

측정 하네스:

```bash
# 실패한 셀만 재시도 — 성공한 셀을 다시 부르면 답변이 새로 생성돼
# 앞서 감사·채점한 결과와 어긋난다. 반드시 이 플래그를 쓸 것.
uv run python exports/wiki_eval/_run.py --retry-failed
```

---

## 8. 업계 조사 요약 (재질문 설계 근거)

- **"Clarify Once, Learn the Default"** — 확신도 임계값으로 갈라라. 0.60 미만은 항상 묻고,
  0.60~0.85 는 가끔 묻고, 0.85 초과는 조용히 기본값을 적용한다. 확정된 기본값은 별도 테이블에
  저장한다 — **우리 `ops_facts` 와 구조가 같다.**
- **"Clarification Is Not Enough: Post-Clarification Answering Remains the Bottleneck
  in Multi-Turn QA"** — 병목은 "언제 물을지"가 아니라 **"되물어 받은 답으로 제대로 답하는지"**다.
  PR #51 이 라우팅만 최적화하다 실패한 이유를 설명한다.

→ **측정 대상은 재질문 발생률이 아니라 「재질문 이후 답변 품질」이다.**
