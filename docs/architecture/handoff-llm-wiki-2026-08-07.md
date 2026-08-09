# 핸드오프 — LLM 위키 봇별 지식 컴파일 레이어 (2026-08-07)

> **다음 세션 1순위.** 이 문서만 읽고 실행할 수 있게 쓴다.
> 저장소 규약은 루트 `AGENTS.md` (응답은 결론부터, 읽기 전용 실험 규율).
>
> 선행 문서: `handoff-glossary-repair-2026-08-05.md` §8 (이 안을 한 번 보류시킨 판정) ·
> `exports/prompt4_2026-08-05/FINDINGS.md` (440호출 실측) ·
> `exports/ops_facts_2026-08/README.md` (하류에 붙는 운영 사실 레이어)

---

## 0. 30초 요약

규정집·대사전·공문을 **봇별로** 하나의 상호연결 위키로 컴파일한다. 챗봇은 원문 청크가 아니라
이 위키를 참조하게 되고, 관리자는 위키가 드러낸 **모순과 공백**만 판정한다.

생성은 **로컬 CLI 에이전트(codex)** 가 markdown 파일에 쓴다. 백엔드는 LLM 을 돌리지 않는다.
markdown 이 정본이고 DB 는 관리자 화면용 캐시다.

**이번 세션이 확정한 것은 설계뿐이다. 코드는 한 줄도 쓰지 않았다.**

---

## 1. Context — 왜 이걸 하는가

### 앞선 실측이 가리키는 곳

`exports/prompt4_2026-08-05/FINDINGS.md` (봇 11 · 55문항 × 2회 × 4프롬프트 = 440호출 · 오류 0):

| 사실 | 수치 |
|---|---|
| 검색·인용 | 4팔 전부 **94~95%** — RAG 는 정상이다 |
| 폐지·현행 미적용 기준 (C05·C06) | **8/8 오답** |
| 근거 없는 5문항에서 유보 | 최선인 팔조차 **4/10** |
| 앵커 충족률 팔 간 차이 | 8pp — **잡음 바닥 20pp 안** |

**프롬프트로도 RAG 로도 안 움직인 것들이다.** 원인은 검색이 아니라 *지식이 정리돼 있지 않다는 것* 이다 —
같은 질문마다 원문 조각에서 매번 다시 조립한다. 축적이 없다.

### 카파시 llm-wiki 패턴

<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f> (원문 전체 확인함)

> "the LLM **incrementally builds and maintains a persistent wiki** … The cross-references are
> already there. The contradictions have already been flagged."

3층 = **raw**(불변) / **wiki**(LLM이 씀) / **schema**(행동 규약).
3동작 = **Ingest**(소스 1건이 10~15쪽 갱신) / **Query**(위키를 읽고 답, 좋은 답은 페이지로 환류) /
**Lint**(모순·낡은 주장·고아 페이지·빠진 교차참조 점검).

### 이 도메인이 특별히 잘 맞는 이유

모순이 **이미 실측으로 쌓여 있다.** 관리자 라벨 ↔ 규정집 45문항 중 18건 갈림 ·
v19→v20 조문 **62건 +1 이동** · 가정행복국 번호 0500/0502 · 문서 0건 주제 4종.
위키의 최대 산출물이 "모순 플래그"인데, 우리는 그게 가장 필요한 도메인에 있다.

### ⚠ 선행 판정과의 관계

`docs/architecture/handoff-glossary-repair-2026-08-05.md` §8 이 이 안을 **보류**시켰다.
반대근거 5개 중 **③ "잴 자가 없다"(기준선이 세션 간 뒤집힘)는 여전히 유효하다.**
그래서 §7 판정 기준을 반증 가능하게 잡는다 — 통과 못 하면 접는다.

---

## 2. 이번 세션에 새로 확정된 것 — 봇별 스코핑

사용자 요구: **Documents 탭이 봇별로 문서를 관리하듯, 위키도 봇별이어야 한다.**

실측(`exports/rag_snapshot_before_2026-08-05.json`, 스토어 `nexus-core-knowledge-base` · 총 189건):

