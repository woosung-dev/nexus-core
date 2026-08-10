# 다음 세션 프롬프트 — 되묻기 판정에 타임아웃 (라이브 선행 조건)

> 아래 블록을 그대로 붙여 넣으면 된다. 20분 안쪽 작업이다.

---

`docs/architecture/handoff-clarify-wired-2026-08-10.md` §3-5 를 먼저 읽어라.

되묻기 판정(`judge_answerability`)이 **클라이언트 타임아웃 없이** Gemini 를 부른다.
2026-08-10 측정에서 한 문항이 매달려 **12분간 진행이 멈췄다**(n=13 이후 무응답,
네트워크는 정상이었다). 측정 하네스에는 `JUDGE_TIMEOUT_SEC = 90` 을 넣어 막았지만
**프로덕션 경로에는 없다.**

되묻기는 shadow 판정과 달리 **사용자 응답 경로에 있다** — 응답을 보낸 뒤 도는 게 아니라
답변을 내보내기 전에 부른다(`chat_service._clarification_for`). 그대로 라이브에 켜면
매달린 시간을 사용자가 그대로 기다린다. **켜기 전에 이걸 고쳐야 한다.**

## 무엇을

`backend/app/services/clarification_trigger.py` 의 `judge_answerability` 에서
`service.generate_structured(...)` 를 `asyncio.wait_for` 로 감싼다.

**이미 받을 준비가 돼 있다** — 같은 함수의 `except (ValidationError, RuntimeError, TimeoutError)`
가 `TimeoutError` 를 잡아 `None` 을 돌려주고, 그러면 `decide()` 가 `status="answer"` 로
fail-open 한다. 판정이 늦어도 제품이 벙어리가 되지 않는다는 이 모듈의 규약 그대로다.

**참고할 선례**: `clarification_service.py:39` 에 `CLARIFICATION_TIMEOUT_SEC = 150.0` 이 있고
`_generate_plan` 이 `asyncio.wait_for` 로 쓴다. **다만 150초는 그대로 쓰지 마라** — 그건
File Search 계획 호출용이고, 여기는 답변을 막고 서 있는 자리다. 하네스가 90초를 썼는데
그것도 사용자 대기로는 길다. **실측 분포를 보고 정해라**:

```bash
# 판정 1회가 실제로 얼마나 걸리는가 — 45문항 로그에 남아 있다
grep -oE "gemini structured\(no-tool\) elapsed=[0-9.]+ms" exports/clarify_eval/_run.log \
  | grep -oE "[0-9.]+" | sort -n | awk '{a[NR]=$1} END{
    print "n="NR, "중앙값="a[int(NR/2)]"ms", "p95="a[int(NR*0.95)]"ms", "최대="a[NR]"ms"}'
```

상수는 `chat_service.CLARIFICATION_MIN_SCORE` 옆에 두지 말고 **판정기 안**에 둬라 —
타임아웃은 판정기의 성질이지 배선의 성질이 아니다.

## 테스트

`backend/tests/test_clarification_trigger.py` 에 이미 fail-open 테스트가 4개 있다
(`test_judge_failure_never_silences_the_product` 등). 같은 자리에 하나 더 넣어라:
**판정이 타임아웃하면 `None` 이 나오고 답변이 그대로 진행된다.**

`_FakeJudge` 규약을 그대로 쓴다(LLM 호출 0). `asyncio.sleep` 으로 지연을 흉내 내고
타임아웃 상수를 아주 작게 주입하거나, `generate_structured` 가 `TimeoutError` 를 던지게 한다.

## 확인

```bash
cd backend && uv run pytest tests/test_clarification_trigger.py -q      # 14 + 신규
cd backend && uv run pytest -q                                          # 191 이상 통과
```

## 제약

- **판정 축을 바꾸지 마라.** `needs_user_input` 이지 `answerable` 이 아니다
- **fail-open 을 깨지 마라.** 타임아웃은 「답변을 진행한다」로 가야 한다.
  판정기가 고장 나서 제품이 벙어리가 되는 쪽이 더 나쁘다 — 모듈 docstring 의 규약이다
- **`_schedule_answerability_judge`(3층 shadow 판정)도 같은 함수를 쓴다.** 거긴 응답을 보낸
  뒤라 급하지 않지만, 타임아웃이 생기면 그쪽도 같이 짧아진다. 그게 문제인지 판단해라
- **이 하나만 한다.** `b4u-tier` 슬롯·`min_score` 재스윕·렌더링 버그는 별건이다

## 왜 이게 라이브 선행 조건인가

라이브 11봇은 전부 `clarify_enabled=false` 라 지금은 판정기를 **호출조차 하지 않는다**.
그래서 이 버그는 아직 사용자에게 안 보인다. `clarify_enabled` 를 켜는 순간 노출된다.
인계 §0 의 「라이브에 켜기 전 선행 조건」에 이걸 하나 더 얹는 셈이다.

레포는 `/Users/woosung/project/agy-project/nexus-core`.
