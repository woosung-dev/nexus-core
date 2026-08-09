# LLM 위키를 기존 RAG 에 어떻게 얹을 것인가 — 3안

> 2026-08-08. 위키 생성 파이프라인은 완료(138쪽·문장 971·인용 대조 99.7%).
> **백엔드에 wiki 참조 0건** — 지금 위키를 아무리 고쳐도 사용자 답변은 안 바뀐다.
> 이 문서는 그 연결을 설계한다.

## 지금 파이프라인 (실측, `chat_service.py`)

```
요청
 ├─ 1. FAQ Override          search_faq_override()  · pgvector 시맨틱 라우팅
 │                            hit 이면 여기서 끝 (LLM 호출 없음)
 ├─ 2. history 로드           bot.history_window
 ├─ 3. ops_facts 오버레이     load_runtime_facts() → build_prompt_overlay()
 │                            system_prompt 뒤에 블록으로 붙음
 │                            term(표기통일)은 프롬프트 아니라 응답 후처리 치환
 └─ 4. RAG 분기
      strict  → _generate_strict_rag_stream   인용 없으면 답변 차단
      일반    → _generate_rag_stream
      비스트림 → generate_with_rag

    Gemini file_search:
      store_name = 봇 공용 스토어 1개
      metadata_filter = "bot_id = 11"
      top_k = settings.RAG_TOP_K
      custom_metadata = [bot_id(numeric), content_sha256(string)]   ← 확장 가능
```

**이미 있는 것 3개가 위키를 얹을 자리다.**

1. `load_runtime_facts` 옆 — 검색 결과를 프롬프트에 얹는 자리가 이미 있다
2. `custom_metadata` / `metadata_filter` — 층을 갈라 검색할 수 있다 (문자열 필터 표현식)
3. FAQ 의 pgvector 라우팅 — 질문 → 문서 매칭 코드가 이미 돌고 있다

## 위키 산출물의 모양

```markdown
---
slug: 가정공과금
sources: [reg-54, reg-55, reg-59, glo-12, glo-22, ...]   ← 원문 앵커 목록
---
## 요약      한 문단. 검색 대상으로 크기가 딱 맞다.
## 사실      문장 + [[src: reg-55]] + > 원문 인용
## 모순      관리자 판정 대상
## 문서에 없음
```

`sources` 가 있다는 게 핵심이다. **위키 페이지 하나를 고르면 관련 원문 조각이 결정적으로 따라온다.**

---

# 1안 — 프롬프트 오버레이 (ops_facts 옆자리)

질문으로 위키 `## 요약` 을 검색해 상위 1~2쪽을 시스템 프롬프트에 얹는다.
Gemini 스토어는 손대지 않는다.

```python
# chat_service.py, load_runtime_facts 바로 아래
wiki_ctx = await load_wiki_context(self.session, bot, request.message)   # 신규
effective_system_prompt = (
    (bot.system_prompt or "")
    + build_prompt_overlay(ops_facts)
    + build_wiki_overlay(wiki_ctx)          # 신규
)
```

| | |
|---|---|
| 손대는 곳 | `chat_service.py` 3줄 + `wiki_service.py` 신규 1개 |
| 검색 | pgvector (FAQ 와 같은 방식). 위키 138쪽 요약만 임베딩 |
| 인용 | **위키가 인용을 안 만든다.** 기존 원문 grounding 그대로 |
| 롤백 | 봇 플래그 하나 |
| 비용 | 반나절 |

**장점** — 가장 싸고, 라이브 스토어를 안 건드리고, 기존 인용 경로가 그대로다.
**단점** — 프롬프트가 길어진다. 위키 내용이 답에 반영돼도 **근거가 원문 조각으로만 표시**되어
"위키 덕분에 맞았는지"를 사후에 가려내기 어렵다.

**★★★★☆ — 측정용으로 최적. 종착지는 아니다.**

---

# 2안 — 위키를 별도 층으로 스토어에 올리고 필터로 라우팅

위키 138쪽을 `layer="wiki"` 로 태깅해 같은 스토어에 올린다. 원문 250건은 `layer="raw"`.

