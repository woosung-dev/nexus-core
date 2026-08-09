# 03. RAG/문서기반 AI 제품의 인용·출처 표시 UX 벤치마킹

- 작성일: 2026-08-06
- 목적: 문서기반 정책 안내 챗봇(한국어 종교/행정 규정, RAG 기반)의 인용 UX 재설계를 위한 벤치마킹. 12개 제품의 인라인 인용 표기·출처 패널·근거 시각화·스트리밍 연출·문서 라이브러리 뷰 5개 축을 조사했다.
- 조사 방법: 1차 소스(공식 헬프센터·공식 문서·공식 블로그·오픈소스 실제 코드) 우선. Kapa/Inkeep은 공식 문서 사이트에 내장된 실제 위젯을 라이브 테스트했고, Onyx는 GitHub의 프론트엔드 TSX 소스코드를 직접 열람해 코드 레벨로 검증했다. 1차 소스 접근 실패 항목은 본문에 "1차 소스 접근 실패, 대체 소스 사용" 또는 "미확인"으로 명시했다.

---

## 1. 핵심 발견 요약

1. **순수 텍스트 각주 `[1]`만 쓰는 제품은 사실상 없다.** 조사한 전 제품이 각주를 쓰더라도 hover 팝업(NotebookLM), 아이콘+이름 칩(Kapa/Onyx/Glean), 원형 배지(Notion) 등으로 강화한다. 내부 데이터는 각주 번호 체계여도(Inkeep의 `label: "1"`) 렌더링은 칩으로 하는 것이 지배적 패턴.
2. **명시적 신뢰도 점수(%·색상 경고배지)를 노출하는 제품은 한 곳도 확인되지 않았다.** 근거 유무는 "인용이 붙느냐/안 붙느냐"라는 이진 신호(Glean), "No results found" 텍스트(Onyx), verified 체크마크(Notion) 같은 절제된 방식으로 전달된다.
3. **스트리밍 연출은 "검색 단계의 가시화"가 핵심 차별점.** "Gathering sources..."(Kapa), 쿼리 칩→결과 칩→깜빡이는 커서(Onyx), Research Steps 접이식 섹션(Perplexity), `citations_delta`로 문장 단위 인용 부착(Claude API) 등 검색→생성→인용의 3단계를 보여주는 제품이 신뢰 연출에서 앞선다.
4. **문서 라이브러리 뷰는 제품 성격에 따라 양분된다.** 사용자가 소스를 직접 넣고 체크박스로 스코프를 지정하는 "개인 워크스페이스"형(NotebookLM)과, 관리자가 커넥터를 관리하고 엔드유저에게는 잘 안 보이는 "엔터프라이즈 인덱스"형(Glean/Onyx/Kapa/Dust). 엔드유저 투명성은 NotebookLM이 압도적.
5. **리서치 결론: 인용을 붙이는 것만으로 신뢰·검증이 저절로 생기지 않는다.** NN/g는 "자신감 있는 어조가 검증을 생략시킨다", "작은 경고 라벨은 반복 노출로 배경 소음이 된다"고 경고하며, ECIR'26 사용자 연구는 출처 표시가 효과는 있으나 답변의 명확성·실용성이 함께 받쳐줘야 신뢰가 형성된다고 실증했다. 문단(passage) 단위 딥링크 + 원문 스니펫 강조가 공통 권고.

---

## 2. 패턴별 비교표

### 2-1. 인라인 인용 표기

| 제품 | 방식 | 장점 | 단점 |
|---|---|---|---|
| Perplexity | 도메인명 칩 + "+N" 축약 (예: `northjersey +3`) | 출처 매체를 즉시 스캔 가능, 다중 소스 축약 | 칩 여러 개면 문장이 시각적으로 무거움 |
| ChatGPT 검색 | 파비콘+발행처명 칩 + hover 카드 (데스크톱) | hover로 이동 전 미리보기 | 모바일에서 hover 불가 |
| Claude (API) | 문장 단위 `citations` 블록 앵커링 (`cited_text` 최대 150자) | 구조적으로 가장 정밀 — 어느 문장이 어느 원문 구절에 근거하는지 기계적으로 보장 | UI 렌더링은 클라이언트 구현 몫 (claude.ai의 시각 스타일은 미확인) |
| NotebookLM | 숫자 각주 + hover 시 원문 발췌 팝업 + 클릭 시 원본 위치로 이동 | 본문 가독성 최상(작은 번호), hover에 발췌문까지 | 번호 자체는 무정보 — 반드시 hover/click 필요 |
| Glean | "citation pills"(공식 용어), 문장 단위, hover 시 스니펫+전후 200자 | 문장 단위 정밀도 + 페이지 번호(`pageNumber`)까지 | — |
| Onyx | 아이콘+문서명 칩 (`SourceTag`), 스트리밍 중 미도착 인용은 숨김 처리 | 깨진 마크업 노출 방지, hover 팝오버(1/N 페이징) | — |
| Kapa.ai | 아이콘+문서 제목 칩, 클릭=즉시 새 탭 이동 (hover 카드 없음) | 출처명 즉시 노출, 구현 단순 | 문장 리듬을 끊음, 미리보기 없음 |
| Inkeep | 칩이지만 문장이 아닌 **문단 아래** 독립 줄 배치 | 본문 흐름을 전혀 안 끊음 | 문장 단위 정밀도 상실(문단 단위만) |
| Notion AI Q&A | 원형 숫자 배지(각주형) | 가독성 최상 | 숫자만으로는 무엇을 가리키는지 알 수 없음 |
| Bing Copilot | 문장/구절 전체를 인라인 링크로 | 근거 범위(어디부터 어디까지)가 명확 | 링크 과다 시 본문이 온통 밑줄 |

