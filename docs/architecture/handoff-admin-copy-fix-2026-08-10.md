# 인계 — 관리자 화면이 사실과 다르게 말하는 것 두 가지 (2026-08-10)

> **이 문서는 대화 요약이 아니라 「검증된 사실 목록」이다.**
> 모든 항목에 **확인 명령**을 붙였다. 다음 세션은 믿지 말고 다시 돌려서 확인하라.
> 명령은 레포 루트(`/Users/woosung/project/agy-project/nexus-core`)에서 실행한다.
> 확인 결과가 다르면 **그 사이에 코드가 바뀐 것이다. 문서가 아니라 코드를 따르라.**
>
> 짝 프롬프트: `next-session-admin-copy-prompt-2026-08-10.md`

---

## 0. 왜 이것만 따로 떼었나

관리자 화면을 직접 돌면서 설정마다 실제 동작을 측정했다. 화면이 주장하는 문장 **9개 중 4개가 거짓**이었다.
그중 **런타임을 하나도 안 건드리고 고칠 수 있는 두 가지**만 이 문서에 담는다.

나머지 둘(strict 게이트를 실제로 작동시키기, 되묻기 배선)은 **사용자에게 보이는 동작이 바뀌므로 별도 세션**이다.
같이 배포하면 문제가 생겼을 때 어느 쪽 때문인지 못 가른다 — CI 가 테스트를 안 돌리고 main push 가 곧 배포다.

**이 작업의 범위: 프론트엔드 문구와 상수뿐. 백엔드 0줄.**

---

## 1. 항목 ① — 프리셋에 적힌 지어냄율이 전부 낮다

`frontend-admin/src/features/bots/schemas.ts` 의 `RETRIEVAL_MODE_OPTIONS[].summary` 세 줄.

| 프리셋 | 화면 | 감사 정본 | 감사 키 |
|---|---|---|---|
| 정확 우선 (`file_search`) | 지어냄 **8.2%** | **14.2%** | `primary.rag.fab_rate` |
| 안전 우선 (`lexical`) | 지어냄 **2.7%** | **3.4%** | `primary.wiki_budget.fab_rate` |
| 균형 (`both`) | 지어냄 **11.2%** | **11.4%** | `primary.hybrid.fab_rate` |

**커버리지(57.9% · 40.2% · 50.4%)와 지연(7.0초 · 1.6초 · 6.1초)은 맞다. 지어냄율 셋만 틀렸다.**

```bash
python3 -c "
import json;p=json.load(open('exports/wiki_eval/audit_summary.json'))['primary']
print({k:p[k]['fab_rate'] for k in ('rag','wiki_budget','hybrid')})"
# → {'rag': 14.2, 'wiki_budget': 3.4, 'hybrid': 11.4}

grep -n "지어냄" frontend-admin/src/features/bots/schemas.ts
# → 95: 8.2% / 102: 2.7% / 109: 11.2%   (전부 낮다)
```

### 숫자만 바꾸면 또 낡는다

이 값들은 **25문항 표본**일 때 쓴 것이고, 45문항 정본으로 갱신될 때 화면이 안 따라왔다.
측정값이 코드에 하드코딩돼 있고 **갱신 트리거가 없다.**

`exports/` 는 gitignore 라 빌드 시 생성은 불가하다. 그래서 **측정 출처를 화면에 보이게** 한다 —
「45문항 · 2026-08」 같은 꼬리표가 붙어 있으면 낡았다는 것이 보인다.

45문항 정본 순위(`handoff-evidence-audit-45set-2026-08-10.md:35`):
`C 2.6 < B′ 3.4 < B 4.1 < F 11.4 < A 14.2` — **현 기본값(A)이 가장 많이 지어낸다.**

> ⚠ `note` 필드도 같이 봐야 한다. 「지어냄이 1/3 로 줄고」(:135)는 2.7/8.2 기준 문장이다.
> 정본(3.4/14.2)이면 **약 1/4** 이다. 숫자만 고치고 문장을 두면 또 어긋난다.

---

## 2. 항목 ② — 켜도 아무 일 없는 스위치가 켜지는 것처럼 보인다

### ②-A 맥락 보완 파일럿

`frontend-admin/src/features/bots/components/bot-edit-form.tsx:615-617`

> 현재 문구: **"모호한 요청에 선택형 추가 질문을 생성하는 실제 LLM 테스트를 이 봇에서만 허용합니다."**

**실측 — ON/OFF 결과가 완전히 같다.**

