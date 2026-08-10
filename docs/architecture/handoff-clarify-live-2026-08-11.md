# 인계 — 되묻기가 라이브에 켜졌다 · 렌더링 결함 2건 해소

> 검증된 사실 목록이다. 믿지 말고 확인 명령을 다시 돌려라. 값이 다르면 그 사이에 코드가
> 바뀐 것이고 **문서가 아니라 코드가 맞다.**
>
> 앞선 문서: `handoff-clarify-wired-2026-08-10.md`(배선) ·
> `next-session-answer-rendering-prompt-2026-08-10.md`(1단계) ·
> `next-session-clarify-live-prompt-2026-08-10.md`(2단계)
>
> 머지된 것: **PR #63**(`d0d01e1`) · **PR #64**(`9377865`)

---

## 0. 지금 라이브 상태

```bash
cd backend && uv run python - <<'PY'
import asyncio, asyncpg, re, pathlib, json
line=[l for l in pathlib.Path('.env').read_text().splitlines() if 'neon.tech' in l][0]
dsn=line.lstrip('#').strip().split('=',1)[1].strip().replace('postgresql+asyncpg://','postgresql://').replace('-pooler','')
dsn=re.sub(r'[?&]ssl(mode)?=[^&]*','',dsn)
async def main():
    c=await asyncpg.connect(dsn,timeout=30,ssl='require')
    for r in await c.fetch("select id,name,retrieval_mode,clarify_enabled,clarification_policy from bots order by id"):
        pol=r['clarification_policy']; pol=json.loads(pol) if isinstance(pol,str) else pol
        print(f"{r['id']:3d} {r['name'][:22]:24s} {r['retrieval_mode']:12s} clarify={r['clarify_enabled']} 규칙{len((pol or {}).get('rules',[]))}")
    await c.close()
asyncio.run(main())
PY
# 기대: 봇 11 만 lexical · clarify=True · 규칙 4개. 나머지 10봇은 file_search · False · 0
```

**켜진 것은 봇 11 하나다**(`테스트 봇 D-1 ver2` · `lexical` · 프롬프트 1,341자).
규칙 4개: `family-start-12day` · `family-start-pre-rite` · `child-first-gen-eligibility` ·
`b4u-tier`. `독신 축복` 은 앞 두 규칙에서 `unresolved` 로 남아 있다.

사용자 트래픽은 봇 3·5·6·7(전부 `file_search`)에 있고 **거기는 아무것도 안 바뀌었다.**

### 앞 문서의 전제 2개가 틀렸다 — 다시 하지 마라

1. **마이그레이션 `a1c7d3e9f204` 를 손으로 올릴 필요가 없었다.** 이미 올라가 있었다.
   배포 워크플로가 `backend/**` 푸시마다 `alembic upgrade head` 를 돌린다
   (`.github/workflows/deploy-backend.yml`, 이미지 빌드 → 마이그레이션 → 배포 순).
   PR #61 머지 배포가 이미 적용했다. → `handoff-clarify-wired` §0 선행조건 ①은 무효.
2. **`[[src:` 는 라이브 사용자에게 보인 적이 없다.** 적용 전 실측 `0 / 2268`
   (assistant 메시지 전체). 봇 11은 생애 발화가 1건이었고 나머지 봇은 `file_search` 라
   라벨을 주입하지 않는다. → 1단계는 사고 대응이 아니라 **예방**이었고 백필도 없었다.

---

## 1. 1단계 — 기계 id 를 화면에 내보내지 않는다 (PR #63)

모델이 주입 라벨(`[reg-41] 규정집v20 제41조`, `wiki/service.py:69`)을 흉내내 기계 id 를
본문에 남긴다. 봇 프롬프트에 인용 형식 지시는 **0건**이다 — 모델이 스스로 만든 것이다.

**생성을 막으면 안 된다.** strict 게이트가 그 표기를 주입 목록과 대조한다(`cited_ids` 는
`\b(?:reg|glo)-\d+\b` 를 답변 전체에서 찾는다). 그래서 **게이트 뒤 · `create_message` 앞**
에서 벗긴다. 순서를 바꾸면 정답이 `STRICT_EVIDENCE_MESSAGE` 로 치환된다 —
`tests/test_source_marker_strip.py::test_벗기기가_strict_게이트보다_앞이면_정답이_죽는다`
가 그걸 실행으로 남겼다.

```
app/services/strict_mode.py       strip_source_markers · strip_source_markers_from_citations
app/services/chat_service.py      되묻기 블록 뒤, 「1층. 결정론 게이트」 주석 앞
app/api/v1/endpoints/clarification_preview.py   관리자 미리보기도 같은 화면을 보여야 한다
```