### 2-2. 출처 패널/카드

| 제품 | 배치 | 표시 내용 |
|---|---|---|
| Perplexity | 3중 구조: "N sources" 버튼→우측 사이드패널 / 별도 Links 탭 / 칩 클릭 팝오버(1/N 페이징) | 파비콘·제목·URL·스니펫·썸네일 |
| ChatGPT 검색 | 답변 하단 "Sources" 버튼 → 패널 | 발행처 로고 카드 목록 |
| NotebookLM | 좌측 Sources 패널 상시 노출 (라이브러리 겸용) | 소스 목록+체크박스, 각주 hover에 발췌문 |
| Glean | 답변 하단 "View sources" 섹션 | 문서/파일/사람 3종 분류, 클릭 시 원래 앱에서 열림 |
| Onyx | 우측 사이드바, "Cited Sources"(인용됨) → "Found Sources"(검색만 됨) → "User Files" 3섹션 | 아이콘+제목 2줄+수정일 배지+태그 배지+키워드 볼드된 스니펫 2줄 |
| Kapa.ai | 별도 패널 없음 — 인라인 칩이 유일한 인용 UI | — |
| Inkeep | 답변 끝 "Sources" 헤더 + 펼쳐진 카드 리스트 (아코디언 아님) | 카테고리 라벨+제목+외부링크 화살표 (스니펫 없음) |
| Notion | Q&A: "N pages found" 플랫 리스트 / Enterprise Search: "결과" 드롭다운(아코디언형)+출처 유형 탭 | 페이지 아이콘+제목 (스니펫 없음) |
| Bing Copilot | "Show all" 버튼 → 우측 패널, 답변과 원문 나란히 대조 | 전체 출처 목록 |

주목할 구분: **Onyx의 "Cited(인용됨) vs Found(검색만 됨)" 분리**는 "검색은 됐지만 답변에 안 쓰인 문서"까지 보여주는 유일한 사례 — 검색 품질에 대한 투명성이 가장 높다.

### 2-3. "근거 있음"의 시각화

| 제품 | 방식 | 근거 부족/없음 시 |
|---|---|---|
| NotebookLM | 인용 자체가 신호. 소스가 짧으면 문장 인용 대신 "문서 전체 참조"로 강등(citation degrade) | 소스에 없으면 "모른다"고 답하도록 설계 (2차 소스 의존, 공식 원문 재확인 못함) |
| Glean | 인용 유무 = 이진 신호. 웹/사내소스 토글을 모두 끄면 "citations won't be included" 명시 | 인용 없는 답변 = 사전학습 지식임을 사용자가 인지 가능 |
| Onyx | 칩 부착 여부가 신호 | 검색 0건 시 "No results found" 텍스트 |
| Notion | **verified 콘텐츠에 파란 체크마크** — 조사 대상 중 유일한 "문서 등급" 시각화 | 권한 없는 문서는 애초에 검색 범위 밖 (경고가 아니라 배제) |
| Kapa.ai | 공식 문서상 "uncertainty reporting"(지식 부족 시 불확실성 보고) 명시 — 실제 UI 형태는 미관찰 | 미확인 |
| Perplexity | Research Steps 접이식 섹션으로 검색 과정 감사 가능. 부정 피드백에 "Wrong sources" 전용 칩 | 미확인 |
| Claude API | 결과 0건 = 오류가 아닌 빈 리스트 반환, 오류 유형별 코드 구분 (API 계약 레벨) | UI 표시는 미확인 |

**공통 패턴: 신뢰도 %·색상 경고배지는 전무.** 절제된 이진 신호 + 텍스트 안내가 업계 표준이다.

### 2-4. 답변 스트리밍/조립 연출

| 제품 | 연출 순서 |
|---|---|
| Perplexity | (API) `search_results` 이벤트 배치 도착 → 텍스트 delta → `[N]` 마커를 결과 id와 매핑. (UI) "Completed N steps" 확장형 섹션 |
| Claude API | 텍스트 생성 → `server_tool_use`(쿼리 스트리밍) → 검색 실행 중 일시 정지 → 결과 스트리밍 → `citations_delta`로 문장별 인용 개별 부착 |
| Onyx | 쿼리 칩 리스트 표시 → 검색된 문서 칩이 하나씩 채워짐 → `BlinkingBar`(animate-pulse) 커서로 텍스트 스트리밍 → 원시 `[1]` 마커를 칩으로 치환 (미도착 인용은 숨김) |
| Kapa.ai | "Gathering sources..." → 텍스트 스트리밍 + 칩 실시간 부착 (라이브 확인) |
| Inkeep | "Thinking · · ·" → 문단 단위 스트리밍, 문단 완성 직후 그 아래 칩 부착 → "✓ Completed" → 맨 끝 Sources 카드 (라이브 확인) |
| Notion | "텍스트 먼저, 페이지 링크는 나중" (공식 헬프센터). 빠른 Q&A와 느린 Research 모드의 기대치를 분리 |
| Mendable | (API) SSE로 `<\|source\|>` 청크가 본문보다 먼저 별도 이벤트로 전송 |
| ChatGPT | 검색모드 자체의 연출은 공식 문서에 명문화 안 됨(미확인). Deep Research는 진행 단계+사용 소스 사이드바 공식 문서화 |

