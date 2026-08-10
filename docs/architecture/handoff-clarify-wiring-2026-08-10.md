# 인계 — 되묻기 배선: 규칙을 먼저 써야 한다 (2026-08-10)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 다르면 **그 사이에 코드가 바뀐 것이다. 문서가 아니라 코드가 맞다.**
>
> 짝 프롬프트: `next-session-clarify-wiring-prompt-2026-08-10.md`
> 선행: `handoff-clarification-trigger-2026-08-11.md` (판정기 설계·측정) ·
> `handoff-unanswerable-built-2026-08-10.md` (오늘의 측정 전반)

---

## 0. 가장 먼저 알아야 할 것 — 지금 배선하면 나빠진다

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

**규칙이 있는 봇이 0개다.** `decide()` 는 규칙 매칭에 실패하면 `handoff` 를 낸다 —
「담당 교회장 또는 가정행복국으로 문의하세요」다.

즉 **지금 배선하면 되묻는 게 아니라, 답을 주던 봇이 사람에게 넘기기 시작한다.**
이건 개선이 아니라 후퇴다.

---

## 1. 왜 하려는가 — 실측 근거

라이브 프롬프트(1,341자) + 라이브 코퍼스로 잰 결과:

| 질문 유형 | 예 | 되물음 |
|---|---|---|
| **극단 모호** — 주제 자체가 없음 | "언제 해야 하나요?" | **2/3** ✔ |
| **실전 모호** — 주제는 있고 케이스가 갈림 | "축복정리 과정은 어떻게 되나요?" | **0/5** ✘ |
| **코퍼스 결손** — 되물어도 안 나옴 | "B4U 등록은?" | 0/2 (맞는 동작) |

프롬프트 3번 항목이 *"불명확할 때 되물어 확인합니다"* 라고 시키는데, **실전 케이스에서는
한 번도 안 한다.** "축복정리 과정"은 본인 세대(1세/축복자녀)에 따라 답이 갈리는데
되묻지 않고 한쪽을 골라 700자를 쓴다.

**그리고 재현이 안 된다.** 같은 질문 2회에 1,018자 → 755자, 분류도 바뀌었다.
되묻기가 코드가 아니라 프롬프트에 맡겨져 있어서다.

### 업계 조사가 같은 방향을 가리킨다 (2026-08-10)

| 논문 | 핵심 |
|---|---|
| **Ask or Assume?** (arXiv 2603.26233) | 모호성 **판정을 실행에서 분리한** 멀티에이전트가 69.40% 해결률. 쉬운 과제엔 안 묻고 어려운 것만 묻는 **보정된** 행동을 보인다 |
| **HopRefusalBench** (arXiv 2608.01358) | 최고 모델도 올바른 정지율 42.9%. **거절 응답의 84.7~98.4%는 이유를 정확히 안다** — 병목은 이유가 아니라 「답 안 함」으로 **커밋**하는 것. underspecified 질문에서 가장 낮다 |

우리 실측이 둘 다 재현했다. 그래서 **판정을 분리하고 코드가 커밋시킨다**가 설계 방향이다.

---

## 2. 이미 있는 것 — 새로 만들지 마라

`backend/app/services/clarification_trigger.py` (**호출자 0개**)

```bash
grep -rn "clarification_trigger" backend/app --include=*.py | grep -v "services/clarification_trigger"
# → chat_service.py 한 곳뿐이고, 그건 3층 shadow 판정(기록 전용)이다
```

| 함수 | 하는 일 |
|---|---|
| `judge_answerability()` | 주입 원문을 읽고 `needs_user_input`/`missing`/`evidence` 판정. evidence 를 주입 목록과 대조. **3중 fail-open** |
| `match_policy_rule()` | 관리자 예시질문을 레포 BM25 로 매칭. **LLM 0회.** 1위가 2위를 1.5배 못 이기면 안 고른다 |
| `_policy_questions()` | 규칙의 `required_slots` 를 그대로 카드로. **문구를 LLM 이 짓지 않는다** |
| `decide()` | B(판정) → A(문구). 규칙 없으면 `handoff` |

**v3 기준 45문항 중 6건(13%) 발동.** v1(「원문이 이 사안을 결정하는가」축)은 35건(78%)이라 못 쓴다 —
**축을 바꾸지 마라.**

---

## 3. 이 세션이 할 일 — 순서가 전부다

### ① 규칙을 다시 쓴다 ← **사람 판단이 필요하다. 혼자 하지 마라**

시드 규칙 4개가 `docs/architecture/clarification-policy-seed-2026-08-11.json` 에 있는데
**겨냥한 문항이 오늘 실패한 것과 하나도 안 겹친다.**

```
시드가 겨냥      22 · 11 / 31 · 32 / 16 / 17
오늘 실패        33 · 34 · 36 · 45 · 18      ← 겹치는 것 0
```

선행 인계가 스스로 적어 뒀다 — *"시드 규칙은 틀린 표적(12건)을 보고 썼다. 라벨을 고친 뒤
다시 써야 한다."* 오늘 실측이 그것을 확인했다.

**오늘 실패한 5건과 갈리는 슬롯**(판정기가 짚은 것, 사람이 검증할 것):

| n | 질문 | 판정기가 짚은 결손 |
|---|---|---|
| 33 | 2세 가정 12일 가정출발의식 절차가 뭐야? | 축복 유형(축복자녀 간 / 축복자녀-1세) |
| 34 | 2세도 가정출발 하기전에 해야되는 의식이 있어? | 축복 상대방 유형 |
| 36 | 축복정리 과정은 어떻게 되나요? | 본인 세대(1세/축복자녀) |
| 45 | B4U 등업 기준이 뭐야? | 회원등급 또는 세대 구분 |
| 18 | 축복자녀이고 1세 식구와 교제 중… 2세-1세 축복 가능? | 가정 편성 유형 |