### 지우는 것과 남기는 것 — 실측으로 정했다

냉동 기준선(`exports/wiki_eval/answers.json`, 답변 225블롭)의 형태별 실측:

| 형태 | 건수 | 처리 |
|---|---|---|
| `[reg-66]` · `[reg-65, reg-63]` | 125 | 지운다 |
| `[src: reg-69]` | 57 | 지운다 |
| `[[src: reg-66]]` | 23 | 지운다 |
| `[근거: reg-56]` · `[근거 규정: reg-41, reg-43, glo-2]` | 8+ | 지운다 |
| `(근거: reg-39, reg-40)` · `(근거: [glo-115], [reg-11])` · `([reg-39])` | 13 | 지운다 |
| **`(근거: 규정집v20 제71조, 표 2)`** | **20** | **남긴다** |

원칙은 **페이로드가 기계 id 뿐인 표기만 지운다.** 조문·항목 표기는 사람이 찾아볼 수 있는
정보이고, **strict 게이트도 그 형식을 `locator` 와 대조한다**(`_locator_keys`) — 지우면
게이트가 읽을 것이 줄고 과잉 거절이 늘어난다(그 형식이 22.5% → 5.0% 를 만든 것이다).

결과: **기계 id 243 → 6 (98% 제거) · 조문 표기 20 → 20 (100% 보존) · 구두점 잔여 0.**
남는 6건은 산문에 박힌 형태(`- 근거: 규정 reg-17, reg-33, glo-34`)뿐이라 **그냥 둔다** —
거기서 id 만 빼면 문장이 토막난다.

**`citations[].segments` 도 같이 벗긴다.** 프론트가 `content.indexOf(segment)` 로 각주를
앵커하므로(`citationMarkers.ts`) 본문만 벗기면 각주가 조용히 전부 빠진다.
`evidence` 는 원문 청크의 부분문자열이라 건드리지 않는다.

## 2. `1~3일` 이 취소선으로 렌더되던 것 (PR #63)

`frontend-client/src/components/chat/ChatArea.tsx:344` →
`remarkPlugins={[[remarkGfm, { singleTilde: false }]]}`.
**레포 전체에서 `remarkGfm` 사용처는 이 한 곳뿐이다**(`frontend-admin` 은 마크다운 렌더가
없다). 설치된 파서로 직접 확인한 mdast `delete` 노드:

| 옵션 | delete 노드 |
|---|---|
| 기본값 | `["3일 정성, 4일째 의식, 5", "취소선"]` ← 범위 표기가 취소선이 된다 |
| `singleTilde: false` | `["취소선"]` |

## 3. 판정 상한 12초 (PR #64) — 값을 임의로 바꾸지 마라

`judge_answerability` 의 except 는 `TimeoutError` 를 이미 받고 있었는데 **그걸 던지는 것이
없었다**(SDK 에 클라이언트 타임아웃 없음). 측정에서 한 호출이 **12분 46초** 매달렸다.

`clarification_trigger.JUDGE_TIMEOUT_SEC = 12.0`. 하네스 값 90초를 그대로 옮기면 안 된다 —
되묻기는 **사용자 응답 경로**다. 값은 측정 분포에서 골랐다
(`exports/clarify_eval/_run.log`, 판정 181회):

```
중앙 4.24s · p90 4.51s · p95 4.61s · 건강한 최대 5.6s
그 위가 절벽이다 — 61.8s · 149.8s · 766.2s (3건)
```

181회 중 178회가 5.6초 안에 끝난다. 절벽 위 3건은 느린 호출이 아니라 멈춘 것이다.
초과하면 `None` 을 돌려 **답변은 그대로 진행된다**(fail-open).
`test_상한은_사용자가_기다릴_수_있는_값이다` 가 5.6~15초 범위를 강제한다 — 90 을 넣으면 실패한다.

## 4. 라이브 적재는 관리자 화면으로 못 한다 (PR #64)

`validate_active_policy`(`schemas/clarification_policy.py`)가 활성 규칙마다 봇의
**File Search 스토어**에 있는 `document_id` 를 요구한다. 봇 11은 `lexical` 이라 스토어가
없다. 어휘 경로의 `decide()` 는 `document_refs` 를 읽지 않는다.

유일한 경로는 `scripts/load_clarification_policy.py` 이고, 라이브에는 **셋을 대야** 한다:

