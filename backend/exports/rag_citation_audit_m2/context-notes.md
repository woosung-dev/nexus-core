# M2 컨텍스트 노트 (결정·근거)

## 핵심 결정
- **메인 답변 경로 무변경**: generate_with_rag / generate_stream_with_rag 의 generate_content +
  grounding 추출 로직은 손대지 않음. 답변 품질·지연·SSE 와이어 포맷을 그대로 보존하기 위함.
- **인용은 사이드패스(interactions)로만**: persona가 grounding 보고를 억제(운영 캡처율 1.4%)하는
  문제를 interactions 채널의 file_citation annotations 로 우회. annotations 는 정확 인용이므로
  approximate=False.
- **비동기 백필**: 요청 트랜잭션과 분리된 새 async_session 에서 인용을 채움. 응답 반환을 막지 않음.
  답변 메시지 커밋 후 message_id 로 update_message_citations → commit.
- **citations 가 비었을 때만 백필 예약**: generate_content 가 드물게 인용을 남기면 그대로 쓰고,
  못 남긴 경우(대부분)에만 interactions 호출(추가 API 비용 최소화).
- **temperature 미지정**: 통제실험에서 temperature=0 은 인용을 죽임. search_citations 는
  generation_config 를 아예 넘기지 않음(서버 기본 유지).
- **인용 지침(_CITATION_INSTRUCTION)**: persona 뒤에 붙여 보고율 33%→75% 로 상승(검증됨).

## 검증된 사실 (SDK 2.10.0, 봇5 라이브)
- interactions annotation 필드: type, document_uri, file_name, source(청크 원문),
  custom_metadata, page_number(선택), start_index, end_index.
- 매핑: title=file_name, content=source[:800], uri=document_uri, page_number=page_number.
- aio.interactions.create 는 async 코루틴 — 서비스의 self._client.aio 경로 그대로 사용.

## 비결정성 / 리스크
- interactions 인용 보고율 ~75% (봇5 4/4, 봇3 2/4). 공백(0건) 시 백필은 아무것도 안 쓰고 종료 →
  기존 동작과 동일(인용 빈 메시지). 재현 안정성은 모델 비결정성에 의존.
- gemini-2.5-flash 는 100% 지만 모델 변경 시 답변 품질 재검증 필요라 채택 안 함(현행 flash-lite 유지).
- 백필 태스크는 이벤트 루프 종료(서버 셧다운) 시 중단될 수 있음 — 인용은 부가정보라 허용.
