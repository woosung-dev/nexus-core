# 프롬프트 변경 검증 하네스

프롬프트(또는 RAG) 변경이 회귀를 만들지 않는지 1명령으로 검증한다.
프로브(멀티샘플)→codex 채점→분산 분류→직전 베이스라인 비교를 한 번에 수행한다.

## 사용법 (레포 루트에서)

```bash
# A/B 모드 — 규칙 추가 전(base)/후(rule) 비교
uv run --project backend python tools/verify/harness.py run \
    --questions crisis --bots 5,3 --samples 3 --rule-file 규칙.md --label rule-v4

# 단순 평가 모드 — 현행 프롬프트 회귀 카나리 (rule-file 없음)
uv run --project backend python tools/verify/harness.py run \
    --questions recency --samples 3 --label canary

# 재채점만 (Gemini 호출 없음 — 채점 instruction 튜닝/레거시 raw 검증)
uv run --project backend python tools/verify/harness.py grade \
    --raw exports/crisis_rule_2026-06-12/프로브_결과_raw_v3.json --questions crisis

# 두 런 비교 / 누적 런 목록
uv run --project backend python tools/verify/harness.py compare --a <runDirA> --b <runDirB>
uv run --project backend python tools/verify/harness.py list --questions crisis
```

## 구성

- `harness.py` — 단일 파일. CLI(run/grade/compare/list) + 프로브 + 채점 + 집계 + 비교.
- `questionsets/*.json` — 질문셋(외부화). 질문·채점 instruction·게이트를 담는다.
- 런 산출물: `exports/verify/<질문셋>/<타임스탬프>_<라벨>/`
  (`raw.json` 프로브 원본, `graded.json` 채점 원본, `summary.json` 집계, `compare.md` 직전 대비).

## 핵심 동작

- **A/B vs 단순 평가**: `--rule-file` 유무로 결정. 룰 텍스트는 질문셋에 박지 않는다.
- **멀티샘플**: 문항당 `--samples` 회 생성. codex 채점은 (bot, sample)당 1콜 —
  같은 qid 샘플을 한 콜에 모으면 일관성 편향으로 분산을 과소 탐지하므로 분리한다.
- **분산 3단 분류**: stable(만장일치) / mixed(불일치·worse 없음) / unstable(불일치·worse 포함).
  품질 게이트는 stable+mixed 의 대표 verdict 로만, 치명 게이트(flag)는 전 샘플로 평가한다.
  unstable 이 `max_unstable` 초과면 INCONCLUSIVE(PASS도 FAIL도 아님).

## 질문셋 스키마

```jsonc
{
  "name": "crisis",
  "description": "...",
  "grader": {
    "instruction_ab":     ["...줄 배열, \\n 으로 join 됨..."],   // A/B 모드 채점 지시
    "instruction_single": ["...단순 평가 모드 채점 지시..."],
    "flag_fields": ["safety_fail", "stigma_new", "markup_leak"], // 치명 플래그 (codex 출력 bool)
    "gates": {
      "max_worse_total": 1,                       // 대표 verdict worse 총 허용수 (null=무제한)
      "max_worse_by_qtype": {"일반": 1},          // qtype별 worse 허용수
      "require_better_gte_worse_qtypes": ["충돌"], // 이 qtype 은 better>=worse 요구
      "expect_b_gte_a": true,                     // (A/B) 기대충족 합계 B>=A
      "zero_flags_any_sample": ["safety_fail"],   // 전 샘플 통틀어 0이어야 하는 플래그
      "max_unstable": 2                           // 초과 시 INCONCLUSIVE
    }
  },
  "questions": [{"qid": "P01", "qtype": "위기진행", "question": "...", "expect": "..."}]
}
```

## 제약

- dev DB(localhost) 읽기 전용 — 봇 프롬프트만 로드. Neon 접근 금지(코드 가드).
- 채점은 codex CLI(구독). OpenAI API 과금 경로 없음.
- 봇 매핑: id5=블레싱 가, id3=블레싱 나.
