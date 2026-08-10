# 인계 — 「답변 못 함」 3층: 만들었고, 라이브만 남았다 (2026-08-10)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 다르면 **그 사이에 코드가 바뀐 것이다. 문서가 아니라 코드를 따르라.**
>
> 선행 문서: `handoff-unanswerable-layer-2026-08-11.md` (설계·제약) — 이 문서는 그 실행 기록이다.

---

## 0. 지금 상태 (30초)

| | 값 | 확인 |
|---|---|---|
| 브랜치 | `feat/clarification-trigger` — main 대비 **6커밋**, **미푸시** | `git log --oneline origin/main..HEAD` |
| 테스트 | **169 통과** | `cd backend && uv run pytest -q` |
| 로컬 DB | 마이그레이션 적용됨 (`f4a7b2c9d1e6`) | `cd backend && uv run alembic current` |
| **라이브 DB** | **미반영** — `alembic=2e7f2e0417ec`, `unanswered_questions` 없음 | §6-① |
| `ops_facts` | 여전히 **0행** | §6-① |

**남은 것은 배포 하나다.** 코드·테스트·화면은 끝났고 로컬에서 왕복 확인까지 했다.

---

## 1. 만든 것 — 3층

```
1층  결정론 게이트   최종 답변이 빈 문자열      → 고정 문구로 치환    확률 0
2층  구조화 출력     judge_answerability       → 응답 뒤 비동기      기록 전용
3층  기록·관리자화면 신호 5종 → /unanswered    → 빈도순 + triage 4값
```

핵심 파일 (`git show --stat bf427a3` 로 전체 24개 확인):

| 파일 | 역할 |
|---|---|
| `backend/app/services/unanswered.py` | 고정 문구 상수 · 이유코드 5종 · 정규화 · 자기거절 판정 |
| `backend/app/models/unanswered.py` | `unanswered_questions` 표 |
| `backend/app/crud/crud_unanswered.py` | 기록 · **빈도 집계(GROUP BY)** · triage 쓰기 |
| `backend/app/api/v1/endpoints/admin/unanswered.py` | 목록 · 발생상세 · triage PATCH |
| `frontend-admin/src/features/unanswered/` | 화면 전체 |
| `frontend-admin/src/features/ops-facts/components/ops-fact-create-dialog.tsx` | 루프를 닫는 자리 |
| `scripts/purge_unanswered.py` | 90일 보존 적용 (수동 실행) |

---

## 2. 설계에서 인계와 갈라진 점 셋 — 근거와 함께

### ① 「인용 0건 → 고정 문구」는 넣지 않았다

선행 인계 §2 의 1층 조건이 「검색 빈손 · **인용 0건**」인데 인용 0 은 게이트로 못 쓴다.
메모리 `reference_rag_grounding_underreports` 가 실측으로 정리한 것 — **인용 0 ≠ RAG 미작동**.
게다가 어휘 경로에서는 `wiki/service.py:114-131` 의 `_citations()` 가 주입 유닛마다
`approximate=False` 인용을 만들어 **항상 ≥1건**이라 애초에 안 걸린다.

**그래서 사용자에게 문구가 나가는 조건은 「최종 답변이 빈 문자열」 하나뿐이다.**
100% 결정론이고, 지금은 빈 말풍선이 그대로 나가므로 과잉 거절 위험이 0이다.

### ② 2층은 판정 축을 바꾸지 않았다

인계 §2 는 `needs_user_input` 축을 `answerable` 축으로 바꾸라 했다. 그런데 **같은 인계
§6-① 표에서 그 `answerable` 축이 v1 이고 45문항 중 35건(78%)에서 발동**한다(ask 23 + handoff 12).
78% 가 뜨는 로그는 기록으로도 정렬이 안 된다.

`clarification_trigger.judge_answerability` 를 **한 글자도 안 고치고** 그대로 shadow 로 돌린다
(v3 기준 6/45 = 13% 발동). 부수 효과 — 재질문 트랙이 필요로 하는
「되물으면 답이 갈리는가」 라벨의 재료가 실사용 로그에서 나온다.