| 봇 | 문서 수 | 구성 |
|---|---:|---|
| **11 · 테스트 봇 D-1 ver2 (주력)** | **2** | **규정집 v20 + 대사전 v4** |
| 8 · 테스트 봇 D-1 | 1 | 규정집만 |
| 6 · 7 | 17 | 공문 포함 |
| 3 · 5 | 17 | 2022 국제 규정집 계열 |
| 21 · 22 | 15 | |
| 4 · 15~19 | 11 | |

**봇마다 문서 집합이 실제로 다르므로 위키는 반드시 봇별이다.** 전역 위키는 성립하지 않는다.

사용자가 지정한 원본 2개는 봇 11 의 문서 집합과 정확히 일치하고,
`exports/golden_2026-08/_corpus_build.py:27-28` 이 이미 이 두 파일을 읽는다.

```
~/Downloads/신한국_축복가정행정_규정집_개정초안_2026v20_축복자녀간축복보완.pdf
   sha256 d8a5ef90e8036df9e8170d1f0bb3ccfcd3fc8b7f84fa251a2f0335cd4f5d5180 · 2,062,334 B
~/Downloads/세계평화통일가정연합_대사전_가정행복국_행정용어_통합본_축복자녀간축복보완_v4.pdf
   sha256 93636bb2855357b61be3d80abe2f25fb407a9e29a07d577d7d0ef1d8b89ed12c · 13,867,017 B
```

### 부수 발견 (별건, 이번 범위 밖)

스토어에 **봇 15~22 의 문서가 남아 있는데 `bots` 테이블엔 id 1~11 만 있다.**
삭제된 봇의 문서가 잔류 중이다. 검색은 `bot_id` 필터라 현재 사고는 없으나 정리 대상이다.

---

## 3. 아키텍처

```
raw (불변)         codex exec (로컬·순차)      wiki/*.md          _verify        _load        /wiki
규정집 v20  ──▶   AGENTS.md 규약 적용    ──▶  정본(git)   ──▶  인용 원문  ──▶  DB 캐시 ──▶  봇 선택기
대사전 v4                                                        대조·자가수리                  + 판정
```

### 왜 백엔드에서 LLM 을 돌리지 않는가

1. **ingest 는 단발 호출이 아니다.** 소스 1건이 파일 10~15개를 고치는 에이전트 루프다.
   FastAPI 에서 하려면 에이전트 프레임워크를 직접 만들어야 한다.
2. **비용.** codex CLI 는 구독이라 과금 0. 이 레포는 이미 채점을 그렇게 한다.
3. **안전.** 위키 생성이 라이브 서비스 경로에 아예 없어야 한다.

### 왜 파일이 정본인가

git diff·history·롤백이 공짜(카파시가 명시). 에이전트가 파일시스템 도구를 이미 갖고 있어
별도 tool 구현이 필요 없다. DB 는 화면이 읽는 캐시일 뿐이고 `_load.py` 로 언제든 재생성된다.

### 디렉토리 — raw 는 문서 단위 공유, wiki 는 봇 단위

```
exports/wiki_2026-08/
  sources/<sha8>/          문서별 낱개 raw. 봇 무관·불변.
    meta.json              display_name · sha256 · size · kind
    001.md … 100.md
  bots/<bot_id>/
    AGENTS.md              공통 템플릿 + 이 봇의 문서 목록
    manifest.json          이 봇이 쓰는 sources/<sha8> 목록
    wiki/
      index.md  log.md  pages/*.md
  _snapshot.py  _split.py  _ingest.py  _verify.py  _load.py
```

같은 규정집을 봇 11·8 이 함께 가지므로 **raw 는 한 벌만 둔다.** 위키만 봇별로 갈린다.

---

## 4. 에이전트 호출 — 기술 상세

`exports/golden_2026-08/_draft.py:97` 의 `codex()` 를 그대로 본뜨되 **샌드박스가 바뀐다.**

