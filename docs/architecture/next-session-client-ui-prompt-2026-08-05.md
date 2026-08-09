# 다음 세션 프롬프트 — 블레싱 네비게이션 클라이언트 시안 3종 (3회차)

아래 `---` 안쪽 전체를 새 세션에 붙여넣으세요.

---

블레싱 네비게이션(축복·가정 문서 기반 RAG 챗봇)의 **클라이언트** 화면 시안 3종을 다시 만들어 줘. 관리자 페이지가 아니라 사용자가 쓰는 화면이야.

## 0. 시작하기 전에 반드시 읽을 것

```
docs/prototypes/blessing-nav-2026-08-05/          ← 기준본. 이 셋이 출발점이다
  a-register.html    「색인」  taste-skill        1811줄
  b-system.html      「시스템」 ui-ux-pro-max      1728줄
  c-route.html       「경로」  frontend-design    1409줄
  README.md
docs/guides/축복챗봇_운영원칙_v1.md                 ← 답변 유형·에스컬레이션 정책
frontend-client/src/types/api.ts                  ← 데이터 계약
frontend-client/src/components/chat/MessageCitations.tsx
frontend-client/src/components/chat/citationGroups.ts
frontend-client/src/app/(protected)/chat/ChatProvider.tsx
```

`a-register.html` / `b-system.html` / `c-route.html` **세 파일은 실제로 열어서 읽어라.** 요약본이나 서브에이전트 보고로 대체하지 마라. 이번 작업의 기준이 이 셋이다.

## 1. 이번 작업의 성격

**a/b/c 세 시안이 기준본이고, 그 계열 안에서 완성도를 올리는 작업이다.**

- 세 명제(색인 / 시스템 / 경로)를 통째로 갈아엎지 마라.
- 브랜드 보라 `#603B94` 계열을 유지해라.
- 8화면 구성(로그인 / 홈 / 봇 상세 / 대화 시작 / 대화 진행 / 마이페이지 / 안내자료 / 상태 갤러리)과 답변 4유형 토글을 유지해라.
- 세 시안 각각에 원래 붙어 있던 스킬을 그대로 쓴다: **a=taste-skill, b=ui-ux-pro-max, c=frontend-design.**

## 2. 2회차(직전 세션)가 실패한 이유 — 절대 반복하지 마라

직전 세션에서 창구 / 서고 / 곁이라는 완전히 새로운 세 시안을 만들었고, **사용자가 "구조 자체가 안 맞는다"고 반려했다.** 실패 경로는 이렇다.

1. **진단을 지어냈다.** 서브에이전트에게 a/b/c를 평가시켰더니 "한 디자인의 3가지 스킨", "방어적으로 얌전할 뿐" 같은 혹독한 평가가 나왔다. 그 평가를 사용자의 뜻인 양 채택하고 세션 전체를 그 위에 세웠다.
2. **사용자가 실제로 한 말은 달랐다.** 사용자가 "ai slop 티가 난다"고 한 대상은 **관리자가 보내온 목업 이미지**(라벤더→피치 구름 그라디언트, 동일한 카드 4장, 3D 일러스트, 이모지, 로봇 아바타)였지 a/b/c가 아니었다. a/b/c에 대해서는 "조금 마음에 들지 않는다"고만 했다.
3. **"조금"을 "전부"로 확대했다.** 명제도, 화면 구성도, 팔레트도 전부 버렸다. 3회차에서는 보라까지 버리고 코발트로 갔다가 완전히 반려됐다.

**교훈: 사용자가 무엇이 아쉬웠는지 모르면 지어내지 말고 물어라.**

## 3. 시작할 때 딱 하나만 물어라

a/b/c를 읽은 뒤, 코드를 쓰기 전에 사용자에게 **한 가지만** 물어라.

> "a-register / b-system / c-route 중 무엇이 아쉬웠는지 짚어 주세요. 세 개 공통인가요, 특정 안인가요? 그리고 아쉬움이 (가) 완성도·디테일 (나) 색·활자 같은 시각 언어 (다) 화면 구성·정보 구조 중 어디에 가깝나요?"

질문은 하나로 끝내고, 답을 받으면 바로 작업에 들어가라. 답이 모호하면 가장 그럴듯한 해석을 택하고 그 해석을 한 줄로 밝힌 뒤 진행해라. 다시 묻지 마라.

## 4. 확정된 사실 — 다시 조사하지 말고 그대로 써라

