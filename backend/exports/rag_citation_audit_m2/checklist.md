# M2 RAG 인용 캡처 체크리스트

## 검증 (구현 전)
- [x] SDK 1.63 → 2.10.0 핀, uv sync
- [x] 1) generate_content + Tool(file_search) + persona → 답변 정상 (봇5)
- [x] 2) generate_content_stream → 텍스트 청크 + grounding 접근 정상
- [x] 3) file_search_stores list/resolve + documents.list + upload 시그니처 호환
- [x] 4) interactions.create + persona + CITE → file_citation annotations (보고율 3/3)
- [x] 5) is_blocked/safe_response_text/build_gemini_contents import·동작

## 구현
- [x] schemas/rag.py: RAGCitation approximate/uri/page_number 추가
- [x] rag/gemini.py: _CITATION_INSTRUCTION 상수
- [x] rag/gemini.py: search_citations(interactions 기반)
- [x] crud_chat.py: update_message_citations
- [x] chat_service.py: _backfill_citations_async / _schedule_citation_backfill
- [x] chat_service.py: 비스트림·스트림 분기에서 citations 비면 백필 예약
- [x] get_rag_service getattr 가드(search_citations 없는 provider skip)

## 테스트
- [x] test_rag_citation_m2.py (매핑·빈입력·직렬화 단위)
- [x] pytest tests/ 전체 통과
- [x] 라이브 E2E (_verify_m2.py) 인용 보고율
- [x] import smoke
