# 인계 — 「답변 못 함」 3층 구조 (2026-08-11)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 다르면 **그 사이에 코드가 바뀐 것이다. 문서가 아니라 코드를 따르라.**

---

## 0. 지금 상태 (30초)

| | 값 | 확인 |
|---|---|---|
| 브랜치 | `feat/clarification-trigger` (미푸시) | `git log --oneline -5` |
| 테스트 | 151 통과 | `cd backend && uv run pytest -q` |
| **라이브 봇 11** | **`retrieval_mode=lexical`** (2026-08-11 전환) | §7-① |
| `ops_facts` | **0행** · 관리자 화면은 있음(`/ops-facts`) | §7-① |
| `messages.source` | **컬럼 없음** — 「못 답함」이 데이터로 안 남는다 | §7-② |
| CI | **테스트를 안 돌린다.** main push → 바로 배포 | §7-③ |

**목표: 답할 수 없을 때 고정 문구를 내고, 그 사실을 기록하고, 관리자가 빈도순으로 본다.**

---

## 1. 이번 세션의 최종 결론 넷

### ① 검색 점수로 「답할 수 있나」를 판정할 수 없다 — 시도하지 마라

네 갈래(페이지 RRF@1 · 유닛 RRF@1 · 원 BM25@1 · 질의어 IDF 커버리지) 전부 실패.
**근거는 통계(AUC)가 아니라 기전 셋이다:**

- **반례가 양 끝에 있다.** Q22 = 코퍼스 최고 BM25(62.27)인데 주장 0건 / Q44 = 최저(6.29) 역시 0건 /
  Q26 = 두 번째 최저(6.69)인데 지어냄 1건
- **재는 것이 다르다.** BM25 는 「코퍼스가 이 단어를 다루나」를 재고, 필요한 건 「이 사안을 결정하는
  조문이 있나」다. **가장 온토픽한 질문이 가장 답할 수 없는 질문일 수 있다**
- **RRF 는 구조적으로 범위가 없다.** `1/(60+rank)` 합이라 관측 범위 1.22배(페이지)·1.08배(유닛).
  **코퍼스를 바꿔도 안 넓어진다**

같은 종류의 시도가 **과거에도 두 번 기각**됐다 — 인용 형광펜 어휘매칭(정확도 25%),
관리자 근거상태 라벨(45문항 중 66%만 일치, *"근거 판정은 어휘 카운트로 하면 안 됨"*).
**합쳐서 3전 3패다. 네 번째를 하지 마라.**

정본: `handoff-clarification-trigger-2026-08-11.md` §2

### ② FAQ 는 차단 전용이다 — 「못 답함」 안내를 FAQ 로 처리하지 마라

FAQ 가 히트하면 `chat_service` 가 **RAG·운영사실·히스토리를 통째로 건너뛴다.**
그래서 near-miss 가 「덜 좋은 답」이 아니라 **「근거 없는 오답」**이 된다.

정본: `faq-usage-policy.md` · 코드에도 박아 뒀다(`faq_service.py` 모듈 docstring)

### ③ 「사실을 넣는 자리」는 `ops_facts` 다

```
FAQ 히트    → 지정답변 반환. 검색 안 돌림. 근거 없음.   ← near-miss = 오답
ops_facts   → 프롬프트에 얹힘. 검색 정상 수행.          ← 구조적으로 안전
```
**둘 다 「관리자가 쓴 문장」인데 하나는 검색을 끄고 하나는 안 끈다.** 그 차이가 전부다.

### ④ 출력과 판정을 갈라야 한다

| | 결정론 가능? |
|---|---|
| **출력** — 어떤 문장을 보여줄까 | **✅ 100%.** 코드가 고정 문자열을 낸다 |
| **판정** — 답할 수 있나 | ❌ 완전 결정론 불가 (①때문) |

**지금 문구가 흔들리는 건 프롬프트에 맡겨서다.** 코드가 치환하면 출력의 확률은 0이 된다.

---

## 2. 만들 것 — 3층

```
1층  결정론 게이트   검색 빈손 · 인용 0건          → 고정 문구      확률 0
2층  구조화 출력     모델은 true/false 만 뱉는다    → 코드가 치환    판정만 확률
     + evidence 대조 src_id 가 주입 목록에 있나     → 문자열 비교    결정론
3층  기록·관리자화면 전부 남긴다 → 빈도순 목록
                                    ↓
                        ops_facts 에 답을 쓴다 → 다음엔 답이 나간다
```

### 1층 — 결정론 게이트 (여기부터. 확률 0)

지금 이 신호들이 **폴백에 삼켜져 사라진다.** 기록으로 살린다.

| 신호 | 현재 위치 | 지금 동작 |
|---|---|---|
| 1단 검색 빈손 | `wiki/service.py` (`not retrieved.pages` 검사) | 빈 답변 반환 |
| 어휘 검색 빈 답변 | `chat_service.py` lexical 분기 | **file_search 로 폴백** |
| 직접 인용 0건 | `strict_mode.has_direct_citation` | strict 봇만 차단 |