```python
subprocess.run(["codex", "exec", instruction,
                "-s", "workspace-write",        # 기존 read-only → 쓰기 필요
                "-c", 'model_reasoning_effort="high"'],
               cwd=str(BOT_DIR),                # 쓰기 범위를 봇 폴더로 가둔다
               input=json.dumps(payload, ensure_ascii=False),
               capture_output=True, text=True, timeout=TIMEOUT)
```

- **순차 실행. 병렬 금지.** 두 세션이 같은 엔티티 페이지를 동시에 고치면 덮어쓴다.
- **resume 키 = 소스 id.** 배치마다 저장한다 — 이 레포엔 18번째 배치에서 터져 앞선 17배치(≈50분)를
  날린 전례가 있다.
- 로컬 확인: `codex-cli 0.146.1` · `claude` 둘 다 `~/.local/bin` 에 있다.
- 어려운 문서는 **Claude Code 대화형 ingest** 로 사람이 개입한다(카파시가 실제로 하는 방식).

---

## 5. AGENTS.md 스키마 — 이 도메인 특유의 5개

일반 llm-wiki 와 갈리는 지점이다. 규정 도메인이라 다섯 개가 더 붙는다.

1. **모든 문장에 출처 앵커.** `[[src: reg-43]]` 없는 문장은 위키에 남기지 않는다.
2. **quote 는 원문 그대로.** 요약·재작성 금지. 프로그램이 대조한다.
3. **문서에 없으면 쓰지 마라.** 추정으로 채우지 말고 `## 문서에 없음` 에 질문으로 남긴다.
4. **모순은 한쪽을 고르지 마라.** `## 모순` 에 양쪽을 나란히 적고 관리자 판정을 기다린다.
5. **조문번호는 검수용.** 챗봇 답변에는 싣지 않는다(v20 활용 원칙).

로그 규약은 카파시 그대로: `## [2026-08-08] ingest | 제43조(12일 가정출발의식)`

---

## 6. 안전장치 — 인용 원문 대조 + 자가수리

`exports/golden_2026-08/_draft.py` 의 3단 구조를 재사용한다.
골든 40건에서 **인용 대조 40/40 · 자가수리 3회 작동 · 지어낸 인용 3건 포착**된 코드다.

```python
# _draft.py:94 — pdftotext 가 "탕 감봉"처럼 공백을 끼워 넣어서
# 공백을 남기면 멀쩡한 인용이 거짓 불일치로 떨어진다
_norm = lambda s: _WS.sub("", _DIGIT_KO.sub(r"\1", unicodedata.normalize("NFC", s)))
```

quote 가 raw 에 실재하지 않으면 → 그 페이지를 **폐기하고** 에이전트가 요구한 조문을 실제로 넣어
재생성(최대 2회).

`_corpus_build.py` 의 조문 분해도 그대로 쓴다 — 조문 100개·결번 0·중복 0 을 검증하고
실패하면 `sys.exit` 한다(`_corpus_build.py:68`).

---

## 7. 판정 기준 — 반증 가능해야 한다

**나는 이미 모순 5건을 안다. 파이프라인이 그걸 독립적으로 재발견하는가가 시험이다.**

| # | 모순 | 파이프라인이 찾아야 할 것 |
|---|---|---|
| 1 | 12일 가정출발의식 조문번호 | v20 은 **제43조**. 제42조는 40일 대체교육 |
| 2 | 금식 기간 | 제17조 **3일 금식**(특별사유 시 9일 조식) ↔ 챗봇 7일 |
| 3 | 성물 수 | 제70조① **천일국 4대 성물** ↔ '5대성물' |
| 4 | 2세×2세 가정출발 | 제35조·제43조 모두 대상 한정 → **문서에 없음**으로 남겨야 함 |
| 5 | 매칭확정자 연령 | 공문 2025-259호 ↔ 제17조 만 20세 ↔ 챗봇 |

| 관측 | 결론 |
|---|---|
| 1·2·4 를 스스로 찾음 (3/3) | **패턴이 이 도메인에서 작동한다. 계속** |
| 1~2건만 찾음 | 조건부 — 스키마 문안을 고쳐 재시도 |
| 0건 | **접는다.** 지금 시안이 그럴듯한 건 내가 잘 쓴 것이지 패턴의 힘이 아니다 |

