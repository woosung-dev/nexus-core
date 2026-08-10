# 인계 — strict 게이트를 실제로 작동시키기 (2026-08-10)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 다르면 **그 사이에 코드가 바뀐 것이다. 문서가 아니라 코드가 맞다.**
>
> 짝 프롬프트: `next-session-strict-gate-prompt-2026-08-10.md`
> 선행: `handoff-unanswerable-built-2026-08-10.md` (오늘의 측정 전반)

---

## 0. 한 줄

**strict 모드는 어휘 경로에서 아무것도 막지 못한다.** 화면은 「직접 인용을 남기지 못하면
답변을 차단합니다」라고 쓰는데, 실측하면 게이트가 보는 값이 **항상 참**이다.

이 문서는 그것을 **문구로 덮지 말고 실제로 작동하게** 만드는 길을 담는다.
길은 실측으로 하나 뚫려 있고, 값은 싸다(LLM 추가 호출 0회 · 지연 0).

---

## 1. 왜 안 걸리나 — 뿌리는 「인용을 우리가 만든다」

```bash
grep -n "approximate=False" backend/app/services/wiki/service.py   # → 127
grep -n "def has_direct_citation" -A 6 backend/app/services/strict_mode.py
```

`_citations()` 가 **주입한 원문 유닛마다** `approximate=False` 인용을 만든다.
모델이 그 원문을 실제로 썼는지와 **무관하다.** 그래서 `has_direct_citation()` 이 항상 참이 된다.

### 실측

```
어휘 경로 답변       → 인용 4건 · approximate = {False} · has_direct_citation = True
코퍼스 밖 질문       → 인용 0건 ·                          has_direct_citation = False
                                                            (그런데 답변도 0자)
```

**유일하게 걸리는 경우가 검색 빈손일 때인데, 그때는 답변 자체가 0자라
1층(`unanswered.UNANSWERED_MESSAGE`)이 이미 고정 문구로 바꾼다.**
즉 strict 를 켜도 보호가 하나도 늘지 않는다.

라이브 현황: **봇 11개 전부 `evidence_policy_mode='legacy'`** — strict 를 쓰는 봇이 0개다.

---

## 2. 뚫린 길 — 인용 마커의 id 를 주입 목록과 대조한다

모델은 답변에 자기가 쓴 근거 id 를 표기한다. **두 형식이 관측됐다.**

```
[[src: reg-3, glo-132]]     원문·위키 블록의 [src_id] 표기를 따라간 것
[근거: reg-25 ⑤]            프롬프트 [출력 형식] 항목을 따라간 것
```

### 실측 ① — id 는 신뢰할 수 있다

6문항 × 2회. **프롬프트 밖 id 0개 · 코퍼스 밖 id 0개.**
모델이 근거 id 를 지어내지 않는다.

> ⚠ **첫 측정에서 「지어냄 2건」이 나왔는데 거짓양성이었다.** 주입 목록을 `_select_units()`
> 결과(원문 유닛)만으로 잡았기 때문이다. **위키 페이지 블록(`_wiki_block`)에도 src id 가 실린다.**
> 대조 대상은 `_context_block(units) + _wiki_block(retrieved)` **둘 다**여야 한다.

### 실측 ② — 마커 출현율은 프롬프트가 정한다

```
현행 프롬프트 (“규정 근거를 밝힐 수 있으면 함께 언급합니다”)
  → 마커 있는 답변 17% ~ 50%   ← 회차마다 흔들린다

인용 강제 문구 추가
  → 마커 있는 답변 83% (5/6)   ← 프롬프트 밖 id 0 · 코퍼스 밖 id 0
```

강제에 쓴 문구:

```
[인용 표기 — 반드시 지킬 것]
사실을 서술하는 문장은 **모두** 문장 끝에 근거를 [[src: id]] 형식으로 붙인다.
id 는 제공된 원문에 실제로 있는 것만 쓴다. 없으면 그 문장을 쓰지 않는다.
```

**게이트를 「마커 id 가 주입 목록 안에 있나」로 바꾸면 문자열 비교만으로 성립한다.**
LLM 추가 호출 0회, 지연 0, 결정론. `clarification_trigger._validate_verdict` 가 쓰는 것과 같은 발상이다.

---

## 3. 이 세션이 먼저 할 일 — 측정이 설계보다 앞이다

**n=6 은 근거로 쓰기에 작다. 구현 전에 이것부터 재라.**

1. **20문항 이상으로 다시 잰다.** 현행 프롬프트 vs 인용 강제, 각각
   `마커 출현율` · `프롬프트 밖 id 수` · `코퍼스 밖 id 수`
2. **마커가 없는 답변을 읽는다.** 사실 주장이 없는 답변(인사·안내·거절)이면 차단해도 되고,
   사실을 말하면서 마커만 빠진 것이면 **과잉 거절**이다. 이 비율이 go/no-go 를 정한다