공통 골격: **① 검색 중임을 문구/칩으로 노출 → ② 텍스트 스트리밍 → ③ 인용 부착(치환 또는 후행)**. Onyx의 "미도착 인용 숨김 처리"는 스트리밍 중 깨진 마크업 노출을 막는 실전 디테일.

### 2-5. 문서 라이브러리 뷰

| 제품 | 유형 | 특징 |
|---|---|---|
| NotebookLM | 개인 워크스페이스형 (엔드유저 투명성 최고) | Sources 패널 = 지식 전체. 체크박스로 답변 스코프 지정, 5개 이상이면 자동 주제 라벨링, 최대 50소스 |
| Glean | 엔터프라이즈 인덱스형 | 엔드유저: "All Knowledge" + 웹/사내소스 토글. 관리자: 커넥터 동기화 상태 대시보드, 노출범위 3단계 |
| Onyx | 엔터프라이즈 인덱스형 | 관리자: 커넥터 테이블(Indexed/Scheduled/Indexing/Paused/Error 상태) + Document Sets(커넥터 묶음, 검색 스코프/에이전트 지식 단위). 엔드유저가 봇의 지식범위를 채팅 화면에서 확인 가능한지는 미확인 |
| Kapa.ai | 관리자 전용 | "Manage sources" 대시보드: 카테고리별 소스 목록, source groups, 무중단 re-fetch. 엔드유저 뷰 없음 |
| Dust | 관리자 중심 | Data Sources 5유형(Connections/Folders/Websites/Custom/Conversation Files), 채널·폴더·페이지 단위 제어. 시각 레이아웃은 미확인 |
| Perplexity | 하이브리드 | Spaces(구 Collections)에 파일 업로드, 웹검색과 병용 |
| Notion | 워크스페이스 자체가 라이브러리 | 별도 뷰 없음, 위키/팀스페이스 구조가 곧 지식 범위 |

---

## 3. 제품별 상세

### 3-1. Perplexity — 인용 UX의 사실상 표준

- **인라인**: 공식 헬프센터는 "numbered citations linking to the original sources"라고만 서술. 실제 렌더링은 도메인명 칩 + "+N" 축약인데, 이 세부는 1차 소스 접근 실패(헬프센터 세부 페이지 Cloudflare 403)로 서드파티 UX 티어다운(aiuxplayground.com)을 대체 소스로 사용.
- **출처 패널**: ① "N sources" 버튼 → 우측 사이드패널 ② Answer/Images와 동급인 Links 탭(카드형: 파비콘·URL·제목·스니펫·썸네일) ③ 칩 클릭 팝오버(1/N 페이징). API는 `search_results`에 `id`(본문 [N]과 매핑)·`title`·`url`·`snippet`·`date` 반환.
- **근거 시각화**: "Research Steps" 접이식 섹션에 검색 단계를 평문 노출. 부정 피드백에 "Wrong sources" 전용 칩 — 인용 실패를 일반 오류와 구분 수집. 근거 없음 시의 UI 변화는 미확인.
- **스트리밍**: (API 공식 문서) `response.reasoning.search_results` 배치 도착 → `response.output_text.delta` → `[N]` 마커와 결과 id 매핑.
- **라이브러리**: Spaces에 파일 업로드(PDF/Word/Excel/CSV), 웹검색과 함께 근거로 사용.
- 출처: https://www.perplexity.ai/help-center/en/articles/10352895-how-does-perplexity-work · https://docs.perplexity.ai/docs/cookbook/articles/streaming-citations/README · https://aiuxplayground.com/teardowns/perplexity/citations/ (대체 소스) · https://www.perplexity.ai/help-center/en/articles/10352961-what-are-spaces

### 3-2. ChatGPT 검색모드

- **인라인**: 공식 헬프센터 확인 — 인라인 인용에 hover하면 상세, 클릭하면 출처 이동(데스크톱 웹). 시각 스타일은 파비콘+발행처명 칩 + "+N"(대체 소스: aiuxplayground).
- **출처 패널**: 인라인 인용이 없으면 답변 하단 "Sources" 버튼 → 패널 (공식 헬프센터, 스크린샷 alt 텍스트로 확인).
- **근거 시각화**: 신뢰도 표시 미확인. 예측성 정보에 "Source: Kalshi" 라벨을 붙이는 특수 케이스만 공식 문서화. 인용 전용 부정 피드백은 없음(표준 좋아요/싫어요만, 대체 소스).
- **스트리밍**: 검색모드 자체의 로딩 연출은 공식 문서에 미명문화(미확인). Deep Research(별도 기능)는 "진행 단계 요약+사용 소스 사이드바, 실시간 진행 추적"이 공식 문서로 확인됨.
- **라이브러리**: 해당없음 (Projects 파일 업로드는 검색 인용 흐름과 별개).
- 출처: https://help.openai.com/en/articles/9237897-chatgpt-search · https://openai.com/academy/search-and-deep-research/ · https://help.openai.com/en/articles/10500283-deep-research-faq