**이 슬롯이 맞는지는 규정 지식이다.** 사용자에게 물어서 확정하라.

규칙 한 건의 모양(시드에서):

```json
{
  "id": "blessing-type-generation",
  "name": "축복 종류·세대 확인",
  "enabled": true,
  "priority": 30,
  "request_examples": ["2세가 기성축복을 받을 수 있나요", "..."],
  "why_ask": "축복 종류와 당사자 세대에 따라 적용 조문이 갈린다…",
  "required_slots": [
    {"id": "blessing_type", "label": "축복 종류",
     "question": "어떤 축복에 대한 질문인가요?",
     "selection_mode": "single",
     "options": [{"id":"second_gen","label":"2세 축복"}, …]}
  ]
}
```

스키마: `backend/app/schemas/clarification_policy.py`

> **`request_examples` 가 매칭의 전부다.** BM25 가 「질문 대 관리자 예시질문」을 비교한다.
> 예시가 실제 질문과 같은 어휘를 안 쓰면 규칙이 안 걸린다.

### ② 규칙을 DB 에 넣고 관리자 화면에서 확인한다

`봇 → 답변 설정 → 추가 확인 질문 정책` 에 「테스트하기」가 있다.
**배선 전에 여기서 먼저 돌려 본다** — 규칙이 실제로 걸리는지 LLM 없이 확인된다.

### ③ 그 다음이 배선이다

삽입점: `backend/app/services/chat_service.py` 의 어휘 분기.
`_retrieve_and_generate` 가 이미 `RetrievalTrace`(주입 원문 포함)를 돌려주므로
판정기에 넘길 원문이 손에 있다.

### ④ 측정

- 발동률(전체 대비 ask/handoff/answer)
- **되물은 뒤 답변 품질** — 선행 인계 §6-③ 이 여기서 실패했다. 선택지를 **전수로** 만들면
  질문자의 실제 상황이 아닌 조합이 섞여 측정이 흐려진다. **질문에 이미 적힌 정보로 분기를
  정하고 그 분기만 재답변**하라

---

## 4. 제약

- **판정 축을 바꾸지 마라.** `needs_user_input`(질문자만 아는 것이 빠졌나)이지
  `answerable`(답할 수 있나)이 아니다. 후자는 45문항 중 35건(78%) 발동해서 못 쓴다
- **되물을 문구를 LLM 이 짓게 하지 마라.** 관리자가 쓴 슬롯 문구를 그대로 꺼낸다
- **규칙이 없으면 `handoff` 다.** §0 을 다시 읽어라 — 규칙 없이 켜면 후퇴다
- **되묻기는 한 번까지.** 프롬프트 3번 항목이 이미 그렇게 정해 뒀다
- **배선하면 전 응답이 비스트리밍이 된다** — `lexical` 은 원래 `stream_ok` 가 거짓이라
  봇 11에는 변화가 없지만, `file_search` 봇에 켜면 체감이 바뀐다
- **turn 당 Gemini 1회가 늘어난다.** 일일 쿼터 소진 이력이 있다(리셋 KST 16:00)
- **라이브 DB 는 읽기만.** 로컬 검증용 복제봇이 **봇 29**로 있다(D-1 ver2 · 1,341자 · lexical)
- **프론트가 선택지를 안 읽는다.** `ChatProvider.tsx` 는 완성 응답에서 `content` 와 `followups`
  둘만 읽는다. `source="ask"` 를 넣어도 화면엔 아무것도 안 뜬다 —
  `ClarificationPrototype.tsx:382` 의 ask/ready/handoff 렌더를 `ChatArea` 로 올려야 한다.
  **이게 실제 비용의 큰 몫이다**

---

## 5. 함정

1. **모델은 항목이 하나면 배열 대신 문자열을 준다**(`evidence: "reg-90"`). 45건 중 31건이
   이걸로 죽었다. `clarification_trigger.py:99-112` 의 `field_validator(mode="before")` 가 막고 있다
2. **`both` 는 삽입점이 없다.** `build_hybrid_turns` 가 `Retrieved` 를 함수 안에서 버린다
3. **0라운드 근거 재사용은 아직 안 된다.** `/answer` 요청에 `bot_id` 와 `message` 밖에 없어
   라운드0 인용이 서버로 안 돌아온다. 요청 스키마 + 클라이언트 변경이 필요하다
4. **`_run.py` 를 `--retry-failed` 없이 돌리면** `answers.json` 이 `audit.json` 과 어긋난다

---

## 6. 확인

```bash
cd backend && uv run pytest -q                                  # 169 통과
cd backend && uv run pytest tests/test_clarification_trigger.py -q   # 14 통과
grep -rn "clarify_enabled" backend/app/api backend/app/services
# → clarification_preview.py 두 줄뿐 (chat_service 는 안 읽는다)
```

---

## 7. 이 순서를 지켜야 하는 이유

`handoff-strict-gate-repair-2026-08-10.md`(strict 게이트)를 **먼저** 하는 것이 맞다.
게이트는 사용자에게 안 보여서 문제가 나면 조용히 되돌릴 수 있다.
되묻기는 봇이 답 대신 질문을 하기 시작하므로 바로 보인다.

**둘을 같은 배포에 넣지 마라.** CI 가 테스트를 안 돌리고 main push 가 곧 배포라,
문제가 났을 때 어느 쪽 때문인지 못 가른다.