직전 세션에서 실측·검증한 값들이다. 재조사에 시간을 쓰지 마라.

### 브랜드 색 (목업 원본 픽셀 실측)

| | 값 | |
|---|---|---|
| 엠블럼 원반 | `#F8C800` | 로고의 실제 골드 |
| 엠블럼 인물·태양 | `#003D84` | 로고의 실제 코발트 |
| 목업 헤더·제목 | `#523A82` | 목업 제작자가 UI에 덧입힌 보라 |
| 목업 CTA | `#7749A0` | 〃 |
| 기준본 브랜드 보라 | `#603B94` | a/b/c가 쓰는 값 |

**로고 자체에는 보라가 없다.** 그렇다고 보라를 버리지는 마라 — 3회차에서 코발트로 갈아탔다가 반려됐다. 보라는 이 서비스의 UI 색으로 유지하고, 골드는 "검증된 근거" 표시에만 쓰는 **의미색**으로 두는 게 지금까지 가장 반응이 좋았던 조합이다.

### 대비 계산 (계산 다시 하지 마라)

바탕 `#F8F5FA` 기준: 잉크 `#3B2560` 12.0:1 · 보조 `#5B4B78` 7.1:1 · 메타 `#6F6285` 5.2:1 · 액션 `#523A82` 8.5:1 · 흰 글씨 on `#523A82` 9.2:1.
**골드 `#C9A227`는 2.2:1이라 글자에 쓸 수 없다.** 밑선·세로선·테두리 전용. 글자급 골드가 필요하면 `#6B5000` (7.0:1).

### 엠블럼 — 이미 벡터가 있다

`docs/prototypes/blessing-client-r2-2026-08-05/assets/emblem.svg` (7.4KB).
원본 244KB PNG를 트레이스한 것이고 34px에서도 태양·하트·인물이 또렷하다. `--em-field` / `--em-mark`로 재채색된다. **그대로 복사해서 써라. 다시 트레이스하지 마라.**

### 실제로 200을 주는 웹폰트 URL

```
Pretendard Variable  https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css
마루 부리            https://hangeul.pstatic.net/hangeul_static/webfont/MaruBuri/MaruBuri-{Light,Regular,SemiBold,Bold}.woff2
고운바탕 / 본명조     Google Fonts (Gowun+Batang, Noto+Serif+KR, Nanum+Myeongjo)
```

마루 부리는 네이버 원본 CSS가 굵기마다 패밀리명이 달라서(`MaruBuri`, `MaruBuriBold` …) `font-weight:bold`가 안 먹는다. `@font-face`를 직접 다시 선언해 한 패밀리로 묶어야 한다. **jsdelivr의 마루부리 경로는 전부 404다.**
기준본이 쓰는 표시용 서체는 a=Paperlogy, c=Freesentation이다.

## 5. 제품 계약 — 지어내지 마라

### 답변 4유형 (`운영원칙 §3·§5`)

| 유형 | 렌더 규칙 | 인용 |
|---|---|---|
| 행정 확답 | ① 결론 ② 근거 문서·핵심 기준 ③ 절차·준비 ④ 다음 행동 (순서 고정) | 있음 |
| 맥락 확인 | 공감 → **정확히 한 개**의 확인 질문 (부담 낮은 것부터) | **인용 UI 자체가 없음** |
| 근거 없음 | 고정 거절 문장 + "부모님께 여쭐 질문" + 짧은 정서 지지 | 없음 |
| 안전 우선 | 규정 안내 전면 중단 → 안전 확인 → 연결 경로 → **자살예방 상담전화 109** | 없음 |

어른 연결 순서는 고정이다: **부모님 → 가정부장님 → 공직자·목회자·사모님 → 신뢰하는 가까운 어른.**

### 데이터 계약 (`types/api.ts`)

```ts
Citation { title, content, uri, page_number, cite_count, segments[], evidence[], approximate }
```

