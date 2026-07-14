# RAG 인용(출처) 아키텍처

기준일 2026-07-14 · 대상 `backend/app/services/rag/gemini.py`, `chat_service.py`, `frontend-{client,admin}/**/MessageCitations.tsx`

## 한 줄 요약

**지금 화면에 보이는 출처는 사용자가 읽은 답변의 인용이 아니다.** 백필이 새로 생성한 두 번째 답변의 인용이다. 그래서 `approximate=True`로 라벨하고 UI가 "참고 가능한 자료(근사)"로 표기한다. 이건 임시방편(F)이고, 목적지는 D 또는 A다.

## 왜 이렇게 됐나 — 페르소나가 grounding 보고를 죽인다

답변 경로는 `models.generate_content` + File Search tool + 페르소나 system_prompt다. **페르소나가 있으면 `grounding_metadata`가 통째로 빈다.**

| 조건 | 인용 캡처율 |
|---|---|
| 운영(페르소나 있음) | **1.4%** (1/72) |
| 페르소나 제거 | **97.2%** (70/72) |
| 페르소나를 대화턴으로 이동 | **0%** |

측정: `exports/rag_citation_audit/REPORT.md`(2026-06-30, 80쌍). 누락 71건의 원인은 아키텍처(페르소나) 69 · 라이브러리 1 · 검색미발생 1 · **코드(필드 미독) 0**.

중요한 반증 두 가지.

- **`grounding_supports`·`citation_metadata`를 추가로 읽어도 소용없다** — 같은 호출에서 1.2%로 동일. 페르소나 경로엔 읽을 신호 자체가 없다.
- **페르소나 위치를 바꿔도 소용없다** — system_instruction이든 대화턴이든 0. 단일 호출 우회는 존재하지 않는다.

검색 자체는 정상이다(조용한 grounding 97.2%). 문서에만 있는 공문 번호·수치가 답변에 정확히 등장한다. **"보고"만 누락된다.**

⚠️ **인용 0건으로 답변을 게이팅하지 말 것.** 검색은 되는데 보고만 없으므로 정상 답변까지 막힌다.

## 현행 구조 (F — 재생성 백필)

```
사용자 질문
  │
  ├─→ generate_content(persona + file_search)  ──→  답변 A  ──→ 화면 표시·DB 저장
  │      └ grounding_metadata = 비어 있음 (98.6%)
  │
  └─ (비동기, 응답 후) chat_service._schedule_citation_backfill
        └─→ interactions.create(persona + 인용지침)  ──→  답변 B (버려짐)
              └ file_citation 어노테이션 ──→ messages.citations 에 백필
```

**결함**: 인용은 답변 B를 가리키는데 사용자는 답변 A를 읽는다. 실측 fidelity gap **7/25**(`exports/rag_ad_probe_2026-07-02/`). 대표 사례 — 표시답변은 "금액 확인 불가"인데 백필 인용은 "250만원" 문서 7건.

**측정치**

| 항목 | 값 |
|---|---|
| 백필 지연 | ~14.8초 (프론트가 폴링해야 하는 이유) |
| 백필 인용율 | flash-lite **88%** / 2.5-flash 40% (봇5 × 25문항) |
| 검색 빈손 | ~28% (모든 인용 아키텍처의 상한) |

## 라이브러리 제약 (google-genai 2.10.0, Gemini Developer API)

| 항목 | 상태 |
|---|---|
| Interactions API | **2026-06 GA**, Google 권장·기본 경로. `generate_content`는 "Legacy"로 재명명 |
| File Search 인용 정식 경로 | interactions `file_citation` 어노테이션 (`groundingSupports` 아님) |
| `FileCitation` 필드 | `start_index`/`end_index`(**바이트**, end exclusive), `file_name`, `document_uri`, `source`, `page_number`, `custom_metadata`, `media_id` |
| `page_number`·`uri`·`custom_metadata` | **사용 가능** ("not supported in **Vertex AI**" = Gemini API 에선 지원) |
| `document_name`·`rag_chunk`(**chunk_id**) | **사용 불가** ("not supported in Gemini API" = Vertex 전용) |
| 인용 강제 노브 | **없음**. `FileSearch` = `file_search_store_names`/`top_k`/`metadata_filter` 3필드뿐 |
| standalone retrieve | **없음**. `file_search_stores` 에 query/search 없음 → C(retrieve-then-cite) 원천 불가 |
| `grounding_supports` 문서화 | population 조건 **전무**. `grounding_chunks` docstring 은 File Search 를 언급조차 안 함(stale) |

**chunk_id 가 없다는 게 설계를 규정한다.** dedup 은 `(title, uri, page_number, sha256(content[:200]))` 근사 키로만 가능하다(`_citation_key`).

## 인용 데이터 모양 — 44건은 문서 44개가 아니다

`file_citation` 1건 = **"답변의 이 구간 ↔ 이 청크"** 연결선. 문서가 아니다.