### 3-3. Claude (claude.ai + Citations API) — 구조 설계의 참조 모델

- **인라인**: claude.ai UI의 시각 스타일은 공식 문서에 미명시(미확인). **API 구조가 핵심**: 응답이 여러 `text` 블록으로 쪼개지고 근거 있는 구간에만 `citations` 배열이 붙는다(`url`/`title`/`cited_text` 최대 150자). 문장 단위 인용 앵커링을 모델 레벨에서 보장하는 구조.
- **근거 시각화**: 검색 0건 = 오류가 아닌 빈 리스트, 실패 유형은 오류 코드로 구분(`max_uses_exceeded` 등) — UI가 아닌 API 계약이지만 "근거 없음" 상태의 시스템 표현을 보여주는 1차 근거.
- **스트리밍**: `server_tool_use`(쿼리) → 검색 실행 중 일시 정지 → 결과 스트리밍 → `citations_delta`로 문장별 인용 개별 부착. claude.ai는 "Searching the web…" 상태 표시(공식 헬프센터).
- **라이브러리**: 웹검색엔 해당없음. 단 Citations API는 업로드 문서(PDF/텍스트/Files API)에도 동일 인용 구조 지원 — 문서 인용과 웹 인용이 같은 메커니즘 공유.
- **비고**: Citations 공식 블로그 — 커스텀 구현 대비 재현율 최대 15% 향상, 고객 사례(Endex)에서 환각·서식 문제 10%→0%, 인용 텍스트는 출력 토큰 과금 제외. 이 프로젝트의 "인용 근거 형광펜"(어휘매칭 25% 기각 → LLM추출+원문대조 95% 채택) 실험 결과와 방향 일치 — 참조 아키텍처로 검토 가치.
- 출처: https://support.claude.com/en/articles/10684626-enable-and-use-web-search · https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool · https://platform.claude.com/docs/en/build-with-claude/citations · https://claude.com/blog/introducing-citations-api

### 3-4. Google NotebookLM — 문서 라이브러리 투명성의 기준점

- **인라인**: 숫자 각주 + **hover 시 원문 발췌 전체 팝업** + 클릭 시 원본 문서의 해당 위치로 자동 이동. 이미지에도 인용 매핑. (공식 헬프센터 확인)
- **출처 패널**: 좌측 Sources 패널 상시 배치. 개별 체크박스로 "이 소스들만 참고" 스코프 지정 가능.
- **근거 시각화**: 신뢰도 배지 없음. 소스가 너무 짧으면 문장 단위 인용 대신 "문서 전체 참조"로 강등(공식 FAQ: 인용이 항상 붙지는 않음). "소스에 없으면 모른다고 답한다"는 서술은 2차 소스에서 일관되게 확인되나 공식 원문 재확인 실패 — 이 항목만 2차 소스 의존.
- **스트리밍**: 생성 중 Stop 버튼 존재(공식). 단계별 연출은 미확인.
- **라이브러리**: Sources 패널이 곧 전체 지식. Discover 버튼으로 웹 소스 추천(최대 10개+요약), 5개 이상이면 자동 주제 라벨링/그룹핑, 최대 50소스·소스당 50만 단어/200MB. **엔드유저가 "봇이 무엇을 아는지"를 확인하는 투명성에서 조사 대상 중 최고.**
- 출처: https://support.google.com/notebooklm/answer/16179559 · https://support.google.com/notebooklm/answer/16215270 · https://support.google.com/notebooklm/answer/16269187 · https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-discover-sources/

### 3-5. Glean — 문단 단위 딥링크의 참조 모델

