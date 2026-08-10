# 인계 — 되묻기 배선 완료 (2026-08-10)

> **검증된 사실 목록이다. 믿지 말고 확인 명령을 다시 돌려라.**
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 값이 다르면 그 사이에 코드가 바뀐 것이다. **문서가 아니라 코드가 맞다.**
>
> 선행: `handoff-clarify-wiring-2026-08-10.md` (배선 전 상태·판정기 설계)
> 브랜치: `feat/clarification-wiring` (main 46156f6 에서 분기)

---

## 0. 라이브는 아직 안 바뀌었다

```bash
cd backend && uv run python - <<'PY'
import asyncio, asyncpg, re, pathlib, json
line=[l for l in pathlib.Path('.env').read_text().splitlines() if 'neon.tech' in l][0]
dsn=re.sub(r'[?&]ssl(mode)?=[^&]*','',line.split('=',1)[1].strip().replace('postgresql+asyncpg://','postgresql://').replace('-pooler',''))
async def main():
    c=await asyncpg.connect(dsn,timeout=30)
    rows=await c.fetch("select id,clarify_enabled,clarification_policy from bots")
    pol=lambda r: json.loads(r['clarification_policy']) if isinstance(r['clarification_policy'],str) else (r['clarification_policy'] or {})
    print("봇", len(rows), "· clarify_enabled=true", sum(1 for r in rows if r['clarify_enabled']),
          "· 규칙 보유 봇", sum(1 for r in rows if pol(r).get('rules')))
    await c.close()
asyncio.run(main())
PY
# 기대: 봇 11 · clarify_enabled=true 0 · 규칙 보유 봇 0
```

`clarify_enabled` 가 거짓이면 `_clarification_for` 가 판정기를 **호출조차 하지 않는다**
(`chat_service.py` `_clarification_for` 첫 줄). 라이브 응답 경로는 배선 전과 같다.

**라이브에 켜기 전 선행 조건 2가지**
1. `messages.clarification` 마이그레이션(`a1c7d3e9f204`)이 라이브에 올라가야 한다 —
   없으면 되물은 턴을 저장하다 죽는다
2. 규칙을 라이브 봇 11에 넣어야 한다. 관리자 API 로는 **안 된다**(§3-2)

---

## 1. 무엇을 만들었나

| 층 | 파일 | 한 일 |
|---|---|---|
| 규칙 | `docs/architecture/clarification-policy-v2-2026-08-10.json` | 규칙 4개. 시드 4개를 대체 |
| 판정 | `backend/app/services/clarification_trigger.py` | **안 건드렸다.** 45문항으로 보정된 것이다 |
| 배선 | `backend/app/services/chat_service.py` | `_clarification_for` + 비스트리밍 분기 삽입 |
| 계약 | `backend/app/schemas/clarification.py` `chat.py` | `ChatClarification`, 응답·요청 필드 |
| 영속 | `backend/app/models/chat.py`, alembic `a1c7d3e9f204` | `messages.clarification` JSON 컬럼 |
| 화면 | `frontend-client/src/components/chat/ClarificationCard.tsx` | 선택지 카드(프레젠테이션 전용) |
| 화면 | `ChatArea.tsx` `ChatProvider.tsx` `types/api.ts` | 카드 렌더 + 응답 파싱 + 재질의 |
| 적재 | `scripts/load_clarification_policy.py` | 로컬 DB 직접 UPDATE (관리자 API 우회) |

커밋: `8b266ab`(백엔드) · `b028122`(프론트)

### 규칙 4개와 표적

| 규칙 id | 표적 | 슬롯 | 규정 근거 |
|---|---|---|---|
| `family-start-12day` | #33 | 축복 유형 | 제43조 · 행정125 · 행정016 |
| `family-start-pre-rite` | #34 | 축복 상대방 유형 | 행정004 · 행정016 · 제31조 |
| `child-first-gen-eligibility` | #18 | 연령 + 상대확정 경로 | 제39조 ①②④ |
| `b4u-tier` | #45 | 회원등급 + 대상 구분 | 제26조 표 · 제25조 ④⑤ |

**#36·#39 는 규칙을 만들지 않았다 — `handoff` 가 맞다.** 사용자 확정: 축복정리는
슬롯형이 아니라 상담 사안이다. 판정기가 #36 에 짚은 「본인 세대」는 주입 원문이
뒷받침하지 않는다(reg-63·64 는 세대가 아니라 정리/무효화·1년 경과·합의 여부로 갈린다).

**#45 슬롯은 사용자 확인을 못 받았다.** 질문 4개 상한에 걸려 규정 근거로만 정했다.