> **함정: 어휘 경로에서 `has_direct_citation` 은 항상 참이다.** `wiki/service.py` 의
> `_citations()` 가 주입 유닛마다 `approximate=False` 인용을 만든다. 어휘 봇에 이걸
> 게이트로 쓰면 **절대 안 걸린다.**

**폴백을 없애지 마라.** 폴백은 사용자 보호 장치다. **폴백했다는 사실을 기록만** 한다.

### 2층 — 구조화 출력 + 코드 치환

**새로 만들지 마라. 이번 세션에 이미 있다.**

- `backend/app/services/rag/gemini.py` → `generate_structured()` — File Search 없는 구조화 호출
- `backend/app/services/clarification_trigger.py` → `judge_answerability()` — 판정 + evidence 대조 + fail-open

`needs_user_input`(되물을까) 축을 `answerable`(답할 수 있나) 축으로 바꿔 쓰면 된다.
**검증 실패 시 답변을 진행한다(fail-open)** — 판정기가 고장 나서 제품이 벙어리가 되는 쪽이 더 나쁘다.

> **함정: 모델은 항목이 하나면 배열 대신 문자열을 준다**(`evidence: "reg-90"`).
> 45건 중 31건이 이걸로 죽어 결과가 통째로 허수였다. `field_validator(mode="before")` 필수.
> 이미 `clarification_trigger.py` 에 들어 있다.

### 3층 — 기록과 관리자 화면 ★ 이번 세션의 주 목표

**지금 「못 답했다」가 데이터로 안 남는다.** `messages` 테이블에 구분 컬럼이 없다
(`source` 는 API 응답에만 있고 저장 안 됨). 마이그레이션 1개가 필요하다.

관리자 화면 요구:

```
못 답한 질문                      횟수   최근        상태
──────────────────────────────────────────────────────
축복 헌금 금액이 얼마인가요         23    2시간 전    미처리
B4U 등록 어떻게 하나요              17    1일 전      미처리
올해 축복식 참가 연령 기준          12    3일 전      ▶ 운영 사실 등록됨
```

- **빈도순이 핵심이다.** 「무엇부터 채울지」를 이 화면이 정해 준다
- 항목에서 `ops_facts` 등록으로 바로 넘어갈 수 있어야 루프가 닫힌다
- **UI 는 `/ui-ux-pro-max:ui-ux-pro-max` 스킬을 써서 만들 것** (사용자 지시)
- 기존 관리자 화면 관례를 따를 것 — `frontend-admin/src/app/(admin)/ops-facts/`, `/chats/` 참고

---

## 3. 제약 — 이유와 함께

- **FAQ 로 해결하려 하지 마라.** §1-② 참조. 차단 전용이다
- **과잉 거절 금지.** 봇 11은 이미 어휘 검색이라 커버리지가 44.2%다(전환 전 56.6%).
  게이트를 세게 걸면 「맨날 모른대」가 된다. **사용자에게 보이는 문구는 1층(확실할 때)만,
  기록은 관대하게** — 두 임계를 나눠라
- **로그에 민감한 사정이 들어간다.** 테스트 문항에도 성폭력·이혼·불륜이 있었다.
  실제 사용자 질문을 관리자 화면에 그대로 띄우는 것이라 **접근 권한·보존 기간을
  시작 전에 정할 것**
- **라이브 DB 는 읽기만.** 쓰기가 필요하면 사용자에게 먼저 물어라. `backend/.env` 에
  Neon 자격증명이 있다 — 커밋 금지
- **「아직 정리되지 않았다」는 약속이 된다.** 사용자가 기다린다. **누가 언제 검수하는지**가
  안 정해지면 문구를 내면 안 된다. 기술이 아니라 운영 문제고, 여기가 제일 자주 무너진다

---

## 4. 열려 있는 것 — 사용자에게 물어서 정할 것