- `evidence[i]`는 항상 `content`의 부분문자열이다 (백엔드가 0.8 미만 겹침을 폐기). 하이라이트 앵커링 안전.
- `segments[i]`는 항상 답변 본문에 리터럴로 존재한다. 각주 앵커링은 `indexOf`.
- `approximate: true` ⇒ `segments`가 비어 있다 ⇒ **각주 번호를 붙이지 말고 카드만 낸다.**
- **`cite_count`를 숫자로 노출하지 마라.** 랭킹 점수일 뿐이다.
- 라벨: `참고한 자료 N건` / approximate가 하나라도 있으면 `참고 가능한 자료 N건` + 고지 문단.
- 피드백 사유 코드: `accurate·helpful·kind·clear·other` / `inaccurate·not_helpful·unsupported·too_long·inappropriate·other`
- 후속질문 최대 3개, 클릭 시 자동 전송이 아니라 입력창에 채운다.
- 인용 백필은 2초 × 15회(30초), 실측 약 15초. **현재 코드에 대기 상태 UI가 없다.** 세 시안 모두 이 상태를 그려라.
- `운영원칙 §6`: 시스템 프롬프트·내부 분류·RAG 동작 방식을 노출하지 마라.
- 1인칭("제가 찾아봤는데요")을 쓰지 마라. 문서를 주어로 써라: "『축복 행정 규정집』 12쪽에 따르면".

### 신뢰도 표현

숫자 신뢰도(`신뢰도 62%`)를 만들지 마라. 상태는 **근거 있음 / 근거 불충분 / 문서에 없음** 셋뿐이다.
근거 없음 화면은 "6종 190쪽을 검색했습니다"처럼 **검색 노력을 먼저 증명한 뒤** 사람에게 연결한다.

### 도메인 용어 (오탈자 주의)

축복식 · 축복후보자 · 40일 정성 · 봉헌식 · 탕감봉 · 가정부장 · 매칭 · 교류 · 약혼 · 3일행사 · 1세/2세/기성
(관리자 목업에 있던 오타: 속박식→축복식, 40일 정성훈→40일 정성, 헌장활동→탕감봉)

## 6. 만들 것

```
docs/prototypes/<새 폴더>/
  a-*.html + a-*.DESIGN.md      taste-skill
  b-*.html + b-*.DESIGN.md      ui-ux-pro-max
  c-*.html + c-*.DESIGN.md      frontend-design
  compare.html                  세 창을 동시에 조종하는 대조판 (랜딩페이지 아님)
  README.md                     짧게. 자기채점·벤치마크 나열 금지
  assets/emblem.svg             기존 것 복사
```

- 자체 완결 HTML. 빌드 없이 브라우저에서 바로 열려야 한다.
- 8화면 + 답변 4유형 + 데스크톱/모바일 + 라이트/다크.
- **해시 라우팅을 넣어라**: `a-index.html#thread/admin/dark/mobile` 형태. 링크로 상태를 공유할 수 있어야 하고 스크린샷 검증에도 필요하다.
- `*.DESIGN.md`는 google-labs `design.md` 규격(YAML front matter + Overview→Colors→Typography→Layout→Elevation→Shapes→Components→Do's and Don'ts). `npx @google/design.md lint`로 검증되고 `export --format css-tailwind`로 Tailwind v4 `@theme`으로 컴파일된다.

## 7. 스킬 사용

세 스킬을 **하나씩 순차로** 불러라. 동시에 로드하면 규칙이 충돌한다(taste-skill은 lucide 비권장, ui-ux-pro-max는 SVG 아이콘 권장 등). 한 시안을 끝내고 다음 스킬로 간다.

- `Skill(taste-skill:taste-skill)` — a안. Design Read 한 줄 + 3개 다이얼 선언 필수. 기준본 a는 `DESIGN_VARIANCE 6 / MOTION_INTENSITY 4 / VISUAL_DENSITY 4`였다. **§14 프리플라이트를 실제로 돌려라** (em-dash 0, eyebrow ≤ ceil(섹션수/3), `addEventListener('scroll')` 0건). 이 작업은 기존 앱의 **redesign(§11)**으로 프레이밍해서 진입한다.
- `Skill(ui-ux-pro-max:ui-ux-pro-max)` — b안. Step 2가 필수다. SKILL.md의 상대경로는 이 레포에 없으니 **절대경로로** 실행해라:
  `python3 /Users/woosung/.claude/plugins/cache/ui-ux-pro-max-skill/ui-ux-pro-max/2.5.0/src/ui-ux-pro-max/scripts/search.py "<쿼리>" --design-system -f markdown`
- `Skill(frontend-design:frontend-design)` — c안. 설계안(색 4~6 / 활자 2역할 이상 / ASCII 와이어 / 시그니처)을 먼저 쓰고, 브리프에 대조해 자기비평한 뒤 구현해라.