3. 문항은 `exports/` 의 45문항 세트를 쓰되, **코퍼스 밖 질문 몇 개를 섞어라** — 빈손일 때
   거동이 달라지는지 봐야 한다

측정 하네스는 새로 만들지 말고 아래 모양을 그대로 쓴다(오늘 쓴 것).

```python
idx = await get_index(BOT_ID)
r = await idx.search(q, top_k=3)
units = _select_units(r, "raw_budget")
inprompt = set(IDRE.findall(_context_block(units) + "\n" + _wiki_block(r)))   # ← 둘 다
resp, _ = await answer_with_wiki(bot_id=BOT_ID, question=q, system_prompt=P, ...)
ids = 마커에서 뽑은 id
oop = ids - inprompt        # 프롬프트 밖
ooc = ids - corpus          # 코퍼스 밖 (wiki_source_units.src_id 전체)
```

---

## 4. 열려 있는 설계 결정 — 사용자에게 물어서 정할 것

**인용 강제 문구를 어디에 두나.**

| | 어디 | 장점 | 단점 |
|---|---|---|---|
| A | 봇 `system_prompt` | 봇마다 조절 가능 | 11봇 전부 손봐야 · 드리프트 |
| B | 코드가 자동으로 덧붙임 (`ops_facts` 오버레이 자리) | 일관 · 한 곳 | **모든 봇의 프롬프트가 바뀐다** |

메모리 `project_prompt_authoring_charter` 가 *"시스템 프롬프트 손대기 전 필독"* 이라고 못 박아 뒀고
문서는 레포 밖(`~/Downloads/축복 앱 문서/`)에 있다. **B 는 그 규약을 건드린다.**

---

## 5. 제약

- **어휘 경로에만 적용한다.** `file_search` 경로는 Gemini 가 인용을 주고 구조가 다르다.
  섞으면 두 경로가 각각 다른 이유로 깨진다
- **`_citations()` 의 `approximate=False` 를 바꾸지 마라.** 그 값은 프론트 각주 앵커링과
  근거 형광펜이 함께 쓴다. 게이트 쪽만 바꾼다
- **`fill_evidence` 를 게이트 앞으로 당기지 마라.** 청크당 LLM 1회라 `lexical` 의 값어치(1.6초)가
  사라진다. 이 방식을 검토했고 기각했다
- **GASP(logprob 기반 근거성)는 불가하다.** 실제로 찔러 봤다:
  `gemini-3.5-flash-lite` + `response_logprobs=True` → `400 Logprobs is not enabled for this model`
- **과잉 거절 금지.** 봇 11은 이미 어휘 검색이라 커버리지가 44.2%다. 게이트를 세게 걸면
  「맨날 모른대」가 된다. §3-2 의 비율이 이 판단의 근거다
- **라이브 DB 는 읽기만.** 로컬 검증용 복제봇이 **봇 29**로 있다(D-1 ver2 · 1,341자 · lexical)

---

## 6. 확인

```bash
cd backend && uv run pytest -q                       # 169 통과
grep -n "approximate=False" backend/app/services/wiki/service.py    # → 127
grep -rn "has_direct_citation" backend/app/services/
# → strict_mode.py:23 (정의) · chat_service.py:587 (비스트리밍 게이트) · 769 (SSE 게이트)
```

```bash
# logprobs 불가 재확인 (GASP 를 다시 검토하려 들 때)
cd backend && uv run python -c "
import asyncio
from google import genai; from google.genai import types
from app.core.config import get_settings
s=get_settings(); c=genai.Client(api_key=s.GEMINI_API_KEY.get_secret_value())
async def m():
    try:
        await c.aio.models.generate_content(model='gemini-3.5-flash-lite',
          contents=[types.Content(role='user',parts=[types.Part(text='hi')])],
          config=types.GenerateContentConfig(response_logprobs=True, logprobs=3, max_output_tokens=5))
        print('지원됨 — GASP 재검토 가능')
    except Exception as e: print('불가:', str(e)[:90])
asyncio.run(m())"
```

---

## 7. 참고 — 업계 조사 (2026-08-10)

| 논문 | 우리에게 |
|---|---|
| **GASP** (arXiv 2607.04223) — 답변 고정 후 근거를 빼며 재채점. grounded 문장은 likelihood 붕괴 | **모델이 logprobs 미지원이라 불가.** 논문이 든 유일한 경쟁 대안은 chunk-level entailment 인데 그건 LLM 호출이 늘어 기각 |
| **HopRefusalBench** (arXiv 2608.01358) — 최고 모델도 올바른 정지율 42.9%. **거절 응답의 84.7~98.4%가 이유는 정확히 안다.** 병목은 「답 안 함」으로 커밋하는 것 | 우리 봇도 같다 — "규정집 기준 확인이 필요합니다"라고 알면서 답한다. **판정을 모델에 맡기지 말고 코드가 커밋시켜야 한다** |