추가 게이트: **인용 대조 100%** · 조문 100개 중 페이지에 안 실린 것 **0건**.

---

## 8. 실행 순서

| # | 작업 | 산출 | 시간 |
|---|---|---|---|
| 0 | **실행 전 점검** — `exports/glossary_repair_2026-08-05/_ragverify.py` 를 그대로 돌린다 | 봇 11 문서 2건·sha 일치 확인 | 5m |
| 1 | `_split.py` — PDF → `sources/<sha8>/*.md` (`_corpus_build.py` 재사용) | raw 250건 | 1h |
| 2 | `AGENTS.md` 스키마 (§5) | 규약 1장 | 30m |
| 3 | **스모크 — 조문 5개만 ingest** | 형식 확인 | 30m |
| 4 | 전량 ingest (봇 11) | 페이지 ~40쪽 | **2~3.5h 무인** |
| 5 | `_verify.py` 인용 대조 | 100% | 1h |
| 6 | `_load.py` → DB (bot_id 포함) | | 1h |
| 7 | `/wiki` 화면을 실데이터 + 봇 선택기로 교체 | | 1.5h |
| 8 | `/ops-facts` 에도 같은 봇 선택기 부착 (§10 곁가지) | | 30m |

**3번에서 멈춰 사용자 확인을 받는다.** 250건을 다 돌리기 전에 형식이 맞는지 보는 게 싸다.

### 첫 실행 스코프 — 확정

- **봇 11 하나.** 문서 2건 = 규정집 100조 + 대사전 150항.
  주력 봇이고 440호출 실측도 이 봇이라 개선 전후 비교가 성립한다.
- 봇 7(공문 4종 포함)은 2차. 나머지 문서가 로컬에 텍스트로 없어 R2 에서 sha256 으로
  캐와야 하므로(`exports/glossary_steering_2026-08-04/_fetch_regbook.py` 가 그 방법) 실패 지점이 는다.
- **대사전은 앞 33쪽 행정용어 150개만.** 뒤 ~1,960쪽은 사상교리 대사전이라 제외
  (블록 경계를 안 닫으면 마지막 항목 body 가 300만자가 되어 LLM 입력이 터진다).
- 공문 4종은 봇 11 문서 집합에 **없다** — 봇 6·7 에만 있다. 2차 대상.
- 과금 **0** (codex 구독).

---

## 9. DB 스키마

```
wiki_sources(id, sha256, doc, kind, locator, quote)      ← bot_id 없음. 문서 단위 공유
wiki_pages(id, bot_id NOT NULL, slug, title, category, summary, body_md,
           status, approver, approved_at, admin_note, updated_at)
           unique(bot_id, slug)
wiki_claims(id, page_id, text, refs jsonb, conflict_id)
wiki_conflicts(id, bot_id NOT NULL, title, sides jsonb, impact, page_id, status)
wiki_gaps(id, bot_id NOT NULL, title, detail, page_id, hits)
```

**`ops_facts` 와 규약이 다르다.** ops_facts 는 `bot_id NULL = 전역`이지만,
위키는 **NULL 을 허용하지 않는다** — 항상 어떤 봇의 문서 집합에서 나오므로 전역 위키가 성립하지 않는다.

마이그레이션 `down_revision` 은 현재 head `a1f6c30d84be`(add_ops_facts). 적용 전 `alembic heads` 확인.

---

## 10. 화면 — Documents 탭 패턴을 그대로 따른다

현재 `/wiki` 는 봇 개념이 없다(`frontend-admin/src/features/llm-wiki/`). 이번에 바꾼다.

**복제할 원본 3개 (전부 확인함)**

| 무엇 | 위치 |
|---|---|
| 봇 선택기 (컨트롤드 더미 컴포넌트, `useBots()` 만 호출) | `frontend-admin/src/features/documents/components/bot-selector.tsx` |
| botId 보관 — URL 아니고 **페이지의 `React.useState<number\|null>`** | `frontend-admin/src/app/(admin)/documents/page.tsx:56, 69, 74-77` |
| 쿼리 키 + `enabled` 게이트 | `features/documents/api.ts:12-15` · `hooks.ts:18-24` |