1. **문구 확정** — 「아직 **학습**되지 않은」 vs 「아직 **정리**되지 않은」
   (사용자·관리자 합의안: *"근거를 찾을 수 없거나 아직 ○○되지 않은 내용입니다.
   담당 교회장님이나 가정행복국(02-3271-0502)으로 연락 부탁드립니다."*)
   ※ 「학습」이 AI 학습으로 오해될 수 있어 남겨 둔 결정이다
2. **로그 접근 권한·보존 기간** (§3 세 번째 제약)
3. **검수 주체·주기** (§3 다섯 번째 제약)

---

## 5. 안 하는 것 (이번 세션 범위 밖)

- **재질문 배선** — 별도 트랙. 라벨부터 만들어야 한다.
  `handoff-clarification-trigger-2026-08-11.md` §6-A
- **기본값 `lexical` 전환** — 봇 11 관찰 결과가 먼저다
- **`both` 검토** — 모순 6건으로 세 팔 중 최악. 접었다

---

## 6. 다음 세션이 모를 컨텍스트

- **시스템 프롬프트에 이미 재질문·거절 규칙이 들어 있다.** 봇 11 프롬프트(1,341자) 3번 항목이
  *"불명확하면 되물어라, 한 번까지"*, 1번이 *"규정집에 없으면 확인되지 않습니다 + 가정행복국"*.
  **라이브에서 실제로 그렇게 동작한다.** 즉 「없는 걸 새로 만든다」가 아니라
  **「이미 일어나는 걸 고정하고 기록한다」**가 정확한 표현이다
- **프롬프트가 "최신 공문을 우선하라"고 시키는데 공문이 지식에 없다.** 이게 `ops_facts` 가
  필요한 가장 깨끗한 예시다
- **`ops_facts` 는 코드·화면·승인 절차가 전부 있고 내용만 0행이다.** 새로 만들 것 없다
- **채울 후보 목록이 이미 있다** — `exports/clarify_eval/results_v1_corpus_gap.json`
  (34문항에서 66건). 재질문 트리거로는 실패한 판정기의 부산물인데 **구멍 탐지기로는 성공**했다.
  단 이건 **시험문제에서 나온 목록**이라, 실사용 로그가 더 정확한 목록을 준다 — 그래서 3층이 먼저다
- **관리자 UI 프리셋 숫자가 낡았다.** 「정확 우선」이 지어냄 8.2% 로 표시되는데 정본은 **14.2%** 다
  (25문항 표본값). `frontend-admin/src/features/bots/schemas.ts` — 별건으로 고칠 것

---

## 7. 확인 명령

### ① 라이브 상태 (읽기 전용)

```bash
cd backend && uv run python - <<'PY'
import asyncio, asyncpg, re, pathlib
line=[l for l in pathlib.Path('.env').read_text().splitlines() if 'neon.tech' in l][0]
dsn=line.split('=',1)[1].strip().replace('postgresql+asyncpg://','postgresql://').replace('-pooler','')
dsn=re.sub(r'[?&]ssl(mode)?=[^&]*','',dsn)
async def main():
    c=await asyncpg.connect(dsn,timeout=30)
    print("bots:", await c.fetchval("select count(*) from bots"))
    print("봇11:", dict(await c.fetchrow("select name,retrieval_mode,evidence_policy_mode from bots where id=11")))
    print("ops_facts:", await c.fetchval("select count(*) from ops_facts"))
    await c.close()
asyncio.run(main())
PY
# 기대: bots 11 · 봇11 = 테스트 봇 D-1 ver2 / lexical / legacy · ops_facts 0
```

> **⚠ 로컬 docker 와 Neon 은 같은 `bots.id` 에 다른 봇이 들어 있다.**
> 로컬 봇11 = `opus2_v4`(5,608자) / 라이브 봇11 = **테스트 봇 D-1 ver2**(1,341자).
> `.env` 의 활성 `DATABASE_URL` 은 **localhost** 다. 상세: `handoff-evidence-audit-45set-2026-08-10.md` §6-A

### ② `messages` 에 구분 컬럼이 없다

```bash
grep -n "source" backend/app/models/chat.py     # → 없음
grep -n "source" backend/app/schemas/chat.py    # → 응답 스키마에만 있음
```

### ③ CI 가 테스트를 안 돌린다

```bash
grep -n "pytest" .github/workflows/deploy-backend.yml   # → 없음
```
main push → build → 배포 → `/health` 200 확인이 전부다. **깨진 코드도 배포된다.**

### ④ 이번 세션 산출물

```bash
git log --oneline -5
ls docs/architecture/faq-usage-policy.md \
   docs/architecture/handoff-clarification-trigger-2026-08-11.md \
   docs/architecture/clarification-policy-seed-2026-08-11.json
ls exports/clarify_eval/          # results_v1_corpus_gap.json = 66건 목록
```

---

## 8. 작업 방식

첫 응답에서 계획을 길게 쓰지 마라. 읽어야 할 코드를 읽고, 확인 명령부터 돌려라.

응답은 결론부터. 처음 한 문장이 「무슨 일이 있었나 / 무엇을 찾았나」에 답해야 한다.
짧게 쓰려고 축약어·화살표 사슬로 압축하지 말고, 넣을 내용을 고르는 쪽으로 줄여라.

서브에이전트는 아껴 써라. 여러 파일에 걸친 폭넓은 조사처럼 정말 독립적이고 큰 갈래일 때만
쓰고, 검증 목적으로는 쓰지 마라.

**커밋 전 부팅 확인은 필수다** — 커밋된 코드가 미추적 모듈을 import 하는 사고가 두 번 있었다.
```bash
git archive HEAD | tar -x -C /tmp/bootcheck && cd /tmp/bootcheck/backend && uv run python -c "import app.main"
```