```bash
cd backend && LIVE=$(grep '^# DATABASE_URL=.*neon\.tech' .env | sed 's/^# DATABASE_URL=//' \
  | sed 's/postgresql+asyncpg:/postgresql:/;s/?ssl=require/?sslmode=require/;s/-pooler\././')

# 먼저 상태만 본다 (쓰지 않는다)
uv run python ../scripts/load_clarification_policy.py --dsn "$LIVE" --bot-id 11 \
  --live --expect-bot-name "테스트 봇 D-1 ver2" --dry-run

# 끄기
uv run python ../scripts/load_clarification_policy.py --dsn "$LIVE" --bot-id 11 \
  --live --expect-bot-name "테스트 봇 D-1 ver2" --disable
```

`--expect-bot-name` 이 필수인 이유: **로컬 11 = `opus2_v4`(5,608자), 라이브 11 =
`테스트 봇 D-1 ver2`(1,341자)** 로 같은 id 가 다른 봇이다. 이름이 다르면 아무것도 안 쓰고 죽는다.

---

## 5. 라이브 브라우저 실검증 (하나로 계정 없이 · 인증 안 끄고)

**인증을 끄지 마라.** 필요 없다. 로컬 `backend/.env` 의 `AUTH_JWT_SECRET` 이 **라이브와
같아서**, 로컬에서 발급한 토큰이 라이브에 그대로 통한다(JIT 프로비저닝이라 계정 불필요).

```bash
# 1. 토큰 (라이브에도 유효하다 — 확인: GET /api/v1/chats 가 200)
cd backend && uv run python -c "
from app.core.security import create_access_token
print(create_access_token(subject='e2e-tester', provider='hanaro', is_official=False)[0])"
# 2. Playwright 로 쿠키를 심는다
#    domain: nexus-core-sable.vercel.app · name: nexus_session · secure: true · sameSite: Lax
# 3. https://nexus-core-sable.vercel.app/chat/new/11
```

**확인된 것 전부 ✅** — 선택지 카드 5개 · 「독신 축복」(unresolved) 클릭 시 **재질의 POST
0건** + 「정리 중」 고정 문구 + 「답변 보기」 비활성 · 다른 선택지는 재답변 · 새로고침 후에도
카드 유지(`messages.clarification` 에 `status=ask` 저장) · 답변 4건 전부 기계 id 0건 · 취소선 0건.

**테스트 흔적을 라이브에 남겨 뒀다**(되묻기가 프로덕션에서 돈다는 유일한 증거):
`users.id=29`(`clerk_user_id='e2e-tester'` — 실사용자는 `hanaro:*` 형식) ·
`chat_sessions` 751·752 · 메시지 6건.
**실사용자 통계를 낼 때 `user_id <> 29` 로 걸러라.**

---

## 6. 함정

### 6-1. 「되물은 턴」을 `is not null` 로 세면 부풀려진다

`messages` 의 JSON 컬럼은 값이 없을 때 **SQL NULL 이 아니라 JSON `null`** 을 저장한다
(SQLAlchemy 가 Python `None` 을 그렇게 쓴다). 되묻기 때문에 생긴 것이 아니다 —
`citations`·`followups` 에 예전부터 1,771행씩 있다.

```
clarification   SQL NULL 4536 · JSON null    4 · 실값    2
citations       SQL NULL 1110 · JSON null 1771 · 실값 1661
followups       SQL NULL 1110 · JSON null 1771 · 실값 1661
```

```sql
-- 부풀려진다: 6
select count(*) from messages where clarification is not null;
-- 맞는 값: 2
select count(*) from messages where clarification is not null and clarification::text <> 'null';
```

컬럼 추가 시점 **전** 행은 SQL NULL, **후** 행은 JSON null 이라 둘 다 걸러야 한다.
고치려면 `JSON(none_as_null=True)` 인데 기존 3,542행 백필 판단이 따라온다. 읽기 쪽은
어느 쪽이든 `None` 으로 역직렬화돼 화면은 멀쩡하므로 급하지 않다.

### 6-2. 판정은 매칭 여부와 무관하게 매 턴 돈다

`clarify_enabled` 인 봇은 라운드0에 주입 원문이 있으면 **항상** 판정 LLM 을 부른다.
규칙이 안 맞아도 부른다. → 봇 11의 **모든 답변에 +4.2초**(중앙). 트래픽이 거의 없는 봇이라
감수했다. 트래픽 있는 봇에 켜기 전에 이 비용을 다시 계산해라.

### 6-3. 어휘 경로 답변에는 인라인 각주가 안 붙는다 (기존 동작)