```ts
// api.ts:12-15 을 그대로 본뜬다
export const wikiKeys = {
  all: ["wiki"] as const,
  byBot: (botId: number) => [...wikiKeys.all, "bot", botId] as const,
}
// hooks.ts:18-24 — botId 없으면 아예 안 부른다
useQuery({ queryKey: wikiKeys.byBot(botId!), queryFn: () => fetchWiki(botId!), enabled: botId !== null })
```

glossary 브랜치의 `app/(admin)/glossary/page.tsx:11` 도 이 `BotSelector` 를 그대로 재사용한다 — 선례가 있다.

- 봇 전환 시 색인·페이지·모순·공백이 전부 갈린다.
- 위키가 없는 봇은 빈 상태 — "이 봇의 문서 N건으로 아직 위키를 만들지 않았습니다".
  생성은 CLI 이므로 화면에서는 **안내만** 한다(버튼으로 LLM 을 돌리지 않는다).
- 상단 지표에 봇 컨텍스트를 넣는다: `봇 11 · 문서 2건 → 위키 N쪽 · 모순 K · 공백 J`.
- 기존 유지: 문장↔원문 왕복(출처 표 클릭 → 우측 원문 전문), 역링크, 모순 3자 선택.
- ⚠ 선택은 새로고침 시 초기화된다(documents·faqs 도 동일). 그대로 간다 — 일관성이 우선이다.

### 곁가지 — `/ops-facts` 에 봇 선택기가 없다

`ops_facts` 는 서버에 `bot_id`·`scope` 파라미터가 다 있는데
(`admin/ops_facts.py:35-36`, `crud_ops_facts.py:45-66`) 화면이 안 쓴다 —
`features/ops-facts/components/ops-facts-board.tsx:47` 이 `useOpsFacts()` 를 인자 없이 부른다.
같은 봇 선택기를 붙이면 서버 기능이 그대로 열린다.

---

## 11. 챗봇 연결 (2차)

`wiki/pages/*.md` 를 Gemini File Search store 에 **봇 11 태그로** 올려 원문 청크 대신
큐레이션 페이지가 검색 대상이 되게 한다. **원문도 함께 남긴다** — 위키가 근거를 못 대면 폴백.
`handoff-glossary-repair-2026-08-05.md` §8 이 지적한 "확장어가 답변 프롬프트를 오염시킨다"를
위키 페이지는 검색 대상 청크라서 우회한다.

`ops_facts` 와는 **하류 관계**다. 위키에서 모순이 판정되면 그 결론이 ops_facts 한 줄이 되어
프롬프트에 실린다. 위키는 "왜 그런가", ops_facts 는 "그래서 뭐라 말할 것인가".

---

## 12. 함정 (물려본 것)

- **대사전 v4 블록 경계.** 안 닫으면 마지막 항목 body 가 300만자가 된다.
- **비싼 생성물은 배치마다 저장.** 18번째에서 터져 50분 날린 전례.
- **1회 실행으로 판정하지 않는다.** 잡음 바닥 20pp.
- **`backend/.env` 는 라이브 Neon 을 가리킨다.** 로컬은 `DATABASE_URL` 을 덮어쓴다.
  스크립트는 반드시 `backend/` 에서 실행한다(`env_file=".env"` 가 상대경로).
- **대사전 v4 사용 승인 미결.** 페이지마다 출처 문서를 태그해 불허 회신 시 골라 되돌릴 수 있게 한다.
- 실행 직전 `exports/glossary_repair_2026-08-05/_ragverify.py` 로 봇 11 문서 2건을 확인한다 —
  **이미 봇 11 전용으로 짜여 있다**(`:58` `bot_id == 11`, `:87-89` 로컬 sha256 ↔ 스토어
  `content_sha256` 대조). 대사전이 스토어에서 사라져 있던 전례가 있다.