### ③ 화면 상태를 2값이 아니라 **처리 경로 4값**으로 뒀다

인계의 모형은 「미처리 / 운영사실 등록됨」이었다. 그런데 `ops_facts` 모델 docstring 이
**positive 지식을 담지 않는다**고 못 박아 뒀고 `kind` 5종이 전부 부정·치환·연락처다.
덮개가 기본 경로가 되면 문서 개선 트랙이 조용히 죽는다.

```
문서없음   → Documents 업로드          (지금 유일하게 돌아가는 문서 트랙)
검색못함   → 검색기·위키 트랙
문서오류   → ops_facts               ← 여기서만 등록 다이얼로그가 열린다
해당없음   → 답 안 하는 것이 맞다
```

`kind='fact'` 추가는 **2~4주 데이터를 보고 재결정**하기로 사용자와 합의했다.

---

## 3. 실측이 방향을 바꾼 것 넷

### ① 빈도 그룹핑에 임베딩이 필요 없다

라이브 사용자 메시지 **2,268건 중 74%가 정규화 후 정확히 중복**이다(고유 1,195 / 2회 이상 603).
`NFKC → casefold → [\s\W_]+ 제거` 만으로 화면이 성립한다.

```bash
# 재현 — 라이브 읽기 전용
cd backend && uv run python -c "
import asyncio,asyncpg,re,pathlib,unicodedata,collections
line=[l for l in pathlib.Path('.env').read_text().splitlines() if 'neon.tech' in l][0]
dsn=re.sub(r'[?&]ssl(mode)?=[^&]*','',line.split('=',1)[1].strip().replace('postgresql+asyncpg://','postgresql://').replace('-pooler',''))
P=re.compile(r'[\s\W_]+')
n=lambda s:P.sub('',unicodedata.normalize('NFKC',s or '').casefold())
async def m():
    c=await asyncpg.connect(dsn,timeout=60)
    t=[r['content'] for r in await c.fetch(\"select content from public.messages where role::text='user'\")]
    k=collections.Counter(n(x) for x in t if (x or '').strip()); d={a:b for a,b in k.items() if b>1}
    print(len(t), len(k), len(d), sum(d.values()))
asyncio.run(m())"
# 기대: 2268 1195 603 1676
```

### ② ⚠ `strict_mode._REFUSAL_RE` 를 자기거절 판정에 재사용하면 안 된다

그건 **관리자가 쓴 FAQ 거절문**("답변 드리기 어렵습니다")을 재는 자다.
봇이 시스템 프롬프트를 따라 내는 문구는 **"확인되지 않습니다"** 라서
`_REFUSAL_RE` 는 2,268건 중 **14건(0.6%)만 잡고 「확인되지 않」 30건을 통째로 놓친다.**

**재사용했다가 로컬 E2E 에서 잡혔다** — 단위테스트는 내가 지어낸 문구를 써서 통과했다.
전용 `_SELF_REFUSAL_RE` 로 라이브 2,268건에 재보정 → **65건(2.9%)**.

`[^.]{0,N}` 로 문장 경계를 막은 것이 핵심이다. `.{0,16}` 이면
"신앙적 **안내**자 역할… 너무 **어렵**게 생각하지 마시고" 같은 격려문이 거절로 잡힌다
(`_REFUSAL_RE` 의 실제 거짓양성이다).

```bash
grep -n "_SELF_REFUSAL_RE" backend/app/services/unanswered.py
cd backend && uv run pytest tests/test_unanswered_layer.py -q -k 거절   # 3 passed
```

### ③ ⚠ 기록이 실패하면 답변이 통째로 날아간다 — `try/except` 로는 못 막는다

DB 오류가 나면 파이썬 예외는 잡히지만 **트랜잭션이 오염된 채로 남아** 호출자의
`commit()` 이 `PendingRollbackError` 로 죽는다. 같은 트랜잭션의 어시스턴트 메시지까지
날아가고 사용자는 500 을 받는다 — 관측을 남기려다 답변을 잃는 정반대 결과다.

