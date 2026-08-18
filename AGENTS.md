# AGENTS.md

이 저장소에서 AI 에이전트가 일할 때의 규약. 사람이 읽어도 되는 문서다.

---

## 1. 응답 형식 — 결론을 먼저 쓴다

**모든 응답은 결론과 간략 정리로 시작한다.** 과정·근거는 그 뒤에 둔다.

```
## 결론
<한두 문장. 무엇을 했고 무엇이 나왔는지.>

## 요약
| 항목 | 결과 |
|---|---|
| … | … |

## (이하 상세)
```

지킬 것:

- **긴 조사·실험 결과일수록 결론을 앞에 둔다.** 근거를 쌓아 올라가 마지막에 결론을 놓지 않는다.
- 표·불릿을 쓰되 **표 안에 문단을 넣지 않는다.** 길면 표 밖으로 뺀다.
- 숫자는 **분모와 함께** 쓴다. `6/20 (30%)` 이지 `30%` 가 아니다.
- 확정된 사실과 추정을 섞지 않는다. 추정이면 "추정"이라고 쓴다.
- **못 한 것·모르는 것을 결론 근처에 적는다.** 문서 끝에 묻지 않는다.
- 이모지로 구획을 나누지 않는다.

## 2. 작업 규율

- **요청 범위를 넘지 않는다.** 인접 코드를 "개선"하지 않는다. 변경한 줄은 전부 요청에 직접 대응해야 한다.
- 커밋·push·PR 생성은 **명시적으로 요청받았을 때만** 한다.
- `git status` 의 기존 dirty/untracked 항목은 다른 작업의 산출물일 수 있다. **수정·삭제·stage 하지 않는다.**
- 실측하지 않은 결과를 실측인 것처럼 쓰지 않는다. 호출에 실패했으면 실패했다고 보고한다.

---

## 3. 이 저장소를 건드리기 전에 알아야 할 것

아래는 2026-08-04 세션에서 **실측으로 확인한** 사실이다. 오래된 항목은 코드로 재확인할 것.

### 3-1. `backend/.env` 는 라이브 DB(Neon)를 가리킨다

```
DATABASE_URL=postgresql+asyncpg://…@ep-icy-wave-…neon.tech/neondb
```

로컬 DB 를 쓰려면 명령줄에서 `DATABASE_URL` 을 덮어써야 한다.
`app/core/config.py` 의 `env_file=".env"` 는 **상대경로**라 스크립트는 반드시 `backend/` 에서 실행한다.

```bash
cd backend && .venv/bin/python ../exports/<dir>/<script>.py
```

`.venv` 는 uv 관리(python 3.14, `google-genai` 2.10). `pip` 없음.

### 3-2. RAG 는 단일 Store + `bot_id` 메타데이터로만 갈린다

- Store 하나(`nexus-core-knowledge-base`)에 모든 봇 문서가 들어간다.
- 격리는 검색 시 `metadata_filter="bot_id = N"` 뿐이다.
- 업로드 시 붙는 `custom_metadata` 는 `bot_id`(numeric) + `content_sha256`(string) **둘뿐**.
- **`custom_metadata` 는 grounding 응답으로 회수된다** (94/94 실측). `page_number` 도 온다.
  `uri` 는 항상 `None`, `GroundingSupport.confidence_scores` 는 항상 비어 있다(검색 점수 없음).
- `content_sha256` 로 **문서 단위 검색 분리가 가능하다** — 재업로드 불필요.

### 3-3. 인용 0 ≠ RAG 미작동

**페르소나가 grounding "보고"를 억제한다. 길수록 심하다.**

| 봇 | system_prompt | 청크 0 보고 |
|---|---|---|
| 7 | 12,369자 | 40/40 (100%) |
| 11 | 2,387자 | 11/40 (28%) |

검색된 청크를 봐야 하는 조사는 **중립 프롬프트 팔을 따로 둬야 한다.** 페르소나 답변만 보고
"검색이 빈손"이라고 판정하면 틀린다.

### 3-4. Gemini free-tier 는 모델당 하루 500회

`GenerateRequestsPerDayPerProjectPerModel-FreeTier`. 한 모델이 막히면 다른 모델은 살아 있다.
장시간 실험 전에 모델별 잔량을 고려할 것.

### 3-5. 업로드 원본은 R2 에 있다 (단, 파일명으로는 못 찾는다)