```
문서(3개)  →  청크(10개)  →  어노테이션(35건)
[2022_ver.] 규정집.pdf
  ├ p.40 청크 ──→ 10개 구간을 뒷받침
  ├ p.42 청크 ──→  5개 구간
  └ p.46 청크 ──→  3개 구간
축복자녀_심사기준.md ─→ 6개 구간
부모매칭_가이드북.txt ─→ 4개 구간
```

한 청크가 여러 문장을 뒷받침하면 문장마다 1건씩 붙고, 한 문장을 여러 청크가 동시에 뒷받침하기도 한다. 25문항 실측 분포는 **어노테이션 중앙값 6건 · 고유 파일 중앙값 2개**(최대 4). 44건은 이상치다.

그래서 `_dedupe_citations()`가 청크로 합치며 `cite_count`(구간 수)를 누적하고, 프론트가 파일명으로 묶어 점수 내림차순 정렬한다.

**⚠️ `cite_count` 로 % 를 노출하지 말 것.** span 은 답변 B 기준이다. "표시된 답변의 70% 근거"는 거짓이다(커버리지 합이 116%인 것도 구간 중첩 탓). 정렬에만 쓴다. 근사일 땐 배지도 "주요 근거"가 아니라 "가장 많이 검색됨"이다.

## 목적지

| 아키텍처 | 판정 | 요지 |
|---|---|---|
| **F (현행)** | 교체 대상 | 재생성 백필. fidelity gap 7/25 실증 |
| **D (post-hoc 귀속)** | **즉시 권고** | 저장된 표시답변을 **읽기 전용 입력 상수**로 두고 persona-free 재검색 청크에 정렬. gap 이 "낮아짐"이 아니라 **불가능**해짐 |
| **A (interactions 단일패스)** | 목적지 | 답변 자체를 interactions 로 생성 → span 이 표시답변을 가리켜 문장 하이라이트·각주 가능. 현시점 인용율·품질 미달로 재프로브 대기 |
| B (generate_content 동일콜) | **반증됨** | 페르소나 있으면 grounding 0. 위치를 바꿔도 0 |
| C (retrieve-then-cite) | 불가 | standalone retrieve 부재. 관리형 File Search 를 떠나야 함 |
| E (Anthropic Citations) | 북극성 | RAG 백엔드 전면 교체 |

### D 마이그레이션이 부딪힐 이음새 (알려진 부채)

- **`_backfill_citations_async()`가 `prompt` 만 받는다**(`chat_service.py:32`). D 는 **표시된 답변 텍스트**가 1차 입력이라 시그니처가 바뀐다.
- **`BaseRAGService` 에 `search_citations` 가 없다** — `chat_service.py:45` 가 `getattr()` 로 우회한다. 인터페이스가 아니다. D 는 retrieval-only 계약과 attribution 계약이 필요하다.
- **`RAGCitation` 이 청크 모양이다** — 문장 귀속·confidence·span·미지지(unsupported) 상태·귀속 방법을 표현하지 못한다.
- **`search_citations(history=...)` 는 죽은 파라미터**다(선언만 있고 미사용). 후속 턴("그럼 얼마야?")의 백필은 문맥 없는 질의로 검색된다.

D 프로토타입은 `exports/rag_ad_probe_2026-07-02/_attribute_d.py`(165줄)에 있다. **로컬 sentence-transformers 불필요** — `gemini-embedding-001`을 기존 클라이언트로 호출한다. 3단 게이트 필요(임계값 단독 불가: 0.75 coverage 93.2% → 0.85 17.3%, 0.80~0.85 구간 지지율 함몰).

## 알려진 부채 (이 문서 기준 미해결)

- **스트리밍 경로 비대칭** — `generate_stream_with_rag` 는 `_split_answer_and_followups()` 를 거치지 않아 `[1.2]` 인용 마커가 본문에 샐 수 있고, `chat_service` 가 잡은 citations 를 SSE 로 내보내지 않는다. 현재 client 는 `stream: false` 로만 호출해 노출되지 않는다.
- **`_CITATION_MARKER_RE` 가 인라인 마커를 지운다**(`gemini.py:112`). A 로 가면 이 마커가 각주의 근거가 되므로 그때 재검토 필요.
- **`approximate` 플래그의 진실 조건이 경로마다 다르다** — grounding_chunks 경로(같은 생성)는 `False`, interactions 백필은 `True`. 새 경로를 추가하면 반드시 이 축을 정할 것.

## 참고

- `exports/rag_citation_audit/REPORT.md` — 페르소나 억제 실측(80쌍)
- `exports/rag_ad_probe_2026-07-02/REPORT.md` — A/D/F 실측(25문항), fidelity gap 실증
- `exports/rag_citation_sweep_2026-07-14/REPORT.md` — 백필 모델 스윕(lite 88% vs 2.5-flash 40%)
