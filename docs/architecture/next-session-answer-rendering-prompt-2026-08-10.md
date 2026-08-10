# 다음 세션 프롬프트 — 답변 렌더링 결함 2건 (되묻기와 무관, 라이브에 이미 보임)

> ## ✅ 완료됨 — PR #63 (`d0d01e1`), 2026-08-11
>
> **결과는 `handoff-clarify-live-2026-08-11.md` §1-2 를 읽어라.** 아래 프롬프트는 기록으로
> 남긴다. 다시 실행하지 마라.
>
> **아래 제목의 「라이브에 이미 보임」은 틀렸다.** 적용 전 실측 `0 / 2268`(assistant 메시지
> 전체) — 사용자에게 보인 적이 없다. 봇 11은 생애 발화가 1건이었고 나머지 봇은
> `file_search` 라 라벨을 주입하지 않는다. 이 작업은 사고 대응이 아니라 **예방**이었다.
>
> 또 아래 ①은 `[[src:` 만 이야기하지만, 실측하면 **가장 흔한 형태는 `[reg-66]`(125건)** 이고
> `[[src:` 는 23건뿐이다. `src|근거` 를 요구하는 정규식으로는 대부분을 놓친다.

> 아래 블록을 그대로 붙여 넣으면 된다. 되묻기 PR(#61)과 **섞지 마라** — 별건이다.

---

되묻기 브라우저 E2E(`docs/architecture/handoff-clarify-wired-2026-08-10.md` §4-7)에서
되묻기와 **무관한** 렌더링 결함 2건을 봤다. 둘 다 어휘 경로(`retrieval_mode='lexical'`)의
문제이고, **라이브 주력 봇 11이 `lexical` 이라 지금 사용자에게 보이고 있을 수 있다.**

## ① 답변 본문에 `[[src: reg-41]]` 마커가 그대로 노출된다

```
"... 축복자녀가정 편성 대상으로 확정되어야 합니다. [[src: reg-41]]"
"... 축도 기준을 확인해야 합니다. [[src: reg-43]], [[src: glo-2]]"
```

E2E 답변 1건에 11개. 내 변경 이전 냉동 기준선(`exports/wiki_eval/answers.json`)에도
40개 중 3개에 있다 — **기존 동작이다.**

### 먼저 알아야 할 것 — 마커는 지우면 안 되는 물건이다

봇 프롬프트(1,341자)에는 인용 형식 지시가 **하나도 없다**(`src`·`[[`·`인용`·`출처` 0건).
모델이 주입 원문의 `[reg-41] 규정집v20 제41조` 라벨을 보고 스스로 만들어 붙인다
(`wiki/service.py:69` 가 그 형식으로 주입한다).

그런데 **strict 게이트가 그 마커를 읽는다**:

```bash
cd backend && grep -n "def cited_ids" -A 4 app/services/strict_mode.py
grep -n "def has_grounded_citation" -A 15 app/services/strict_mode.py
```

`_strict_blocks` 는 어휘 경로에서 「답변에 남은 근거 표기를 주입 목록과 대조」한다(PR #59).
**마커를 안 나오게 만들면 strict 봇이 전부 차단된다.** 그러니 생성은 그대로 두고
**게이트를 통과한 뒤에 벗겨야 한다.**

### 순서가 함정이다

`chat_service.py` 비스트리밍 분기의 현재 순서:

```
1  _strict_blocks        ← 마커가 있어야 한다
2  되묻기 판정
3  빈답변·자기거절 게이트
4  apply_term_rules      ← 본문과 citations[].segments 를 같이 고친다
5  create_message        ← 저장되는 본문
6  _schedule_evidence_fill ← 답변 본문과 원문을 대조해 근거 구절을 채운다
```

- **1번보다 뒤여야 한다** — 앞이면 strict 봇이 죽는다
- **5번보다 앞이어야 한다** — DB 에 마커가 남으면 새로고침 때 다시 보인다
- **4번·6번과의 상호작용을 확인해라.** 프론트가 `citations[].segments` 를 본문에서
  **문자열 검색**해 각주를 앵커한다(`frontend-client/src/components/chat/citationMarkers.ts`).
  본문만 바꾸고 segments 를 안 맞추면 **각주가 전부 빠진다** — `apply_term_rules` 가
  이미 그 이유로 둘을 같이 고치고 있다(`chat_service.py` 주석 참조)
- **스트리밍 경로**(`_generate_rag_stream`·`_generate_strict_rag_stream`)도 봐라.
  지금 어휘 경로는 비스트리밍 전용이라 안 걸리지만, `file_search` 봇도 마커를 내는지
  확인해서 필요하면 같이 처리해라

### 검증

```bash
# 라이브에 실제로 노출되고 있는지 — 라이브 DB 는 읽기만 한다
#   messages.content 에 '[[src:' 가 있는 행 수를 봇별로 센다
# 로컬 재현: 봇 29 에 「2세 가정 12일 가정출발의식 절차가 뭐야?」
cd backend && uv run pytest -q                    # 기존 통과 수 유지
```
strict 봇 회귀가 핵심이다 — `tests/` 의 strict 게이트 테스트가 그대로 통과해야 한다.

## ② `1~3일` 이 취소선으로 렌더된다

```
원문:  "1~3일 정성, 4일째 의식, 5~11일 정성, 12일째 의식"
화면:  "1 ~~3일 정성, 4일째 의식, 5~~ 11일 정성, 12일째 의식"  (가운데가 취소선)
```

`remark-gfm` 의 `singleTilde` 가 기본 `true` 라 `~텍스트~` 를 취소선으로 읽는다.
**규정 본문에 물결표 범위 표기가 흔해서 자주 걸린다**(「1~3일」·「5~11일」·「만 17~19세」).

```bash
cd frontend-client && grep -n "remarkGfm" src/components/chat/ChatArea.tsx    # :344
grep -n "singleTilde" -A 12 node_modules/remark-gfm/readme.md                 # :226
```

가장 작은 고침은 옵션 하나다:

```tsx
remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
```

`~~취소선~~`(이중)은 그대로 살고 `~단일~`만 꺼진다. 확인할 것:
- **같은 마크다운을 쓰는 다른 화면**도 있는지 (`grep -rn "remarkGfm" frontend-client/src`).
  있으면 같이 고쳐야 화면마다 다르게 보이지 않는다
- 인용 각주 렌더(`rehypeCitationMarkers`)와 같이 쓰이는 자리라 회귀를 눈으로 볼 것

### 검증

```bash
cd frontend-client && npx tsc --noEmit && npm run build
```
그리고 브라우저에서 「2세 가정 12일 가정출발의식 절차가 뭐야?」를 물어
`1~3일 정성 … 5~11일 정성` 이 취소선 없이 나오는지 본다.
(로그인 절차는 인계 §4-6 에 있다 — 하나로 계정 없이 세션 JWT 를 직접 만든다)

## 제약

- **두 건을 한 PR 로 묶어도 되지만 되묻기 PR(#61)에는 넣지 마라.** 되묻기와 무관하고,
  CI 가 테스트를 안 돌리고 main push 가 곧 배포라 문제가 났을 때 원인을 못 가른다
- **①에서 마커 생성을 막지 마라.** strict 게이트가 그걸 읽는다
- **어휘 경로의 답변 생성(`answer_with_wiki`)을 다시 설계하지 마라.** 표시 문제다
- 이 둘 말고 다른 렌더링을 손보지 마라

레포는 `/Users/woosung/project/agy-project/nexus-core`, main 에서 새 브랜치를 딴다.