---

## 2. 배선의 순서 — 바꾸지 마라

`chat_service.py` 비스트리밍 분기:

```
_strict_blocks 치환
  ↓
★ _clarification_for  ← 여기여야 한다
  ↓
1층 빈답변 게이트 → 표기 통일 → create_message → 3층 기록
```

되묻기 본문은 인용 0건이고 거절문도 아니다. strict 게이트 **앞**에 놓으면
`_strict_blocks` 가 참이 되어 `STRICT_EVIDENCE_MESSAGE` 로 통째로 치환된다 —
봇이 되물은 질문이 삼켜진다. 지금은 라이브 11봇이 전부 `legacy` 라 안 터지지만
strict 를 켜는 순간 터진다.

```bash
cd backend && uv run pytest tests/test_chat_clarification_wiring.py::test_clarification_must_come_after_the_strict_gate -q
```

되물은 턴에는 shadow 판정과 인용 백필을 둘 다 건너뛴다 — 같은 판정을 두 번 돌리면
Gemini 가 turn 당 2회가 되고, 본문이 질문이라 채울 근거도 없다.

---

## 3. 함정 — 이번에 새로 확인한 것

### 3-1. 관리자 「추가 확인 질문 정책 → 테스트하기」는 배선 경로가 아니다

선행 인계 §3② 의 「LLM 없이 확인된다」는 **틀렸다.**

```bash
grep -n "live_decision" backend/app/api/v1/endpoints/admin/bots.py    # :139
grep -n "generate_structured_with_rag" backend/app/services/clarification_service.py  # _generate_plan
```

`admin/bots.py:139` → `live_decision(round=0)` → `_generate_plan` →
`rag_service.generate_structured_with_rag` = **File Search LLM 호출**이고, 규칙 선택도
LLM 이 낸 `raw_plan.policy_match` 로 한다(`clarification_service.py:785`).
배선이 쓰는 `match_policy_rule`(BM25)와 **다른 경로다.**

규칙 검증은 커밋된 테스트로 한다:
```bash
cd backend && uv run pytest tests/test_clarification_policy_v2.py -q   # 7 통과
```

### 3-2. 관리자 API 로는 규칙을 저장할 수 없다

`validate_active_policy`(`backend/app/schemas/clarification_policy.py:93-97`)가 활성 규칙마다
`document_refs` 를 요구하고, 그 `document_id` 가 봇의 **File Search 스토어**에 있어야 한다.
대상 봇은 `retrieval_mode='lexical'` 이라 스토어가 없다. 어휘 경로의 `decide()` 는
`document_refs` 를 읽지 않는다.

```bash
cd backend && uv run python ../scripts/load_clarification_policy.py --bot-id 29
# 봇 29(테스트 봇 D-1 ver2 · lexical) clarify_enabled=True 규칙 4개: ...
```

라이브에 넣으려면 같은 판단이 필요하다 — 스키마를 풀든지, DB 로 직접 넣든지.

### 3-3. `exports/` 는 gitignore 지만 하네스 `.py` 는 추적 중이다

```bash
grep -n exports .gitignore          # /exports
git ls-files exports/ | head        # 그런데 _run.py·_audit.py 는 추적된다(강제 추가)
```

**코드는 커밋되고 데이터(`results.json`·`answers.json`·`audit.json`)는 안 된다.**
그래서 측정 산출물은 이 기계에만 있다 — 다른 기계에서는 §4 의 명령을 다시 돌려야 한다.

### 3-4. `results.json` 이 남아 있으면 `--retry-failed` 가 전부 건너뛴다

`--retry-failed` 는 `status` 가 있는 키를 건너뛴다. 옛 측정의 `results.json` 은 45키를 전부
갖고 있어 새 정책으로 다시 재려면 **파일을 치워야 한다.** 옛 결과는
`results_v3_seedpolicy.json` 으로 보존해 뒀다.

`answers.json` 에도 같은 일이 났다. 시드 정책은 #33 에 분기를 4개 만들었고 v2 는 1개만
만드는데, `stage_reanswer` 가 자기가 만든 키만 덮어써서 `33b1~33b3` 이 살아남아
**감사에 섞였다**(지어냄 5건 중 1건이 그것이었다). 하네스에 옛 분기 제거를 넣었다.

### 3-5. Gemini SDK 호출에 클라이언트 타임아웃이 없다

2026-08-10 측정에서 한 문항이 매달려 12분간 진행이 멈췄다(n=13 이후 무응답, 네트워크는 정상).
하네스에 `JUDGE_TIMEOUT_SEC = 90` 을 넣어 `asyncio.wait_for` 로 감쌌다.
**프로덕션 경로(`judge_answerability`)에는 타임아웃이 없다** — 되묻기를 라이브에 켜기 전에
이걸 봐야 한다.