```
clarify_enabled=False → source=rag · RAG 호출 1회 · 선택지 0개
clarify_enabled=True  → source=rag · RAG 호출 1회 · 선택지 0개
```

```bash
grep -rn "clarify_enabled" backend/app/api backend/app/services
# → clarification_preview.py 두 줄뿐. chat_service 는 안 읽는다.
```

`clarify_enabled` 를 읽는 곳은 **미리보기 엔드포인트 하나뿐**이다.
바로 아래 「테스트하기」 칸에서는 동작하지만 **실제 사용자 대화에는 안 붙어 있다.**

### ②-B 추가 확인 질문 정책

`frontend-admin/src/features/bots/components/clarification-policy-section.tsx:361-393`
「필수 확인 질문 사용」·「새 규칙 만들기」도 같다 — 미리보기에서만 쓰인다.

라이브 실측: **봇 11개 중 `clarify_enabled=true` 0개 · 규칙이 있는 봇 0개.**

### ②-C Gems

`frontend-admin/src/app/(admin)/instructions/page.tsx:27`

> 현재 문구: **"Gem을 만들고, 그 Gem으로 시스템 프롬프트를 생성하고, 비교로 검증하세요."**

런타임은 `bot_instructions` 를 **읽지 않는다.** 만든 결과를
**봇 → 답변 설정 → 시스템 프롬프트에 직접 붙여넣어야** 반영된다.
화면만 보면 저장하면 적용될 것처럼 보인다.

```bash
grep -rn "BotInstruction\|instruction_service" backend/app/services/chat_service.py
# → 없음
```

---

## 3. 제약

- **백엔드를 건드리지 마라.** 이 작업은 프론트 문구·상수뿐이다.
- **기능을 붙이지 마라.** 파일럿을 실제로 배선하는 것은 별도 세션이다(§5).
- **라이브 DB 는 읽기만.** 이 작업엔 DB 접근 자체가 필요 없다.
- **`exports/` 를 빌드에 끌어들이지 마라.** gitignore 라 배포 이미지에 없다.
- 숫자를 바꿀 때 **`summary` 와 `note` 를 함께** 봐야 한다(§1 마지막 경고).

---

## 4. 확인

```bash
cd frontend-admin && pnpm lint && pnpm build     # 무결
cd backend && uv run pytest -q                   # 169 통과 (백엔드는 안 건드리므로 그대로)
```

화면 확인이 필요하면 로컬 스택을 띄운다. **라이브 관리자 화면은 저장·삭제 버튼이 있어 클릭하며 돌면 안 된다.**

```bash
cd backend && uv run uvicorn app.main:app --port 8099 &
cd frontend-admin && INTERNAL_API_URL=http://127.0.0.1:8099 \
  NEXT_PUBLIC_API_URL=http://127.0.0.1:8099 pnpm dev --port 3099 &
# 봇 29 = 라이브 D-1 ver2 복제본(프롬프트 1,341자 · lexical · 규정집v20+대사전v4)
open http://127.0.0.1:3099/bots/29/edit
```

> ⚠ **로컬과 라이브가 같은 `bots.id` 에 다른 봇을 담고 있다.**
> 로컬 11번은 `opus2_v4`(5,608자), 라이브 11번이 D-1 ver2(1,341자)다.
> 로컬 검증용 복제본이 **봇 29**로 만들어져 있다.

---

## 5. 이 세션에서 하지 않는 것

| | 왜 미루나 |
|---|---|
| **strict 게이트를 실제로 작동시키기** | 인용 표기를 강제하면 마커 출현율이 17% → **83%** 로 오르고 id 는 하나도 안 지어낸다는 실측이 있다. 다만 n=6 이라 작고, 강제 문구를 어디에 둘지(봇 프롬프트 vs 코드 오버레이)가 안 정해졌다 |
| **되묻기 배선** | **규칙이 있는 봇이 0개**라 지금 배선하면 되묻는 게 아니라 전부 `handoff`(담당자 안내)로 빠진다. 시드 규칙 4개는 겨냥한 문항이 오늘 실패한 5건(33·34·36·45·18)과 **하나도 안 겹친다** |

둘 다 **사용자에게 보이는 동작이 바뀐다.** 이 문서의 두 항목은 안 바뀐다 — 그래서 갈랐다.

상세: `handoff-unanswerable-built-2026-08-10.md` · 측정 전문은 `~/Desktop/관리자-설정-안내.pdf`
