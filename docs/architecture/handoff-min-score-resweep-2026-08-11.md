# 인계 — 규칙 매칭 하한 재스윕 (n=6 → n=45)

> 검증된 사실 목록이다. 믿지 말고 확인 명령을 다시 돌려라. 값이 다르면 그 사이에 코드가
> 바뀐 것이고 **문서가 아니라 코드가 맞다.**
>
> 앞 문서: `handoff-clarify-live-2026-08-11.md` §8-1 이 남긴 숙제다.

---

## 0. 무엇이 바뀌었나

`CLARIFICATION_MIN_SCORE` **15.0 → 20.0**.

**동작은 안 바뀐다.** 45문항 전부에서 결과가 동일하다 — 산 것은 여유(margin)뿐이다.
정책 JSON 도, 라이브 DB 도 안 건드렸다.

```bash
cd backend && WIKI_DENSE_SCALES="" uv run python -u ../exports/clarify_eval/_sweep.py
# 기대 마지막 4줄:
#   거짓양성 최고  #8    14.46  → family-start-pre-rite
#   참양성 최저    #45   25.78  → b4u-tier
#   안전 구간      (14.46, 25.78]  · 기하 중점 19.31
#   최고 정확도 45/45 를 내는 하한: 14.47 ~ 25.78
```

---

## 1. 앞 스윕이 왜 못 미더웠나

하한 15 는 **판정기가 양성으로 뽑은 6문항**만 표본으로 썼다. 그 집합이 실행마다 흔들린다:

```
results_v3_seedpolicy.json  양성 7건  [12, 18, 33, 34, 36, 39, 45]
results.json (최신)         양성 7건  [18, 20, 33, 34, 36, 39, 45]   ← #12 빠지고 #20 들어옴
```

표본이 Gemini 난수에 매달려 있으면 하한도 난수다.

**끊는 방법은 판정기를 다시 돌리는 게 아니었다.** `min_score` 가 사는 곳은
`match_policy_rule`(`clarification_trigger.py:211-252`)이고 이건 BM25 어휘 비교라 모델이
없다. 판정기는 「되물을까」만 정하고 하한은 「어느 규칙이냐」만 정한다 — 두 축이 분리돼 있다.
그래서 판정 결과와 무관하게 **45문항 전수에 결정론적으로** 돌릴 수 있다.
판정기가 흔들려 어떤 문항이든 양성이 될 수 있으니 오히려 전수가 옳은 표본이다.

**Gemini 0회 · DB 0회 · 쿼터 0.** 재스윕에 판정 재실행은 필요 없었다.

---

## 2. 측정 (`exports/clarify_eval/_sweep.py`)

정답지: 정책 `_note` 의 표적 4건이 참양성, **나머지 41문항은 전부 「걸리는 규칙 없음」**.

| 구분 | 문항 | BM25 | 매칭 규칙 |
|---|---|---|---|
| 참양성 | #18 | 52.23 | `child-first-gen-eligibility` |
| 참양성 | #34 | 41.81 | `family-start-pre-rite` |
| 참양성 | #33 | 27.13 | `family-start-12day` |
| **참양성 최저** | **#45** | **25.78** | `b4u-tier` |
| (지배도 1.5배에서 이미 탈락) | #22 | 24.83 | — |
| **거짓양성 최고** | **#8** | **14.46** | `family-start-pre-rite` ← 「교류 신청 예절」이다 |
| 거짓양성 | #30 | 12.86 | `family-start-pre-rite` |
| 거짓양성 | #12 | 12.72 | `child-first-gen-eligibility` |
| 거짓양성 | #20 | 10.98 | `child-first-gen-eligibility` |
| 거짓양성 | #39 | 10.94 | `child-first-gen-eligibility` (앞 스윕이 쓴 그 값) |

앞 문서의 `#39 10.94` · `#45 25.78` 이 그대로 재현됐다 — 하네스가 맞다.

**안전 구간 (14.46, 25.78] 사이는 비어 있다.** 이 안 어떤 값을 넣어도 45/45 로 같다.

```
거짓양성 최고 14.46 ──(×1.037)── 15.0 ──────────(×1.719)────────── 25.78 참양성 최저
거짓양성 최고 14.46 ──────(×1.383)────── 20.0 ────(×1.289)──────── 25.78 참양성 최저
```

15 를 버린 이유는 틀려서가 아니라 **오매칭 경계에서 0.54 밖에 안 떨어져 있어서**다.
20 은 기하 중점 √(14.46×25.78)=19.31 근처이고 양쪽 여유가 균형을 이룬다.

---

## 3. 하한이 두 벌 있다 — 갈리면 측정과 실물이 다른 규칙을 고른다

| 위치 | 지금 |
|---|---|
| `backend/app/services/chat_service.py:113` | **정본** `CLARIFICATION_MIN_SCORE = 20.0` |
| `backend/tests/test_clarification_policy_v2.py` | `MIN_SCORE = 20.0` + 정본과 같은지 assert |
| `exports/clarify_eval/_run.py` · `_sweep.py` | 정본을 **import** 한다 (베낀 값 없음) |

