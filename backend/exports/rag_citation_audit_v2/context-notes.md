# interactions 답변경로 이전 — Context Notes

브랜치 `feat/rag-answer-interactions` (origin/main 기준 격리 worktree, google-genai==2.10.0).

## 배경
M2(PR #31)는 답변(generate_content)과 인용(interactions 사이드패스)을 **두 호출**로 따로 받아, 인용이 그 답변의 실제 출처라는 보장이 없었다(사용자 지적). 정공법 = 답변 경로를 interactions 로 옮겨 **단일 호출**로 답변+그 답변 자신의 정확 인용을 받는다.

## 라이브 프로브 결정사항 (실측, scratchpad/probe_interactions.py 등)
- **비스트림 interactions**: output_text 에 `<followups>` 블록 동반(✓ smuggle 가능), 인라인 `[n.n]` 마커 없음, file_citation annotations 다수(19건 등). → 단일 호출로 답변+인용+followups 전부 획득.
- **스트리밍 interactions**: annotations 가 델타·completed·interactions.get 어디에도 안 실림(0건). file_search_result 델타 result=null. → **스트림으론 인용 못 받음.**
- 그래서 스트림 경로는 **의사-스트림** 채택(사용자 결정): interactions 비스트림 1회로 답변+인용+followups 받고 본문을 청크로 SSE 전송. 모든 경로 단일호출·정확인용·무결성.
- 멀티턴 input: `[{"type":"user_input"|"model_output","content":[{"type":"text","text":..}]}, ... , user_input(현재)]` 수용·문맥반영 정상.
- 안전: interactions 는 finish_reason 없음 → `status in (failed,cancelled)` 또는 빈 output_text 로 차단 판정.

## 구현 요약
- `rag/gemini.py`: `_interactions_answer`(공용 단일호출), `generate_with_rag`/`generate_stream_with_rag` 모두 이를 사용. 헬퍼 `_citations_from_steps`(file_citation→RAGCitation approximate=False)·`_build_interaction_input`·`_chunk_text`. system_instruction = persona + `_CITATION_INSTRUCTION` + `_FOLLOWUPS_INSTRUCTION`. temperature 0 금지(인용 억제). 레거시 generate_content·grounding 파싱 제거, 미사용 import(genai/types/build_gemini_contents/is_blocked/safe_response_text) 정리.
- `chat_service.py`: 백필 전부 제거(인용 인라인). 스트림은 최종 dict의 `followups`를 사용(별도 generate_followups 호출 제거). 비스트림은 rag_response.followups 그대로.
- `search_citations`/`update_message_citations` 유지(관리/수동 재인용용, 자동호출 안 함).
- 테스트: `test_rag_interactions.py` 신규, `test_rag_config`/`test_safety_block`/`test_chat_history` interactions 형태로 재작성. `pytest` 68 passed.

## 라이브 E2E 스모크
비스트림·의사스트림 모두 답변 양호·`<followups>` 누출 없음·followups 추출 정상. 인용은 비결정적(해당 런 0건, 프로브선 19건) — A/B에서 정량화.

## 검증(A/B, generator/evaluator)
40Q×봇3·5로 OLD(generate_content) vs NEW(interactions) 캡처 → codex 블라인드 A/B(답변품질 승/무/패)+NEW 인용무결성 → 게이트(답변품질 무회귀·정확도·안전·markup 0·인용지지≥80%·지연 참고). 게이트 통과 시에만 이전. 스크립트: scratchpad/_capture_ab.py·_judge_ab_codex.py·_report_ab.py.

## 미해결/주의
- 인용 비결정성 ~25% 공백은 단일호출에도 잔존(스트림은 구조적으로 인용 0이라 의사스트림으로 우회). 게이트 인용보고율로 정량.
- 의사스트림은 TTFT 증가(토큰 실시간 스트림 아님) — 사용자가 수용 결정.