```python
custom_metadata = [
    {"key": "bot_id", "numeric_value": bot_id},
    {"key": "layer", "string_value": "wiki"},      # 신규
]
# 검색 시
metadata_filter = 'bot_id = 11 AND layer = "wiki"'
```

| | |
|---|---|
| 손대는 곳 | `gemini.py` 업로드·검색 2곳 + 업로드 스크립트 |
| 검색 | Gemini file_search 그대로. 필터만 추가 |
| 인용 | **위키 페이지가 인용으로 잡힌다** — 원문 추적이 한 단계 늘어남 |
| 롤백 | 필터 문자열 되돌리기 |
| 비용 | 1~2일 |

**장점** — Gemini 검색을 그대로 쓴다. 층을 갈라놔서 섞이지 않는다.
**단점** — **어느 층을 볼지 누가 정하는가**가 미결이다. 셋 다 문제가 있다.

```
항상 위키만     원문에 있는데 위키에 안 실린 내용을 못 찾는다
항상 둘 다      top_k 예산이 갈린다. 지금도 검색이 병목인데 더 나빠진다
LLM 라우터      호출이 한 번 늘고, 라우팅 오판이라는 새 오류원이 생긴다
```

그리고 인용이 위키 페이지로 바뀌면 **`ops_facts` 때 겪은 "치환하면 각주 사라지는" 함정**을
다른 모양으로 다시 만난다. 사용자에게 보여줄 근거가 규정집 조문이 아니라 우리가 만든 요약이 된다.

**★★☆☆☆ — 권하지 않는다. 미결을 코드로 옮길 뿐이다.**

---

# 3안 — 결정적 2단 검색 (위키는 라우터, 근거는 항상 원문)

위키를 **검색 대상이 아니라 색인**으로 쓴다.

```
질문
 └─▶ ① 위키 요약 138개에서 top-k 페이지 선택        pgvector · 우리 코드 · 결정적
       └─▶ ② 그 페이지의 frontmatter sources 를 읽음   [reg-54, reg-55, reg-59, ...]
             └─▶ ③ Gemini file_search 를 그 앵커로 좁혀 호출
                   metadata_filter = 'bot_id = 11 AND src_id IN ("reg-54", ...)'
                   └─▶ ④ 답변 생성. 인용은 원문 앵커 그대로
```

위키 `## 사실` 문장은 컨텍스트로 함께 얹되, **근거로 표시되는 것은 언제나 원문**이다.

| | |
|---|---|
| 손대는 곳 | `wiki_service.py` 신규 · `gemini.py` 필터 파라미터 · `chat_service.py` 분기 |
| 검색 | 1단은 우리 pgvector, 2단은 Gemini file_search |
| 인용 | **원문 앵커 그대로.** 각주가 안 사라진다 |
| 전제 | 원문 250건 업로드 시 `src_id` 를 custom_metadata 에 넣어야 함 (현재 없음) |
| 비용 | 3~4일 |

**장점**

- `wiki-todo.md` P2 의 미결 **"원문을 함께 남길 것인가"가 구조적으로 사라진다.**
  위키는 라우팅에만 쓰고 근거는 항상 원문이므로, 검색이 둘 중 뭘 고를지 고민할 일이 없다.
- 검색 범위가 조문 250개에서 관련 20개로 좁혀진다. **병목이 검색이라는 실측**
  (`branch_ablation_2026-08-04`, L2 분기별 검색 1순위)에 정면으로 맞는 처방이다.
- 1단이 결정적이라 **왜 이 답이 나왔는지 재현된다.** 회귀 하네스로 측정이 된다.
- 이 구조가 곧 RAPTOR / parent-document retriever 패턴이다 — 요약 레이어로 찾고
  원문 leaf 로 답한다. 계층이 뚜렷한 문서에서 가장 잘 듣는 것으로 보고돼 있다.

**단점**

- 1단이 틀리면 2단이 아무리 좋아도 못 고친다. 위키 요약 품질에 성능이 묶인다.
- 원문 재업로드가 필요하다 (`src_id` 메타데이터). 봇 11 기준 250건.

**★★★★★ — 종착지. 다만 1안으로 값을 본 뒤에 간다.**

---

# 비교