상수를 `clarification_trigger.py` 로 옮기지 않았다 —
`test_chat_clarification_wiring.py:102` 가 `chat_service.CLARIFICATION_MIN_SCORE` 를
심볼로 참조하고, 옮기면 그 테스트가 깨진다. 값만 바꾸면 그대로 통과한다.

하네스는 테스트에서 import 하지 않는다 — 모듈 로드가 dotenv·엔진 생성까지 끌고 온다.
대신 그쪽의 literal 을 지우고 정본 import 로 바꿨다. **베낄 값이 없으면 드리프트도 없다.**

`/exports` 는 `.gitignore` 에 있지만 **하네스 스크립트는 강제 추적**한다
(`_run.py`·`_audit.py`·`wiki_2026-08/*.py` 가 이미 그렇다). `_sweep.py` 도 `git add -f`
로 넣었다 — 데이터(`questions.json`·`results.json`·`answers.json`)만 제외 대상이다.

---

## 4. 테스트가 이제 하한을 양쪽에서 조인다

이전에는 `TARGETS` 6건이 **하한이 내려가는 쪽만** 잡았다. 세 가지를 더했다:

```
tests/test_clarification_policy_v2.py
  TARGETS 에 #8 추가                          거짓양성 최고점. 하한이 14.46 아래면 실패
  test_harness_uses_the_production_min_score  정본과 테스트 상수 동기화
  test_min_score_sits_inside_the_measured_gap #8·#45 를 그 자리에서 다시 재서 구간 확인
```

마지막 것이 핵심이다. **숫자를 박지 않고 매번 다시 계산한다** — `request_examples` 를
고쳐 경계가 움직이면 거기서 터진다.

---

## 5. 함정

### 5-1. 다음 작업(#20 → 5번째 규칙)이 정확히 이 경계를 건드린다

새 규칙의 `request_examples` 는 「편성·가정출발·축복자녀」 어휘를 기존 두 규칙과 공유한다.
#8(14.46)이 20 위로 올라오거나 #45(25.78)가 20 아래로 내려가면 하한을 다시 골라야 한다.
**규칙을 추가한 직후 `_sweep.py` 를 돌려라.** `test_min_score_sits_inside_the_measured_gap`
가 실패하면 그게 신호다.

### 5-2. 스윕 격자는 관측값만으로는 부족하다

게이트가 `top_score < min_score` 라 관측값 자체는 통과한다. 관측값만 격자로 쓰면
「45/45 구간은 24.83~25.78」이라는 **거짓 결론**이 나온다(14.47~25.78 이 맞다).
`_sweep.py` 는 관측값과 그 바로 위(+0.01)를 같이 넣어 이걸 피한다.

### 5-3. `MIN_RULE_DOMINANCE=1.5` 는 별개 축이다 — 안 건드렸다

#22(24.83)는 하한이 아니라 지배도에서 탈락한 문항이다. 하한을 아무리 만져도 안 바뀐다.
지배도를 스윕하려면 별건으로 하라.

### 5-4. 45문항 세트는 `exports/` 라 레포에 없다

`exports/wiki_eval/questions.json` 은 gitignore 다. 그래서 테스트가 질문 원문을 파일에
박아 둔다(`TARGETS`). 다른 기계에서 `_sweep.py` 를 돌리려면 그 파일이 있어야 한다.

---

## 6. 확인

```bash
cd backend && uv run pytest -q                                        # 224 통과 (기준선 221 +3)
cd backend && uv run pytest tests/test_clarification_policy_v2.py -q  # 12 통과 (9 → +3)
cd backend && uv run pytest tests/test_chat_clarification_wiring.py -q # 6 통과 (무회귀)
cd backend && WIKI_DENSE_SCALES="" uv run python -u ../exports/clarify_eval/_sweep.py
```

**기존 테스트 수정은 `test_clarification_policy_v2.py` 의 상수·주석·`TARGETS` 1건 추가뿐이다.**

### 안 해도 되는 것 (확인함)

- **판정기 재실행 불필요** — 하한은 판정 뒤에만 쓰인다
- **라이브 재적재 불필요** — `load_clarification_policy.py` 는 정책 JSON 을 쓰는 스크립트고,
  하한은 백엔드 코드다. `bots.clarification_policy` 는 안 바뀐다

### 배포

`backend/**` 를 main 에 푸시하면 배포가 자동으로 돈다
(`handoff-clarify-live-2026-08-11.md` §6-7). 라이브에서 되묻기가 켜진 봇은 11 하나뿐이고
45문항 기준 동작이 동일하다. 그래도 **다른 변경과 같은 배포에 섞지 마라.**

---

## 7. 다음

`handoff-clarify-live-2026-08-11.md` §8 의 남은 4건. 순서는 그대로다.
**#20 을 5번째 규칙으로 넣는 작업이 §5-1 때문에 이 문서와 붙어 있다.**