`admin/bots.py` 가 Gemini 업로드 전에 원본을 R2 에 저장한다. 그러나
**키를 `uuid4().hex` 로 랜덤화하고 매핑을 DB 에 남기지 않는다**(문서 테이블 자체가 없음).

회수 방법: `list_documents` 의 `size_bytes` + Gemini `custom_metadata` 의 `content_sha256` 으로
버킷을 대조한다. 실제로 통한다(`exports/branch_ablation_2026-08-04/_glossary_etl.py` 주석 참조).

### 3-6. `exports/` — **스크립트는 추적되고 데이터는 안 된다**

조사·실험 스크립트는 여기 둔다(`exports/regression/`, `exports/branch_ablation_2026-08-04/`
가 선례). 2026-08-18 부터 `.py`·`.sh` 만 git 이 추적한다. 인계문서가 참조하는 명령이
다른 머신에서 안 돌던 문제 때문이다. 결과물(JSON·XLSX·HTML)과 레드팀 문항 원문·라이브
응답은 계속 빠진다.

⚠ **그래서 크리덴셜을 여기 박으면 이제 진짜로 커밋된다.** 예전에는 `/exports` ignore 가
우연히 막아 줬다 — 그 방어막은 없다.

```bash
git config core.hooksPath .githooks     # 머신마다 1회. 커밋 전에 검사한다
python3 scripts/scan_secrets.py         # 손으로 볼 때
```

라이브 DSN 이 필요하면 `exports/_neon.py` 의 `neon_url()` 을 써라. GitHub push protection
은 Gemini 키도 Neon 접속 문자열도 **못 잡는다**(둘 다 실측).

### 3-7. 채점·판정은 codex CLI 로

LLM 심사(채점·분류·의미판정)는 API 키 과금을 피해 구독 `codex exec` 를 쓴다.
**생성 모델과 판정 모델을 분리한다** — 자기 답을 자기가 채점하지 않는다.
선례: `exports/regression/_l3.py`, `exports/branch_ablation_2026-08-04/_branches.py`.

---

## 4. 라이브 자원을 건드리는 실험의 규율

- **읽기 전용을 기본으로 한다.** DB 는 `SELECT` 만. 실행 전후로 `messages`·`chat_sessions`
  카운트와 `bots.system_prompt` 해시를 대조해 증명한다.
- **`bots.system_prompt` 를 수정해 실험하지 않는다.** 프롬프트 변형은 스크립트 메모리에서만 조립한다.
- 운영 경로와 같은 조건인지 **해시로 확인**한다(예: A 팔의 `system_instruction` 이
  `bot.system_prompt + _FOLLOWUPS_INSTRUCTION` 과 바이트 단위로 같은지).
- 러너는 **resume-safe** 로 만든다. 호출마다 디스크에 쓰고, 재실행 시 성공분을 건너뛴다.
- 429/503 백오프와 throttle 을 넣는다.
- **같은 조건을 최소 2회 돌린다.** 1회 결과로 판정하지 않는다(비결정성이 크다).

---

## 5. 측정할 때 자주 틀리는 것

- **정규식으로 답변 구조를 세지 마라.** 모델이 `~인 경우:` / `### 1. 항목` / 표를 섞어 쓴다.
  실측으로 양방향 오차를 확인했다. 의미 기반 판정(codex)을 쓰고, 그것도 실행 간 변동이 있으니
  소수점이 아니라 방향만 읽는다.
- **대조군 없이 개입 효과를 주장하지 마라.** "B 에서 X 가 나왔다"는 A 기준선을 재기 전엔 의미가 없다.
- **RAG 파일명·본문에 NFD/NFC 가 섞여 있다.** 문자열 비교 전에
  `unicodedata.normalize("NFC", …)` 를 거치지 않으면 거짓음성이 난다.
- `pdftotext -layout` 은 숫자와 한글 사이에 공백을 넣는다("2 세가정 편성"). 별칭 매칭용
  문자열은 반드시 정규화한다.

---

## 6. 관련 문서

| 주제 | 위치 |
|---|---|
| 시스템 전체 구조·요청 여정 | `docs/architecture/system-overview-2026-08-04.md` |
| 조건부 분기 답변 문제 | `docs/architecture/conditional-answer-rag-proposal-2026-08-04.md` |
| 적응형 재질문 | `docs/architecture/adaptive-clarification-proposal-2026-08-04.md` |
| 분기 절제 실험 결과 | `exports/branch_ablation_2026-08-04/FINDINGS.md` |
| 회귀 하네스 | `exports/regression/` |