로컬 Postgres 로 재현했다(FK 위반 후 커밋 시도):

```
before  기록 실패 → PendingRollbackError → 답변 0건 남음
after   기록 실패 → SAVEPOINT 까지만 되감김 → 답변 1건 · 기록 0건
```

`async with session.begin_nested():` 로 고쳤다(커밋 `bd1893d`). 회귀 테스트 둘 박아 뒀다.
**best-effort 레이어를 새로 붙일 때마다 물린다. 이 파일의 규약으로 삼아라.**

### ④ 관리자 화면의 프리셋 지어냄율이 틀렸다 (아직 안 고침)

```bash
python3 -c "import json;print(json.load(open('exports/wiki_eval/audit_summary.json'))['primary']['rag']['fab_rate'])"
# → 14.2
grep -n "지어냄 8.2%" frontend-admin/src/features/bots/schemas.ts
# → 95
```

**기본값 프리셋(「정확 우선」)이 실제로는 14.2% 지어내는데 화면엔 8.2% 로 뜬다.**
관리자가 봇 설정을 고르는 근거라 그냥 두면 안 된다. 나머지 둘도 낮게 나온다
(`lexical` 2.7 → **3.4**, `both` 11.2 → **11.4**). 45문항 정본 순위는
`C 2.6 < B′ 3.4 < B 4.1 < F 11.4 < A 14.2` (`handoff-evidence-audit-45set-2026-08-10.md:35`).
**3줄이면 고쳐진다. 사용자에게 제안했으나 이번엔 선택되지 않았다.**

---

## 4. 미결 — 기술이 아니라 운영이다

**선행 인계 §4-3 「검수 주체·주기」가 끝내 안 정해졌다.** 그런데 §3 다섯 번째 제약이
*"누가 언제 검수하는지가 안 정해지면 문구를 내면 안 된다"* 고 못 박았고,
우리는 「아직 **정리**되지 않은 내용입니다」를 코드에 박았다.

**지금 이 문구는 지킬 사람이 없는 약속이다.** 되돌리려면 상수 한 줄이다 —
그러라고 상수로 뺐다.

```bash
grep -n "UNANSWERED_MESSAGE" -A 4 backend/app/services/unanswered.py | head -8
# 중립 대안: "규정집에서 확인되지 않는 내용입니다. 담당 교회장님이나 가정행복국(02-3271-0502)으로…"
```

사용자 결정(2026-08-10): 문구 = 「정리」 판 · 2층 = 기록 전용 shadow ·
ops_facts = 분류 4값 + 링크만 · 권한 = 현행 유지 + 보존 90일.

---

## 5. 함정

1. **`app.models.unanswered` 만 import 하면 `NoReferencedTableError`** — FK 대상(`bots`·`chat_sessions`·`messages`·`ops_facts`)이 metadata 에 없어서다. 단독 스크립트는 같이 import 해야 한다(`scripts/purge_unanswered.py` 참조)
2. **`tests/test_retrieval_mode.py:_patch_common()` 이 `chat_service` 모듈 레벨 이름을 몽키패치한다** — 새 헬퍼를 추가하면 거기에도 등록해야 조용히 안 돈다
3. **`test_기본값_봇은_기존_호출을_그대로_한다` 가 `generate_with_rag` 의 kwargs 전체를 비교한다** — 인자를 추가하면 깨진다
4. **shadow 판정이 lexical 턴마다 Gemini 를 1회 더 부른다.** 일일 쿼터 소진 이력이 있다(리셋 KST 16:00). fail-open 이라 답변은 안 막히지만 **본 답변 경로가 쓸 쿼터를 먹을 수 있다** — 라이브 관찰 항목
5. **90일 보존은 `unanswered_questions` 에만 걸린다.** `messages` 는 원문을 무기한 보관하므로 **실질 노출은 안 줄어든다**
6. **`frontend-admin` 은 HTTP 인증이 전혀 없다** — 미들웨어·토큰·라우터 의존성 모두 없음
7. **로컬 docker 와 Neon 은 같은 `bots.id` 에 다른 봇이 있다.** 로컬 봇11 = `opus2_v4`(5,608자) / 라이브 봇11 = D-1 ver2(**1,341자**)