- **같은 PDF 를 두 봇이 가지면 스토어에 두 벌 저장된다.** `content_sha256` 은 메타데이터일 뿐
  중복 제거에 안 쓰인다. 그래서 `sources/<sha8>/` 로 **우리 쪽에서** 한 벌만 두는 게 의미가 있다.
- **RAG 는 `metadata_filter="bot_id = N"` 정확일치라 NULL-전역을 표현할 수 없다**(`gemini.py:448`).
  전역 위키를 만들어도 챗봇에 못 먹인다 — 위키가 봇별이어야 하는 기술적 이유이기도 하다.

---

## 13. 다음 세션 재개 프롬프트

```text
docs/architecture/handoff-llm-wiki-2026-08-07.md 를 읽고 시작해줘.
저장소 규약은 루트 AGENTS.md 를 따른다(응답은 결론부터).

목표: 카파시 llm-wiki 패턴을 봇 11 에 실제로 돌려, 패턴이 이 도메인에서 작동하는지 판정한다.
지금까지는 설계와 화면 시안뿐이고 파이프라인 코드는 한 줄도 없다.

순서:
1. §8-0 — exports/glossary_repair_2026-08-05/_ragverify.py 로 봇 11 문서 2건과
   sha256 일치를 먼저 확인한다. 대사전이 스토어에서 사라져 있던 전례가 있다.
2. §3 디렉토리로 exports/wiki_2026-08/ 을 만들고 _split.py 를 쓴다.
   조문 분해는 exports/golden_2026-08/_corpus_build.py 를 재사용한다
   (조문 100개·결번 0·중복 0 검증이 이미 들어 있다).
3. §5 규칙 5개로 AGENTS.md 스키마를 쓴다. 출처 앵커 없는 문장 금지가 핵심이다.
4. **조문 5개만 스모크 ingest 하고 멈춰서 산출물을 나에게 보여줘라.**
   250건을 다 돌리기 전에 형식을 확인한다.
5. 승인 나면 전량 ingest (순차·resume-safe·배치마다 저장, 2~3.5시간 무인).
6. §7 판정 — 내가 이미 아는 모순 5건 중 1·2·4 를 파이프라인이 스스로 찾아내는가.
   0건이면 이 로드맵을 접는다.
7. _verify.py 인용 대조 100% → _load.py 로 DB 적재 → /wiki 화면을 실데이터로 교체.

주의:
- codex 샌드박스는 -s workspace-write, cwd 를 봇 폴더로 가둔다. 병렬 금지.
- 라이브 Neon 에 아직 아무것도 안 올라갔다. ops_facts 마이그레이션도 미반영이다.
- 1회 실행으로 판정하지 마라. 잡음 바닥 20pp.
```

---

## 14. 이번 세션의 미완 사항

- `/ops-facts` 는 로컬 검증 DB 에만 적용됐고 **라이브 Neon 은 `7c04bb6da692` 그대로다.**
  ops_facts 마이그레이션(`a1f6c30d84be`)도 아직 실서버 미반영. 사용자가 "로컬 먼저"를 택했다.
- 검증용 DB `nexus_ops_verify`(컨테이너 `nexus_clarification_db`)를 만들어 뒀다. 불필요하면 DROP.
  `docker exec nexus_clarification_db psql -U nexus_user -d postgres -c "DROP DATABASE nexus_ops_verify"`
- 백엔드(8080)·관리자(3100) dev 서버가 이 세션에서 떠 있다. 다음 세션은 새로 띄운다.
- `frontend-admin/src/features/llm-wiki/` 의 `wiki.ts` 페이지 본문 8쪽은 **내가 손으로 쓴 것**이다.
  raw 소스 22건은 코퍼스 대조 18/18 · 실측 4/4 로 진짜지만, 위키 문장·"상호참조 12건"·
  기록 탭의 ingest 로그는 구성한 것이다. 4번 단계에서 실제 산출물로 갈아끼운다.
- `docs/prototypes/ops-facts-2026-08-07/index.html` — 독립 시안(정오표). 실화면과 별개로 남겨 뒀다.