`wiki/service._citations()` 가 `segments` 를 채우지 않는다(스키마 기본값 `[]`).
프론트는 `content.indexOf(segment)` 로 앵커하므로 어휘 답변에는 `[1]` 이 안 생긴다 —
「참고한 자료 N건」 목록만 나온다. **내 변경 탓이 아니다.** 각주 회귀를 확인하려면
`segments` 가 채워진 메시지로 봐야 한다(로컬에 픽스처 행을 넣어 확인했다).

### 6-4. 각주는 `<sup>` 이 아니라 `<button>` 이다

`ChatArea.tsx` 의 `components.sup` 이 `<sup>` 을 `<button title="참고한 자료 N번 보기">`
로 갈아 끼운다. `querySelectorAll("sup")` 으로 세면 **0개가 나와 거짓 실패**한다.
`button[title*='참고한 자료']` 로 세라.

### 6-5. Playwright MCP 프로파일은 다른 세션이 잠근다

`mcp-chrome-<hash>` 프로파일은 한 번에 한 세션만 쓴다. 다른 Claude 세션이 잡고 있으면
`Browser is already in use` 가 난다. **그 Chrome 을 죽이지 마라** — 자기 playwright 를
따로 띄우면 된다(`npm i playwright` + `npx playwright install chromium`).

### 6-6. Vercel 배포 확인은 청크 grep 으로 안 된다

`/login` 이 로드하는 청크에는 채팅 화면 코드가 없어서 `singleTilde` 를 grep 해도 안 나온다.
커밋의 deployment status 로 봐라:

```bash
gh api repos/woosung-dev/nexus-core/commits/<sha>/status --jq '.state, [.statuses[].context]'
# 기대: success · ["Vercel – nexus-core-admin", "Vercel – nexus-core"]
```

### 6-7. 배포가 마이그레이션을 자동으로 올린다

장점이자 함정이다. 백엔드를 건드리는 아무 PR 을 머지하면 **아직 올리고 싶지 않은
마이그레이션도 같이 올라간다.** 미완성 마이그레이션을 main 에 두지 마라.
그리고 **CI 는 테스트를 안 돌린다**(`pull_request` 트리거가 레포에 없다) — main 푸시가 곧
배포이므로 위험한 변경 둘을 같은 배포에 넣으면 원인을 못 가른다.

---

## 7. 확인

```bash
cd backend && uv run pytest -q                                   # 221 통과
cd backend && uv run pytest tests/test_strict_mode.py -q         # 11 통과 (게이트 무회귀)
cd backend && uv run pytest tests/test_source_marker_strip.py -q # 29 통과
cd frontend-client && pnpm exec tsc --noEmit && pnpm build       # 통과

curl -s https://nexus-core-447687906928.asia-northeast3.run.app/health   # {"status":"ok"}
```

기준선은 190 이었다 → 1단계 +29 → 2단계 +2 = **221**. **기존 테스트 수정 0건**이 핵심이다.

배포된 리비전: `nexus-core-00031-s8s`(`d0d01e1`) → `nexus-core-00034-ljw`(`9377865`).

**백업**: Neon 스냅샷 브랜치 `backup-2026-08-10-clarify-live`
(`br-shiny-butterfly-am970d0c`, compute 없음) + 로컬 덤프
`~/nexus-neon-backups/2026-08-10-clarify-live.dump`(4.2M, `pg_restore --list` 247객체 검증).

---

## 8. 다음

1. **`min_score` 재스윕** — `CLARIFICATION_MIN_SCORE=15` 는 n=6 스윕이고 그 6건이 실행마다
   흔들린다. `_run.py` 의 `MIN_SCORE` 와 **같아야** 한다
2. **#20(축복 편성 유형)을 5번째 규칙으로** — 슬롯 미정. 제4조·제40조
3. **나머지 슬롯에 `unresolved` 가 필요한지** — 규정집이 안 다루는 갈래는 지우지 말고
   표시해라. **어휘 카운트로는 공백을 못 찾는다**(「기성」 37건 · 「독신 축복」 17건으로
   멀쩡히 뜬다). 새 규칙·선택지를 넣을 때마다 codex 감사를 다시 돌려라
4. **되묻기용 라벨** — 무주장·지어냄 라벨은 재질문의 표적이 아니다(코퍼스 커버리지를
   재고 재질문은 질문 모호성을 고친다). 값어치를 말하려면 라벨을 사람이 만들어야 한다
5. **트래픽 있는 봇으로 확장하기 전에** §6-2 의 +4.2초를 다시 계산해라
