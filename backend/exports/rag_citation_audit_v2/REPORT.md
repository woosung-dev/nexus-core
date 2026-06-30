# interactions 답변경로 이전 — A/B 검증 결과 (게이트: STOP)

브랜치 `feat/rag-answer-interactions` · 봇 3·5(flash-lite) × 40문항 × OLD(generate_content) vs NEW(interactions) · codex 블라인드 심판.

## 결과 (n=80)

| 지표 | 값 | 게이트 |
|---|---|---|
| 답변품질 승/무/패(NEW기준) | 승 30 · 무 13 · **패 37 (패배율 46.2%)** | FAIL (패≤15%) |
| 정확도(정확%) | **NEW 46.2% vs OLD 55.0%** | FAIL (NEW≥OLD−2pp) |
| 안전 unsafe | NEW 0 · OLD 0 | PASS |
| markup leak | capture 0 · judge 1(오탐) | FAIL(형식상) |
| 인용 보고율(positive 72) | NEW 36% vs OLD 0% | — |
| 인용 무결성(인용한 26건) | full|partial **96%**, hallucinated 5 | PASS |
| 지연 p90 | NEW 12.7s vs OLD 9.3s | PASS(<1.5×) |
| **종합** | | **STOP — 이전 보류** |

## 해석 (정직하게)

- **NEW가 틀린 게 아니라 "조금 덜 선호"됨**: 패배 37건 다수가 "둘 다 정확, OLD가 더 상세/명확"한 근소차. NEW 정확 37·부분오류 41 — 부분오류가 OLD보다 ~7건 많음.
- **markup leak 1건은 오탐**: codex가 "~어떨까요?" 같은 부드러운 제안을 내부표기로 오인. capture의 `<followups>` 정규식은 0.
- **hallucination 5건은 부분지지 뉘앙스**: 답변이 검색된 청크 범위를 약간 넘어 단정(예: 가정회비 '선교활동 목적'이 인용에 없음). 날조라기보단 인용 커버리지 부족.
- **인용은 NEW의 명백한 이득**: 같은 호출에서 정확 인용(무결성 96% 지지), OLD는 0%. 인용 보고율 36%(상담형 문항은 인용 안 함이 정상).

## 핵심 트레이드오프

| | 답변 품질 | 인용 | 호출 수 |
|---|---|---|---|
| **M2(현재 main)** | 우수(정확 55%) | interactions 정확 인용이나 **별도 호출(디커플링)** | 2 |
| **NEW(이 브랜치)** | 회귀(정확 46%) | 같은 호출 인라인(무결성) | 1 |

→ 단일호출·무결성을 얻는 대가로 **답변 정확도 ~9pp 회귀**. 게이트 기준 미충족.

## 교란변수 분리 재검증 (NEW2 = interactions, 인용지시 제거)

| 변형 | 정확도 | 승/무/패(vs OLD) | 인용 보고율(positive) | markup leak |
|---|---|---|---|---|
| OLD (generate_content) | 50~55% | 기준 | 0% | 0 |
| NEW (interactions + 인용지시) | 46% | 30/13/37 | 36% | 0 |
| **NEW2 (interactions, 인용지시 X)** | **52.5%** | **34/12/34(균형)** | **0%** | 0 |

→ `_CITATION_INSTRUCTION`이 **인용 보고와 답변 품질 저하를 동시에** 유발한다. 지시 ON이면 인용(36%)·품질저하, 지시 OFF면 품질회복(OLD 동등)·인용 0. **단일 호출로는 둘을 동시에 못 얻는다.** (NEW2의 게이트1 FAIL은 회귀가 아니라 ~동률을 85% 임계가 못 잡는 보정 이슈 — 정확도 패리티·균형 승패가 본질.)

## 최종 결론 — M2(2-호출) 유지, 마이그레이션 미머지

검증으로 **M2의 2-호출 설계가 정당함이 입증됨**: M2는 답변을 깨끗한 generate_content로 생성하고, 인용은 interactions(인용지시 ON, **답변은 버리고 인용만** 취득)로 받는다. 그래서 인용지시의 품질 저하가 사용자 답변에 닿지 않는다. 단일 호출은 답변·인용이 같은 생성이라 이 분리가 불가능 → 어느 한쪽 희생.

- NEW(인용지시 ON): 답변 품질 회귀 → 불가.
- NEW2(인용지시 OFF): 인용 0 → 의미 없음.
- **M2(현행)**: 답변 우수 + interactions 정확 인용(별도 호출) → 둘 다 확보.

**결정: 이 브랜치는 머지하지 않는다(실험/근거 기록용).** 운영은 M2(main) 유지. 사용자가 지적한 "2-호출 디커플링"은 단점이 아니라 Gemini 거동상 **필요한 분리**임이 데이터로 확인됨.

산출물(scratchpad): `_ab_captures.json`/`_ab_judge.json`(NEW), `_ab2_captures.json`/`_ab2_judge.json`(NEW2), `_capture_ab.py`/`_capture_new2.py`/`_judge_ab_codex.py`/`_report_ab.py`.
