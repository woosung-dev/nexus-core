# 다음 세션 프롬프트 — `b4u-tier` 슬롯 검토

> 아래 블록을 그대로 붙여 넣으면 된다. 30분 안쪽 작업이다.

---

`docs/architecture/handoff-clarify-wired-2026-08-10.md` §4-5 를 먼저 읽어라.

되묻기 규칙 4개 중 **`b4u-tier` 하나만 사용자 확인 없이 규정 근거로만 정했다**(PR #61).
다른 3개는 규정 지식 보유자가 슬롯을 확정했는데, 이건 인터뷰 질문 4개 상한에 걸려 빠졌다.
**그 슬롯이 틀리면 봇이 엉뚱한 것을 되묻는다** — 시드 규칙이 #33 에 「축복 유형」 대신
「지금 어디까지 진행되셨나요」를 물었던 것과 같은 실패다.

## 지금 규칙 (`docs/architecture/clarification-policy-v2-2026-08-10.json`)

표적 질문: **#45 「B4U 등업 기준이 뭐야?」**
판정기가 짚은 결손: `['본인 세대 및 대상(축복자녀/미혼 1세)', '확인하고자 하는 등업 단계(대기자/신청자/후보자)']`

```
슬롯1  member_tier    「지금 B4U 회원등급이 어떻게 되시나요?」
                     대기자 / 신청자 / 후보자 / 잘 모르겠어요
슬롯2  applicant_type 「어느 쪽에 해당하시나요?」
                     축복자녀 / 미혼 1세 / 국제매칭 희망자
```

## 슬롯2 가 의심스럽다 — 이걸 확인받아라

제26조 표를 열별로 보면 **대상 구분이 「승인 기준」 열이 아니라 「이용 조건」 열에 있다.**

| 회원등급 | 승인 기준 | 상대검색·프로필 열람 조건 |
|---|---|---|
| 대기자 | 회원가입 및 기본정보 입력 단계 | 프로필 공개 불가 / 열람 불가 |
| 신청자 | 축복프로필 작성 완료 후 교구 가정행복부장 승인 | 이용 가능. **축복자녀는 원칙적으로 부모가 이용하며, 미혼 1세는 담당 공직자가 이용** |
| 후보자 | 한국 기준 축복이수 교육을 모두 완료 후 교구 가정행복부장 승인 | 공식 후보자 교류·상담 가능. 프로필 비공개 시 검색 제한 |

즉 **「등업 기준」자체는 회원등급으로만 갈리고, 축복자녀/미혼 1세는 등업 뒤 「누가 쓰는가」를 가른다.**
그렇다면 슬롯2 는 질문 「등업 기준이 뭐야」에 대해 불필요한 되물음일 수 있다.

**물어볼 것 세 가지:**

① **슬롯2(대상 구분)를 남길 것인가?**
   - 남긴다 → 등업 기준도 대상별로 다르다는 근거가 규정집 밖(공문 등)에 있다는 뜻이다. 어디인지 받아라
   - 뺀다 → 슬롯 1개짜리 규칙이 된다. 되묻기 마찰이 절반으로 준다
   - 바꾼다 → 「지금 등급」 대신 「올라가려는 등급」이 맞을 수도 있다. 질문자는 보통 다음 단계를 묻는다

② **「국제매칭 희망자」는 제26조 표에 없다.** 제25조 ①에 B4U 가입 대상으로만 나온다.
   등업 기준이 따로 있는지, 없다면 **`unresolved: true`(정리 중) 대상인지** 확인받아라
   — 「독신 축복」과 같은 상황일 수 있다(§4-5)

③ **슬롯1 선택지가 맞는가?** 대기자 → 신청자 → 후보자 3단계가 현행인지.
   `glo-44` 는 「대기자→신청자→후보자 순」이라고 쓴다

## 고친 뒤 반드시 할 것

```bash
# 1. 규칙이 여전히 표적에 걸리는가 (LLM 0회 · 배선이 실제로 쓰는 함수)
cd backend && uv run pytest tests/test_clarification_policy_v2.py -q     # 9 통과
#    선택지를 바꿨으면 test_unresolved_options_are_marked_not_deleted 도 같이 고쳐라

# 2. 봇에 다시 적재 (관리자 API 로는 안 된다 — 인계 §3-2)
cd backend && uv run python ../scripts/load_clarification_policy.py --bot-id 29

# 3. 선택지를 바꿨으면 재답변 셀을 지우고 다시 감사한다
#    (안 지우면 옛 분기가 살아남아 감사에 섞인다 — 인계 §3-4 에서 실제로 겪었다)
python3 - <<'PY'
import json, pathlib
for name in ("answers.json", "audit.json"):
    p = pathlib.Path("exports/clarify_eval")/name
    d = json.loads(p.read_text())
    if name == "answers.json":
        d = [r for r in d if not r["n"].startswith("45b")]
    else:
        d["cells"] = {k: v for k, v in d["cells"].items() if not k.startswith("45b")}
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
PY
cd backend && uv run python -u ../exports/clarify_eval/_run.py --stage reanswer --retry-failed
cd backend && AUDIT_DIR=$PWD/../exports/clarify_eval AUDIT_ARMS=baseline,clarify \
  uv run python -u ../exports/wiki_eval/_audit.py --stage all
#    ⚠ 요약 출력은 KeyError 로 죽는다(ARM_LABEL 에 baseline/clarify 가 없다).
#      데이터는 audit.json 에 남으니 summarize() 를 직접 불러라 — 인계 §4-4
```

**어휘 카운트로 근거 유무를 판정하지 마라.** 「기성」 37건 · 「독신 축복」 17건으로 멀쩡히
뜨는데 정작 「독신 가정의 가정출발 절차」는 규정집에 없었다. 실제로 가르는 것은 감사뿐이다.

## 제약

- **선택지는 2~5개.** `validate_active_policy` 가 막는다. 6개가 필요하면 다른 걸 빼라
- **규정집이 안 다루는 갈래는 지우지 말고 `unresolved: true` 로 표시해라.** 지우면 공백이
  화면에서 숨고, 질문자는 직접 입력으로 넘어가 같은 지어냄을 다시 만난다
- **판정기(`clarification_trigger.py`)와 판정 축을 건드리지 마라.** 45문항으로 보정된 것이다
- **`request_examples` 는 손대지 마라.** BM25 매칭이 6/6 으로 맞춰져 있다.
  슬롯만 바꾸는 작업이다
- **라이브 DB 는 읽기만.** 로컬 검증용 복제봇이 봇 29 다

## 범위

**이 하나만 한다.** `#20`(5번째 규칙 후보)·`min_score` 재스윕·`judge_answerability` 타임아웃은
별건이다(인계 §7). 규칙을 늘리지 마라.

레포는 `/Users/woosung/project/agy-project/nexus-core`, 브랜치는 `feat/clarification-wiring`
(PR #61) 또는 그 머지 뒤 main 에서 새로 딴다.