### 3-6. `min_score=15` 는 n=6 스윕이다

`chat_service.CLARIFICATION_MIN_SCORE` 와 `_run.py` 의 `MIN_SCORE` 가 **같아야 한다.**
다르면 측정과 실물이 다른 규칙을 고른다.

---

## 4. 실측

측정 봇: 로컬 29(D-1 ver2 복제 · 1,341자 · `lexical` · 위키 138쪽). 45문항.

### 4-1. 발동률 — 표적 6/6

```
                 시드 정책(03:21)   v2 정책(18:51)
  ask                 2                 4
  handoff             4                 3
  answer             39                38
```

| n | 질문 | 상태 | 적용 규칙 | 시드일 때 |
|---|---|---|---|---|
| 33 | 2세 가정 12일 가정출발의식 절차가 뭐야? | ask | `family-start-12day` | ask / `family-start-stage` ✘ |
| 34 | 2세도 가정출발 하기전에 해야되는 의식이 있어? | ask | `family-start-pre-rite` | ask / `eligibility-age` ✘ |
| 18 | 축복자녀이고 1세 식구와 교제 중… | ask | `child-first-gen-eligibility` | handoff |
| 45 | B4U 등업 기준이 뭐야? | ask | `b4u-tier` | handoff |
| 36 | 축복정리 과정은 어떻게 되나요? | handoff | (없음 — 의도) | handoff |
| 39 | 축복 받고 1년도 안되었는데 상대가 성화… | handoff | (없음 — 의도) | handoff |

**시드 정책은 #33·#34 를 걸긴 했지만 엉뚱한 것을 물었다** — #33 은 「축복 유형」이 없는데
「지금 어디까지 진행되셨나요」를, #34 는 「상대방 유형」이 없는데 「만 나이」를 물었다.
규칙 없음(handoff)보다 나쁜 상태였다.

```bash
cd backend && uv run python -u ../exports/clarify_eval/_run.py --stage judge
# 판정 완료 45/45 — ask 4 · handoff 3 · answer 38
```

### 4-2. 판정기 자체가 실행마다 흔들린다 ← **새로 확인**

판정 verdict 는 정책과 무관한데(정책은 규칙 매칭에만 쓴다), 두 실행의 양성 집합이 다르다:

```
03:21  18 · 33 · 34 · 36 · 39 · 45            (6건)
18:51  18 · 20 · 33 · 34 · 36 · 39 · 45       (7건)   ← #20 이 answer → handoff
(중단된 18:36 실행)  #12 가 answer → handoff
```

#20 「2세가 1세와 은사축복식을 참석하고 이후에 아이를 갖았고 출산했습니다. 태어난 아이는
2세가 되나요?」의 결손은 「축복 편성 유형(1세가정/축복자녀가정)」이다 — **슬롯형이 맞고
제4조·제40조가 정확히 그것으로 갈린다.** 규칙이 없어 handoff 로 간다.