- **인라인**: 공식 개발자 문서가 "citation pills" 용어 명시. 문장 단위로 부착, Deep-Linked Citations 활성 시 문서가 아닌 **정확한 근거 구절(passage)로 딥링크** + hover 팝오버에 강조된 스니펫과 전후 약 200자 컨텍스트. 슬라이드/PDF는 페이지 번호까지.
- **출처 패널**: "View sources" 섹션 — 문서/파일/**사람(작성자·소유자)** 3종 분류. 클릭 시 원래 앱(Drive/Confluence 등)에서 열림.
- **근거 시각화**: 인용 유무 자체가 이진 신호. 웹·사내소스 토글을 모두 끄면 "citations won't be included"라고 공식 명시 — 인용 없는 답변은 사전학습 지식임을 구분.
- **스트리밍**: UI 연출 미확인 (멀티스테이지 RAG 파이프라인 서술만 존재).
- **라이브러리**: 엔드유저 — "All Knowledge" 기본 + 웹/사내소스 토글로 근거 범위 조절. 관리자 — 커넥터 동기화 상태 대시보드, 노출범위 3단계(전체/테스트 그룹/비공개). 주의: Glean의 "Library" 기능은 사용자 생성 콘텐츠 모음이지 인덱스 문서 목록이 아님.
- 출처: https://developers.glean.com/guides/chat/deep-linked-citations · https://docs.glean.com/user-guide/assistant/glean-chat/glean-chat-citations/glean-citations · https://docs.glean.com/user-guide/assistant/how-glean-accesses-info · https://docs.glean.com/connectors/about

### 3-6. Onyx (구 Danswer) — 오픈소스라 코드 레벨로 검증됨

전 항목을 GitHub 실제 프론트엔드 TSX 코드로 검증(신뢰도 최고).

- **인라인**: LLM이 `[1]`/`[D1]`/`[Q1]` 마커 출력 → `MemoizedAnchor`가 파싱해 `SourceTag` 칩(아이콘+truncate된 문서명)으로 치환. **스트리밍 중 문서 데이터가 아직 안 온 인용은 숨겼다가 데이터 도착 시 칩으로 표시** — 깨진 마크업 노출 방지.
- **출처 패널**: 우측 사이드바 3섹션 — "Cited Sources"(인용된 순서 정렬) / "Found Sources"(검색됐으나 인용 안 됨) / "User Files". 카드 = 아이콘+제목 2줄+수정일 배지+태그 배지(최대 3개)+검색 키워드 볼드된 스니펫 2줄.
- **근거 시각화**: 칩 hover/click 시 팝오버(제목·아이콘·상대시간·저자/태그, 다중 소스면 1/3 카운터+화살표). 검색 0건이면 "No results found". 신뢰도 점수·색상 배지는 코드상 없음.
- **스트리밍**: 타임라인형 — 쿼리 칩 리스트 → 결과 문서 칩이 하나씩 채워짐 → `BlinkingBar`(animate-pulse) 커서로 텍스트 스트리밍 → 마커를 칩으로 치환.
- **라이브러리**: 관리자 — 커넥터 테이블(Indexed/Scheduled/Indexing/Paused/Error + 데이터량), Document Sets(커넥터 묶음, 검색 스코프 필터/에이전트 지식 단위로 재사용), 폴더 단위 권한(3.x+). 엔드유저 검색 UI에 날짜/작성자/태그/소스타입 필터. 엔드유저가 채팅 화면에서 봇의 지식범위를 직접 확인 가능한지는 미확인.
- 주요 검증 파일: `web/src/app/app/message/MemoizedTextComponents.tsx`(마커→칩 치환), `web/src/refresh-components/buttons/source-tag/SourceTag.tsx`·`SourceTagDetailsCard.tsx`(칩/팝오버), `web/src/sections/document-sidebar/DocumentsSidebar.tsx`·`ChatDocumentDisplay.tsx`(사이드바), `web/src/app/app/message/BlinkingBar.tsx`, `.../timeline/renderers/search/InternalSearchToolRenderer.tsx`(스트리밍)
- 출처: https://github.com/onyx-dot-app/onyx · https://docs.onyx.app/admins/connectors/overview · https://docs.onyx.app/admins/managing_features/document_sets

### 3-7. Kapa.ai — 미니멀 칩 단일 체계 (라이브 테스트 확인)

- **인라인**: 회색 알약형 칩(로고 아이콘+문서 제목)이 문장/불릿 끝에 인라인 삽입. 숫자 없음, hover 카드 없음, 클릭=즉시 새 탭 이동. 인라인 인용 형식은 커스터마이징 불가한 고정 항목(공식 문서 명시).
- **출처 패널**: 없음 — 인라인 칩이 유일한 인용 UI. 하단엔 복사·피드백 아이콘만.
- **근거 시각화**: 공식 문서에 "지식이 부족할 때 불확실성 보고" 명시. 실제 UI 형태는 테스트 중 미관찰(미확인).
- **스트리밍**: "Gathering sources..." → 텍스트 스트리밍+칩 실시간 부착 (라이브 확인).
- **라이브러리**: 엔드유저 뷰 없음. 관리자 "Manage sources" 대시보드(카테고리별 소스·source groups·무중단 re-fetch).
- 출처: https://docs.kapa.ai/ (라이브 테스트) · https://docs.kapa.ai/customizing · https://docs.kapa.ai/data-sources/manage

### 3-8. Inkeep — 문단 단위 칩 + 후행 Sources 리스트 (라이브 테스트 확인)

- **인라인**: 칩이지만 문장 안이 아니라 **각 문단 바로 아래 독립 줄**에 배치. 내부 데이터는 각주 체계(`provideLinks` 툴: `label`/`url`/`title`/`breadcrumbs`)이나 렌더링은 텍스트 칩.
- **출처 패널**: 답변 끝 "Sources" 헤더 + 펼쳐진 세로 카드 리스트(카테고리 라벨+책 아이콘+제목+외부링크 화살표). 스니펫 없음. 오픈소스판은 `Sources`·`InlineCitation` 전용 컴포넌트 공식 제공(Vercel AI Elements).
- **근거 시각화**: 배지 없음. 생성 완료 시 "✓ Completed" 상태 텍스트.
- **스트리밍**: "Thinking · · ·" → 문단 단위 스트리밍+문단 완성 직후 칩 부착 → "✓ Completed" → 맨 끝 Sources 리스트 (라이브 확인).
- **라이브러리**: 엔드유저 뷰 없음. 관리자 대시보드 "Sources" 섹션에서 소스 추가·색인.
- 출처: https://docs.inkeep.com/ (라이브 테스트) · https://docs.inkeep.com/cloud/ai-api/question-answer-mode/overview · https://docs.inkeep.com/talk-to-your-agents/vercel-ai-sdk/ai-elements

### 3-9. Mendable — API 레벨만 확정 (위젯 라이브 테스트 실패)

- 1차 소스 접근 실패(자사 문서 내장 위젯이 백엔드 무응답), API 문서 기반으로만 확정.
- **API**: 응답에 `sources[]`(`id`/`content`/`link`/`relevance_score`) 반환 — **조사 대상 중 유일하게 관련도 점수를 노출하는 API**. 렌더링은 클라이언트 위임(기본 컴포넌트가 인라인 인용을 그리지 않는 것으로 보임 — 추정).
- **스트리밍**: SSE로 `<|source|>` 청크(출처 메타데이터)가 본문보다 먼저 별도 이벤트로 전송 → `<|message_id|>` → 도구 청크.
- **라이브러리**: 없음. 문서 수집 API도 "제공 예정" 상태.
- 출처: https://docs.mendable.ai/mendable-api/chat · https://docs.mendable.ai/examples

### 3-10. Dust — 시각 스타일 미확인

- 공식 문서·블로그·마케팅 페이지를 다각도로 탐색했으나 실제 앱은 로그인 필요, 마케팅 데모는 잠긴 애니메이션이라 **인라인 인용의 시각 스타일은 끝내 미확인** (1차 소스 접근 실패).
- 확인된 것: RAG 3단계(청크 검색 → 모델 전달 → "올바른 출처로의 링크와 함께 응답 생성")가 공식 문서화. Data Sources 5유형(Connections/Folders/Public Websites/Custom/Conversation Files), Slack 채널·Drive 폴더·Notion 페이지 단위 제어.
- 출처: https://docs.dust.tt/docs/user-documentation/agents/knowledge/search-data-sources · https://docs.dust.tt/docs/what-are-data-sources

### 3-11. Notion AI Q&A — 각주 배지 + verified 체크

- **인라인**: 원형 숫자 배지(각주형) — 본문 가독성 최상, 대신 숫자만으론 무정보. (공식 블로그 제품 스크린샷 확인)
- **출처 패널**: Q&A 모드 — 답변 아래 "N pages found" 플랫 리스트(아이콘+제목). Enterprise Search — AI 개요 + "결과" 드롭다운(아코디언형) + 출처 유형별 탭 + 제목/작성자/팀스페이스 필터.
- **근거 시각화**: **verified 콘텐츠에 파란 체크마크** — 조사 대상 중 유일하게 "문서 자체의 공인 등급"을 시각화. 권한 없는 문서는 경고가 아니라 검색 범위에서 배제.
- **스트리밍**: "텍스트가 먼저, 페이지 링크는 나중"(공식 헬프센터). 빠른 Q&A vs 느린 Research 모드의 기대치 분리.
- 출처: https://www.notion.com/blog/introducing-q-and-a · https://www.notion.com/help/guides/find-answers-and-generate-reports-with-enterprise-search · https://www.notion.com/help/guides/understanding-how-q-and-a-finds-answers-can-help-you-get-better-results

### 3-12. (참고) Bing Copilot

- 문장/구절 전체를 인라인 링크로 처리("inline links the entire sentence or passage", 공식 Bing 블로그). "Show all" 버튼 → 우측 패널에서 답변과 원문 대조. 신뢰도 라벨·로딩 연출은 미확인.
- 출처: https://blogs.bing.com/search/April-2025/Introducing-Copilot-Search-in-Bing · https://www.microsoft.com/en-us/microsoft-copilot/blog/2025/11/07/bringing-the-best-of-ai-search-to-copilot/

---

## 4. 연구/디자인 아티클 요약

### 4-1. AI Chatbots Discourage Error Checking — NN/g, Pavel Samsonov, 2025-05
- https://www.nngroup.com/articles/ai-chatbots-discourage-error-checking/
- 챗봇의 자신감 있는 어조·문법적 정확성·세심한 서식이 "권위 있는 출처"처럼 보여 사용자가 검증을 생략하게 만든다. 변호사·의사가 존재하지 않는 판례/논문을 인용한 실제 사례 제시. 설계 권고: **인용 출처로의 딥링크 + 스니펫 강조**, 클릭 가능한 추적 질문.
- 시사점: 인용 UX는 장식이 아니라 검증 행동을 유도하는 장치로 설계해야 함 — 이 프로젝트의 "인용 근거 형광펜"(grounding_supports로 실제 참고 대목 강조) 방향과 정확히 일치하는 근거 자료.

### 4-2. AI Hallucinations: What Designers Need to Know — NN/g, Page Laubheimer, 2025-02
- https://www.nngroup.com/articles/ai-hallucinations/
- 신뢰 구축에는 AI의 한계 인정이 필요: 불확실성의 1인칭 표현, 신뢰도 표기, 명확한 출처 링크 권고. 동시에 **"작고 일반적인 경고 라벨은 반복 노출로 배경 소음이 되어 행동을 바꾸지 못한다"**고 경고.
- 시사점: 상시 면책 문구 대신, 근거가 실제로 부족한 답변에만 상태가 달라지는(조건부) 신호를 설계할 것.

### 4-3. Magic-8-Ball Thinking — NN/g, Caleb Sponheim, 2024-08
- https://www.nngroup.com/articles/ai-magic-8-ball/
- 사용자가 AI 출력을 검증 없이 수용하는 패턴 경고. 정답이 반복되면 경각심이 낮아짐. 인라인 인용·정보 카드 + Gemini "Double check response" 같은 능동적 자체검증 기능을 대안으로 제시.
- 시사점: 정책 안내처럼 "대체로 맞는" 도메인일수록 인용이 클릭되지 않고 방치될 위험 — 수동적 링크가 아닌 능동적 확인 유도(원문 대조 버튼류) 고려.

### 4-4. Trust Me on This: A User Study of Trustworthiness for RAG Responses — Łajewska & Balog, ECIR '26
- https://arxiv.org/abs/2601.14460
- 통제 사용자 연구: 출처 표시·사실 근거·정보 범위 세 설명 유형 모두 사용자를 객관적으로 더 나은 응답으로 유도하는 효과가 있었으나, **신뢰 판단은 객관적 품질만이 아니라 응답의 명확성·실용성·사용자의 사전 지식에도 강하게 좌우됨**.
- 시사점: "인용을 더 많이/정확히" ≠ "신뢰 상승". 답변의 가독성·실행가능성 개선과 병행해야 효과가 남 — 메모리의 "간략하게 답하기(결론 위주)" 원칙과 연결.

### 4-5. (업계 관점) Anthropic Citations API 블로그 / Glean 인용 아티클
- https://claude.com/blog/introducing-citations-api — 프롬프트 유도 인용의 비일관성 문제의식에서 출발, 문서 원문 그라운딩으로 재현율 +15%, 고객 사례 환각 10%→0%. (최초 공개는 2025-01 베타로 추정 — 페이지 표기일과 불일치, 정확한 최초 발행일 미확인)
- https://www.glean.com/perspectives/top-ai-assistants-for-accurate-source-citations — 신뢰 4요소: RAG 검색, 권한 인식 검색, 문장 단위 인라인 인용, 다중 출처 종합. UX 권고: **문서 단위가 아닌 구체적 문단으로 링크**, 모든 인용이 실제 접근 가능한 출처로 연결.

---

## 5. 종합: 이 프로젝트에 추천하는 인용 UX 조합 3가지

전제: 한국어 종교/행정 규정 안내 챗봇. 소스는 웹이 아닌 **내부 규정 문서**(사용자가 원문에 항상 접근 가능하지 않을 수 있음)이므로, 웹검색형 제품의 "클릭=원문 새 탭 이동" 패턴을 그대로 쓸 수 없고 **스니펫을 UI 안에서 보여주는 것**이 더 중요하다. 또한 기존 실험 결론("어휘 카운트 근거 판정 금지", "grounding으로 답변 게이팅 금지", "grounding 보고 누락 ≠ RAG 미작동")을 반영했다.

### A. 보수적 조합 — 검증된 패턴만, 구현 난이도 낮음

| 축 | 채택 패턴 | 참조 제품 |
|---|---|---|
| 인라인 | 숫자 각주 배지 (원형, 문장 끝) | Notion, NotebookLM |
| 출처 표시 | 답변 하단 카드 리스트 (문서명+조항/페이지+스니펫 2줄) | Inkeep, Onyx 카드 구성 |
| 근거 시각화 | 인용 유무 = 이진 신호. 검색 0건 시 "규정집에서 관련 근거를 찾지 못했습니다" 텍스트 | Glean, Onyx |
| 스트리밍 | "규정집 확인 중..." 단일 문구 → 텍스트 스트리밍 → 완료 후 카드 부착 | Kapa, Notion |
| 라이브러리 | 없음 (관리자 화면에만 문서 목록) | Kapa |

- 채택 이유: 전 요소가 최소 2개 제품에서 검증된 패턴. 각주 배지는 한국어 본문 가독성을 해치지 않고, 후행 카드 리스트는 스트리밍 중 인용 마커 치환 로직이 불필요해 프론트 구현이 단순하다.
- 고려사항: NN/g 연구가 지적하듯 후행 리스트는 클릭율이 낮아 검증 유도가 약하다. 각주 번호와 카드의 대응을 시각적으로 명확히 할 것(카드에 같은 번호 표기). 규정 문서 특성상 카드에 반드시 **조항 번호/문서 버전(예: 2026 정본)**을 표기해야 한다.

### B. 균형 조합 — 신뢰 신호 강화, 중간 난이도 (권장)

| 축 | 채택 패턴 | 참조 제품 |
|---|---|---|
| 인라인 | 숫자 각주 + **hover/tap 시 원문 발췌 팝업** (모바일은 바텀시트) | NotebookLM 각주 + Glean hover 프리뷰 |
| 출처 표시 | 하단 카드 리스트 + 카드 확장 시 **근거 구절 형광펜 강조 스니펫**(전후 문맥 포함) | Glean Deep-Linked Citations |
| 근거 시각화 | 3상태: 인용 있음(기본) / 근거 부족 시 답변 상단에 조건부 안내 문구 / 검색 0건 시 명시 텍스트. 신뢰도 %는 노출하지 않음 | NN/g 권고 + 업계 공통(점수 미노출) |
| 스트리밍 | "규정집 검색 중..."(검색 쿼리·대상 문서 칩 노출) → 텍스트 스트리밍 → 각주가 문장 단위로 부착 | Onyx 타임라인, Claude `citations_delta` |
| 라이브러리 | 엔드유저용 "이 봇이 아는 문서" 시트: 문서명+버전+최종 갱신일 목록 (읽기 전용) | NotebookLM Sources 패널의 축소판 |

- 채택 이유: hover 발췌 팝업 + 형광펜 스니펫은 NN/g가 권고한 "딥링크+스니펫 강조"의 구현체이고, 이 프로젝트에서 이미 검증한 "인용 근거 형광펜"(LLM추출+원문대조 95%) 파이프라인을 그대로 활용할 수 있다. 문서 라이브러리 공개는 "규정집 어디까지 아는 봇인지"에 대한 사용자 불신을 구조적으로 해소한다 — 조사 대상 중 NotebookLM만 갖춘 차별점을 가벼운 형태로 이식.
- 고려사항: ① 인용 부착은 반드시 문장→원문 그라운딩 기반이어야 함(어휘 카운트 판정은 기존 감사에서 거짓양성 확인됨). Anthropic Citations API류의 구조(문장 단위 `cited_text` 앵커링)를 백엔드 계약으로 채택 검토. ② "근거 부족" 안내는 조건부로만 — 상시 노출하면 배경 소음화(NN/g). ③ grounding 보고 누락이 인용 0으로 이어지는 기존 이슈가 있으므로, "인용 없음" UI 상태를 "근거 없음"으로 단정 표기하지 말 것(게이팅 금지 원칙).

### C. 실험적 조합 — 차별화 경험, 구현 난이도 높음

| 축 | 채택 패턴 | 참조 제품 |
|---|---|---|
| 인라인 | 문장 단위 그라운딩: 근거 있는 문장에 각주 + 탭 시 **우측(모바일: 하단) 원문 뷰어가 해당 조항으로 스크롤 + 형광펜** | NotebookLM 클릭 내비게이션 + Bing "답변·원문 나란히 대조" |
| 출처 표시 | 원문 뷰어 패널 상시 병치. "인용된 문서 / 검색됐지만 인용 안 된 문서" 2구획 | Onyx Cited/Found 분리 |
| 근거 시각화 | 문서 등급 배지: 정본(2026 규정집)=체크마크, 공문=별도 라벨, 보조자료=무배지. 답변 문장별로 근거 등급이 다르면 각주 색으로 구분 | Notion verified 체크 응용 |
| 스트리밍 | 검색 단계 타임라인(쿼리 칩 → 검색된 문서 칩 → 생성) + 능동 검증 버튼("원문과 대조하기") | Onyx 타임라인 + Gemini Double-check 개념(NN/g 소개) |
| 라이브러리 | 대화 진입 전 소스 패널: 문서 카드(버전·발효일·관할)+주제 라벨 자동 그룹핑, 사용자가 답변 스코프 선택 | NotebookLM 체크박스 스코프 |

- 채택 이유: 규정 안내라는 도메인은 "답이 아니라 조항"이 최종 근거이므로, 원문 뷰어 병치는 웹검색형 제품이 못 하는 차별화가 가능하다. Cited/Found 분리는 "검색은 됐는데 왜 안 썼나"까지 투명하게 만들어 관리자 감사(근거상태 라벨 검증)에도 재사용된다. 문서 등급 배지는 기존 인터뷰에서 확정된 "2022승인/정본2026(P0)" 위계와 자연스럽게 맞물린다.
- 고려사항: ① 원문 뷰어는 문서 전문 렌더링+앵커 좌표가 필요해 파이프라인 비용이 크다(NFD/NFC 파일명 혼재 이슈부터 정리 필요). ② 근거 등급을 각주 색으로 구분하는 것은 업계에 전례가 없는(조사 범위 내 미발견) 실험 — 사용자 테스트 없이 배포하지 말 것. ③ ECIR'26 연구대로 인용 강화만으로 신뢰가 오르지 않으므로, 답변 자체의 간결성(결론 우선)을 함께 유지해야 한다.

### 공통 원칙 (세 조합 모두 적용)

1. **신뢰도 % 점수는 노출하지 않는다** — 조사한 12개 제품 중 노출 사례 0건. Mendable조차 `relevance_score`를 API에만 두고 UI 노출은 확인 안 됨.
2. **스트리밍 중 미완성 인용 마커를 노출하지 않는다** — Onyx의 "숨겼다가 데이터 도착 시 칩 표시" 패턴 채택.
3. **인용 카드에는 문서명만이 아니라 조항·버전을 함께** — Glean의 pageNumber, 이 도메인에선 "규정집 §4, 2026 정본" 수준의 입자.
4. **"인용 없음"과 "근거 없음"을 UI에서 동일시하지 않는다** — 기존 실증(grounding 보고 누락 ≠ RAG 미작동)에 따라, 인용이 비어도 답변을 차단하거나 경고로 도배하지 않는다.

---

## 부록: 조사 한계

- Perplexity 웹 UI 세부·ChatGPT 검색 칩 스타일은 공식 헬프센터가 시각 스타일을 명문화하지 않아 서드파티 UX 티어다운(aiuxplayground.com)을 대체 소스로 사용했다.
- Dust는 실제 앱 로그인 장벽으로 인라인 인용 시각 스타일 미확인. Mendable은 위젯 백엔드 무응답으로 API 레벨만 확정.
- claude.ai 웹 UI의 인용 렌더링 스타일, NotebookLM의 "모른다고 답한다" 동작의 공식 원문, ChatGPT 검색모드의 로딩 연출은 미확인으로 남김.
- NN/g의 "72% 사용자가 톤이 신뢰에 영향" 류의 수치는 검색 스니펫에서만 보였고 원문 대조에 실패해 본문에서 인용하지 않았다.