| | 1안 오버레이 | 2안 층 분리 | 3안 2단 검색 |
|---|---|---|---|
| 구현 비용 | 반나절 | 1~2일 | 3~4일 |
| 인용이 원문으로 남나 | ✅ | ❌ 위키가 됨 | ✅ |
| 검색 병목 개선 | ❌ | △ | ✅ |
| 재현·측정 용이 | △ | ❌ | ✅ |
| 미결(원문 병존) 해소 | 미룸 | 코드로 옮김 | **해소** |
| 롤백 | 플래그 | 필터 | 플래그 |

**권고: 1안으로 이번 주에 값을 재고, 값이 나오면 3안으로 간다. 2안은 건너뛴다.**

값이 안 나오면 거기서 접는다 — `wiki-todo.md` P2 에 적어둔 그대로다.

---

# 어떻게 테스트하나

## A. 회귀 하네스 A/B (배치)

`exports/regression/` 55문항이 이미 있다. 봇 플래그 하나로 위키 on/off 를 갈라 같은 질문을 두 번 돌린다.

```
측정 항목
  앵커 충족률        답에 있어야 할 조문이 실제로 인용됐나
  폐지·현행 미적용    C05·C06 — 지금 8/8 오답인 구간
  근거 없을 때 유보   지금 최선의 팔이 4/10
  검색 지연          3안은 2단이라 늘 수 있다. 재야 한다
```

**판정선을 먼저 정한다.** 프롬프트 4종 실험에서 팔 간 차이 8pp 가 잡음 바닥 20pp 안에 있었다.
**20pp 를 못 넘으면 개선이 아니다.**

## B. 질의 시뮬레이터 (관리자 화면)

`/wiki` 워크벤치에 탭 하나를 더한다. 질문을 넣으면 4열로 보여준다.

```
┌ 질문 ────────────────────────────────────────────────────┐
│ 미혼 1세가 축복자녀와 축복받으려면 나이 제한이 있나요?      │
├───────────┬───────────┬───────────────┬──────────────────┤
│ 위키 후보  │ 소환된    │ 위키 없이     │ 위키 켜고        │
│ (1단 결과) │ 원문 조각 │ 답            │ 답               │
├───────────┼───────────┼───────────────┼──────────────────┤
│ 축복자녀- │ reg-19    │ …            │ …               │
│ 미혼-1세  │ reg-39    │              │                  │
│ (0.82)    │ reg-17    │ 인용 2건      │ 인용 3건          │
└───────────┴───────────┴───────────────┴──────────────────┘
```

**1단이 뭘 골랐는지가 보여야 한다.** 답만 보면 3안의 실패 원인(1단 오선택 vs 2단 부실)을
가려낼 수 없다. 이 화면이 없으면 3안은 디버깅이 안 된다.

## C. 선행 조건

3안을 재려면 원문 업로드에 `src_id` 메타데이터가 있어야 한다. 없으면 2단 필터를 못 건다.
**1안 측정과 병행해서 재업로드를 준비한다.**

---

# 남은 판단 2개

1. **1단 검색을 pgvector 로 할 것인가, Gemini 로 할 것인가.**
   pgvector 권장 — FAQ 가 이미 그 코드를 쓰고 있고, 결정적이라 재현된다.
2. **위키 `## 모순`·`## 문서에 없음` 을 답변에 쓸 것인가.**
   당장은 쓰지 않는다. 관리자가 판정하기 전의 모순을 사용자에게 보이면 안 된다.
   `검토상태` 게이팅과 같은 정책이 먼저다.

---

## 참고

- [Contextual Retrieval in AI Systems — Anthropic](https://www.anthropic.com/engineering/contextual-retrieval)
- [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/file/8a2acd174940dbca361a6398a4f9df91-Paper-Conference.pdf)
- [NodeRAG: Structuring Graph-based RAG with Heterogeneous Nodes](https://arxiv.org/pdf/2504.11544)
- [RAG Architecture: From Naive Pipelines to Agentic Retrieval — Galileo](https://galileo.ai/blog/rag-architecture)
- 실측 근거: `exports/prompt4_2026-08-05/FINDINGS.md` · `exports/branch_ablation_2026-08-04/`
- 선행 설계: `docs/architecture/handoff-llm-wiki-2026-08-07.md` · `wiki-todo.md`