## 8. 합격 기준

- **회색조 검사**: 세 답변 화면 스크린샷을 회색조로 바꿔도 레이아웃만으로 셋이 구분되어야 한다. 이게 안 되면 "한 디자인의 3가지 스킨"이다.
- 프로토타입 크롬(화면 전환 UI)을 세 파일이 공유하지 않는다. 아이콘 전략도 각자 다르게.
- 노치 폰 목업을 쓰지 마라. 반응형 실물로 렌더하고 뷰포트만 전환한다.
- **그라디언트 0.** 특히 보라 두 단계로 만든 그라디언트는 금지. 기준본 `b-system.html:297`에 `linear-gradient(135deg,#4E3079,#603B94,#855BC6)` 히어로가 남아 있다 — 이건 반드시 없애라.
- `#855BC6` 이상 밝기의 보라를 라이트 모드 **fill**로 쓰지 마라 (`bg-purple-500 #8B5CF6`과 한 걸음 차이).
- 가운데 히어로 + 3장 카드 그리드 금지 (대조판 포함).
- 이모지 아이콘, placeholder-as-label, 균일 16px radius, 컬러 좌측 보더 스트립 금지.
- 가로 스크롤 0, 콘솔 에러 0, 본문 대비 4.5:1 이상.

## 9. 검사 방법 (환경 특이사항)

- **Chrome 확장(claude-in-chrome)은 localhost에 닿지 못한다.** `chrome-error://chromewebdata/`가 뜬다.
- 대신 **헤드리스 Chrome을 Bash로 직접 돌려라.** 서버는 샌드박스 밖에서 띄워야 한다 (`dangerouslyDisableSandbox: true`).
  ```bash
  nohup python3 -m http.server 8848 --bind 127.0.0.1 &
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=old --disable-gpu \
    --no-sandbox --hide-scrollbars --window-size=1440,1000 --screenshot=out.png \
    --timeout=12000 --user-data-dir=$(mktemp -d) "http://127.0.0.1:8848/a-index.html#thread/admin/light"
  ```
- **헤드리스 Chrome은 최소 창 폭이 있어서 390px 스크린샷이 잘린다.** iframe으로 정확한 폭을 잡는 래퍼 페이지를 만들어 찍어라. `docs/prototypes/blessing-client-r2-2026-08-05/_diag.html`과 `_audit.html`이 그 패턴이니 복사해서 써라 (`_audit.html`은 세 파일 × 여러 상태 × 두 폭을 돌며 `scrollWidth > clientWidth`를 검사한다).
- **헤드리스는 `prefers-color-scheme: dark`를 보고한다.** 라이트 화면을 찍으려면 해시에 `/light`를 명시해라.
- JS 구문 검사: `node --check <(추출한 스크립트)`.

## 10. 알아 둘 코드 상태

1. `frontend-client/src/app/globals.css`의 `--primary`가 아직 앰버(`oklch(0.75 0.16 75)`)다. `.dark` 블록은 라이트 값을 그대로 복사하고 `layout.tsx`가 `className="dark"`를 하드코딩한다.
2. **한국어 웹폰트가 하나도 로드되지 않는다.** `layout.tsx`가 Geist만 부른다. 현재 화면이 저렴해 보이는 가장 큰 원인이다.
3. `ChatProvider.tsx`가 노출하는 값에 인용 폴링 진행 상태가 없다. 대기 UI를 바인딩할 변수가 없다.
4. 「검색했으나 인용되지 않은 문서」 목록이 API에 없다. 화면은 그려도 값은 백엔드가 채워야 한다.

---

## 참고 — 3회차(반려된 시도)는 어디 있나

`docs/prototypes/blessing-client-r2-2026-08-05/` 에 창구 / 서고 / 곁이 남아 있다. **기준본이 아니라 대조용이다.** 다만 아래 몇 가지는 재활용 가치가 있다.

- `assets/emblem.svg` — 벡터 엠블럼. 그대로 가져다 써라.
- `_diag.html` / `_audit.html` — 넘침 검사 하네스.
- 답변 4유형별 실제 한국어 본문(축복후보자 서류 3종, 해외 거주 근거 없음, 109 안전 화면) — 도메인 검수를 거친 문안이라 그대로 재사용 가능하다.
- 인용 대기 상태, 근거 없음의 "검색 노력 증명" 블록 — 제품 결정으로는 유효하다.