두 가지 함의:
- **`min_score=15` 를 n=6 으로 스윕한 근거가 더 얇아졌다.** 양성 집합이 실행마다 바뀐다
- **답을 주던 질문이 handoff 로 내려가는 일이 실제로 일어난다**(#20·#12). 선행 인계 §0 이
  경고한 후퇴가 규칙 4개로 다 막히지는 않았다. 5번째 규칙(편성 유형) 후보가 #20 이다

### 4-3. 되물은 뒤 재답변

```bash
cd backend && uv run python -u ../exports/clarify_eval/_run.py --stage reanswer
# 재답변 완료 — 기준선 4 · 분기 22
```

분기는 전수 조합이 아니다(§5). 문항별: #33 1개(고정) · #34 5개 · #18 7개 · #45 6개 = 19.

### 4-4. 지어냄율 — **차이를 말할 수 없다**

```bash
cd backend && AUDIT_DIR=$PWD/../exports/clarify_eval AUDIT_ARMS=baseline,clarify \
  uv run python -u ../exports/wiki_eval/_audit.py --stage all
# ⚠ 요약 출력은 KeyError 로 죽는다 — ARM_LABEL 에 baseline/clarify 가 없다.
#    데이터는 audit.json 에 다 남는다. summarize() 를 직접 불러 집계했다(audit_summary.json).
```

| 팔 | 셀 | 무주장 | 주장 | 지어냄 | 지어냄율 | 셀당 |
|---|---|---|---|---|---|---|
| baseline (되묻기 전 냉동본) | 4 | 1 | 24 | 0 | 0.0% | 0.0 |
| clarify — 선택지 정정 전 | 19 | 4 | 141 | 4 | 2.8% | 0.21 |
| **clarify — 정정 후** | **18** | **3** | **137** | **1** | **0.7%** | **0.06** |

「기성·독신」선택지를 쪼개고 「독신 축복」을 `unresolved` 로 표시하자 **지어냄 4건 → 1건**
(§4-5). 남은 1건은 선택지 문제가 아니다:

```
34b0(축복자녀 간 축복)  "축복자녀 가정은 축복식에 앞서 성주식에 참여한다."
  → 제31조 ④ 는 「기원절 입적 축복식이 해당 축복식과 함께 진행되는 경우」로 한정한다.
     조건을 떼고 일반화했다 — 흔한 RAG 정밀도 문제고 되묻기와 무관하다.
```

**이 표로 「되묻기가 품질을 바꿨다」고 말하면 안 된다.** baseline 이 24주장뿐이라
0/24 의 상한은 대략 12%다(rule of three). clarify 의 0.7% 는 그 안에 들어간다.
말할 수 있는 것은 **되물은 뒤 답변이 평소보다 더 지어내지는 않는다**는 것뿐이다
(선행 측정의 어휘팔 45문항 지어냄율 2.7% 와 같은 자릿수이거나 그 아래).

### 4-5. 지어냄 4건이 전부 한 셀에 몰렸다 → **고쳤다**

전부 `34b3` = `family-start-pre-rite` 의 선택지 **「기성·독신 축복」** 이었다.

```
기성·독신 가정은 가정출발을 위해 탕감봉을 거친다.
  → 탕감봉은 기성가정·1세가정에는 있으나 독신 가정에는 직접 적용되지 않는다
기성·독신 가정은 가정출발을 위해 40일 성별을 거친다.
  → 40일 성별은 1세가정·기성가정에 명시, 독신 가정까지 뒷받침 안 됨
기성·독신 가정은 가정출발을 위해 가정출발교육을 거친다.
기성·독신 가정은 성주식·축복식·탕감봉·40일 성별·가정출발교육을 거쳐 3일행사를 진행한다.
  → 전체 절차는 미혼 1세 편성 가정·기성축복 가정에 한정. 독신까지 일반화 불가
```

**원인은 선택지를 「기성」과 「독신」으로 묶은 것이다.** 코퍼스는 기성축복가정을 다루지만
독신 가정의 가정출발은 다루지 않아, 묶은 라벨을 고르면 봇이 없는 쪽까지 일반화한다.

**고친 방법 — 지우지 않고 표시한다.** (사용자 결정)
지우면 공백이 화면에서 숨고, 독신 질문자는 직접 입력으로 넘어가 같은 지어냄을 다시 만난다.

```
ClarificationPolicyOption.unresolved: bool     규정집이 아직 다루지 않는 갈래 표시
ClarificationQuestion.unresolved_options       그 라벨 목록을 화면에 전달
ClarificationCard                              고르면 재질의를 보내지 않고 고정 문구를 띄운다
```

문구: 「〈독신 축복〉에 대한 기준은 아직 규정집에 정리되지 않았습니다. 정리되는 대로
업데이트할 예정이며, 급하시면 담당 교회장님이나 가정행복국(02-3271-0502)으로 문의해 주세요.」

선택지는 5개가 상한이라(`validate_active_policy`) 「잘 모르겠어요」를 빼고
「기성 축복」/「독신 축복(정리 중)」으로 쪼갰다. 두 규칙에 같은 라벨이 있어 둘 다 고쳤다.

하네스도 같은 규칙을 따른다 — `_branches` 가 저장된 스냅샷이 아니라 **현행 정책**을 읽고
`unresolved` 갈래를 만들지 않는다. 측정이 프로덕션에 없는 경로를 만들면 안 된다.

```bash
cd backend && uv run pytest tests/test_clarification_policy_v2.py -q   # 9 통과
# test_unresolved_options_are_marked_not_deleted 가 「기성·독신 축복」 라벨의 부활을 막는다
```

**어휘 카운트로는 이 공백을 못 찾는다.** 「기성」 37건 · 「독신 축복」 17건으로 멀쩡히 뜬다.
없는 것은 라벨이 아니라 **독신 가정의 가정출발 절차**다. 실제로 가른 것은 재답변 셀을
codex 로 감사한 결과뿐이다 — 새 규칙·선택지를 추가하면 같은 감사를 다시 돌려라.

### 4-6. 브라우저 E2E 는 못 돌렸다

실제 채팅 경로(`/chat/*`)는 로그인 세션 쿠키를 요구하고, 인증 우회는 프로토타입 경로
(`/chat/new/{id}?clarify-prototype=1`)에만 걸려 있다(`frontend-client/src/middleware.ts:20-26`).
자격증명이 없어 못 돌렸다.

대신 확인한 것:
- **백엔드 계약 실증** — 로컬 봇 29 에 `process_chat_request` 를 직접 태워
  `source=clarification_ask` · `rule_id=family-start-12day` · 슬롯 문구가 관리자가 쓴 그대로 ·
  `messages.clarification` 영속화 True. 재질의(`clarification_round=1`)는 판정을 건너뛰고
  `source=rag` · 인용 4건. 비표적(#20 계열)은 무영향
- **프론트** — `npx tsc --noEmit` 통과, `npm run build` 통과

**남은 것: 브라우저에서 카드가 뜨고, 눌러서 재답변이 오고, 새로고침 후에도 남는지.**

---

## 5. `_run.py` 에서 바꾼 것

```
BOT_ID            11 → 29     로컬 11 은 opus2_v4(5,608자)라 라이브 프롬프트가 아니다
POLICY            시드 → clarification-policy-v2-2026-08-10.json
MIN_SCORE         신규 15.0   chat_service.CLARIFICATION_MIN_SCORE 와 같아야 한다
JUDGE_TIMEOUT_SEC 신규 90     §3-5
MAX_BRANCHES      4 → 8       전수 조합을 버려서 폭발하지 않는다
_branches()       전수 조합 → 고정(PINNED) + 한 번에 한 슬롯씩
옛 분기 제거       신규        이번 실행이 만들 분기보다 옛 것이 많으면 잔재가 남는다(§3-4)
itertools import  제거        전수 조합을 안 써서
```

`_branches` 가 전수 조합을 버린 이유: 「만 25세 미만 + 공적 소개」처럼 실재하지 않는
사람이 섞여 측정이 흐려진다(선행 인계 §6-③ 이 여기서 실패했다). 미정 슬롯은
「잘 모르겠어요」로 두는데, 그건 지어낸 값이 아니라 관리자가 넣어 둔 실제 선택지다.

---

## 6. 확인

```bash
cd backend && uv run pytest -q                                        # 188 통과
cd backend && uv run pytest tests/test_clarification_policy_v2.py -q  # 7 통과 (규칙 6/6 적중)
cd backend && uv run pytest tests/test_chat_clarification_wiring.py -q # 6 통과
cd frontend-client && npx tsc --noEmit && npm run build               # 통과

# 커밋된 트리가 실제로 뜨는가
git add -A && TREE=$(git write-tree) && rm -rf /tmp/bootcheck && mkdir -p /tmp/bootcheck \
  && git archive "$TREE" | tar -x -C /tmp/bootcheck \
  && cp backend/.env /tmp/bootcheck/backend/ \
  && (cd /tmp/bootcheck/backend && PYTHONPATH=$PWD ../../..//Users/woosung/project/agy-project/nexus-core/backend/.venv/bin/python -c "import app.main; print('BOOT OK')")
```

---

## 7. 다음 — 순서대로

1. **브라우저 E2E 1회**(§4-6). 카드가 뜨는지·눌리는지·「정리 중」 문구가 나오는지·
   새로고침 후 남는지. 이 세션에서 유일하게 못 확인한 것이다
2. **#45 슬롯을 사용자에게 확인받아라.** 질문 4개 상한에 걸려 규정 근거로만 정했다
3. **`min_score` 재스윕.** n=6 이고 그 6건조차 실행마다 바뀐다(§4-2)
4. **`judge_answerability` 에 타임아웃**(§3-5). 라이브 선행 조건이다
5. **다른 슬롯에도 `unresolved` 가 필요한지 보라.** 지금 표시된 건 「독신 축복」 하나뿐이고,
   그건 감사가 실제로 잡은 것만 고친 결과다(사용자 결정). 새 규칙을 넣을 때마다 재감사

라이브 반영은 §0 의 선행 조건 2가지를 먼저 채우고, strict 게이트(PR #59)와
**같은 배포에 넣지 마라.** CI 가 테스트를 안 돌리고 main push 가 곧 배포라,
문제가 났을 때 어느 쪽 때문인지 못 가른다.

`#20`(태어난 아이는 2세가 되나요 — 결손: 축복 편성 유형)은 5번째 규칙 후보다.
제4조·제40조가 정확히 편성 유형으로 갈린다. 지금은 규칙이 없어 handoff 로 간다.