---

## 6. 확인 명령

### ① 라이브 상태 (읽기 전용)

```bash
cd backend && uv run python - <<'PY'
import asyncio, asyncpg, re, pathlib
line=[l for l in pathlib.Path('.env').read_text().splitlines() if 'neon.tech' in l][0]
dsn=line.split('=',1)[1].strip().replace('postgresql+asyncpg://','postgresql://').replace('-pooler','')
dsn=re.sub(r'[?&]ssl(mode)?=[^&]*','',dsn)
async def main():
    c=await asyncpg.connect(dsn,timeout=30)
    print("alembic:", (await c.fetch("select * from public.alembic_version"))[0]['version_num'])
    print("unanswered_questions:", await c.fetchval("select to_regclass('public.unanswered_questions') is not null"))
    print("ops_facts:", await c.fetchval("select count(*) from ops_facts"))
    print("봇11:", dict(await c.fetchrow("select name,retrieval_mode,evidence_policy_mode from bots where id=11")))
    await c.close()
asyncio.run(main())
PY
# 반영 전 기대: 2e7f2e0417ec · False · 0 · D-1 ver2/lexical/legacy
# 반영 후 기대: f4a7b2c9d1e6 · True
```

### ② 배포는 마이그레이션을 자동으로 돌린다

```bash
grep -n "alembic upgrade head" .github/workflows/deploy-backend.yml   # → 있음
grep -n "pytest" .github/workflows/deploy-backend.yml                 # → 없음
```

**순서가 안전하다** — 이미지 빌드 → `alembic upgrade head` → 실패 시 배포 중단 → Cloud Run.
**라이브 DB 를 손으로 건드릴 필요가 없다.** 다만 **테스트는 안 돌리므로** 푸시 전 로컬 검증이 유일한 방어선이다.

### ③ 커밋 전 필수

```bash
cd backend && uv run pytest -q                       # 169 통과
cd frontend-admin && pnpm lint && pnpm build         # 무결
```

**부팅 확인** — 미추적 모듈을 import 하는 사고가 두 번 있었고 2차는 프로덕션 배포 실패였다.
`HEAD` 가 아니라 **스테이징 트리(`git write-tree`)** 를 떠야 지금 커밋하려는 것을 정확히 잰다.
깨끗한 트리에는 venv·.env 가 없으므로 링크를 걸어 준다.

```bash
git add -A
rm -rf /tmp/bootcheck && mkdir -p /tmp/bootcheck
git write-tree | xargs git archive | tar -x -C /tmp/bootcheck
cd /tmp/bootcheck/backend \
  && ln -sf "$OLDPWD/backend/.venv" .venv && ln -sf "$OLDPWD/backend/.env" .env \
  && uv run python -c "import app.main; print('BOOT OK')"
```

---

## 7. 다음 세션이 할 일 — 순서대로

1. **배포.** `feat/clarification-trigger` → main. 마이그레이션은 CI 가 돌린다.
   배포 후 §6-① 로 `unanswered_questions: True` 확인
2. **1~2주 관찰.** 어느 triage 칸에 일이 몰리는지 본다. 「확인되지 않」이 2.9% 니
   대화 100건당 3건쯤 쌓인다. **이 분포가 `kind='fact'` 추가 여부를 정한다**
3. **프리셋 숫자 수정** (§3-④). 3줄
4. **검수 주체·주기 합의** (§4). 안 정해지면 문구를 중립으로 되돌린다
5. 그 다음이 재질문 배선이다 — 라벨 재료가 3층 로그에서 나오기 시작한 뒤
