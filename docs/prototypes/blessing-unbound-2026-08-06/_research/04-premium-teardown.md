# 프리미엄 랜딩 코드 레벨 해부 (Premium Landing Teardown)

작성일 2026-08-06 · 대상 6곳 · **전량 1차 실측** (2차 자료 인용 없음)

---

## 0. 방법론과 신뢰도

두 경로로 교차 측정했다. 값이 어긋나면 **B(브라우저 실측)를 정본**으로 삼았다.

| 경로 | 방법 | 얻은 것 |
|---|---|---|
| **A. 정적** | Chrome UA로 HTML + CSS 번들 직접 curl 다운로드 | 토큰 **정의**(`--title-6-size` 같은 설계 의도), @font-face 실명, easing 원문, @keyframes |
| **B. 동적** | Playwright, 뷰포트 **1440×900**, `getComputedStyle` 전수 조사 | 실제 **렌더된** px/hex, 요소별 사용 **빈도**, 액센트 **면적** |

다운로드 실적 — 6곳 전부 200 OK, WAF 우회 불필요:

```
linear   HTML 1,266KB  CSS 52파일 248KB      vercel  HTML  619KB  CSS  4파일 945KB
stripe   HTML  635KB  CSS  5파일 466KB      raycast HTML  367KB  CSS 11파일 384KB
cursor   HTML  640KB  CSS  4파일 419KB      framer  HTML 2,177KB  (인라인 <style> 7블록)
```

CSS 총 76개 파일 약 2.5MB를 전부 파싱했다(Framer는 인라인 블록 추출). **2차 자료(디자인 토큰 아카이브, 해부 아티클)를 인용한 항목은 하나도 없다** — 모든 수치의 출처는 위 파일들과 브라우저 계산값이다.

**실측 실패 없음.** 다만 아래 4가지는 값을 읽을 때 감안할 것:

- **Stripe 히어로 h1 색**: `rgb(129,184,26)`으로 찍히는데 이건 애니메이션 그라디언트가 도는 중간값이다. 정지 상태 기준색은 자식 span에서 읽은 `#061b31`.
- **Cursor**: 한국어 로케일로 렌더되어 히어로 문구가 한글이다. 폰트 지표(CursorGothic/EB Garamond)와 색·간격은 로케일 무관하게 동일.
- **Stripe 일부 초기 측정치**는 뷰포트가 1044px로 잡힌 상태에서 나왔다. 1440px로 재측정해 반영했고, 반응형으로 달라지는 값(h1 48px 등)은 토큰의 반응형 사다리와 대조해 확인했다.
- **빈도수(N=)**: `document.querySelectorAll('*')` 상위 5,000개 노드 기준. 절대 개수가 아니라 **상대 비중** 지표로 읽어야 한다. 랜딩 하단까지 스크롤하지 않은 상태라 지연 로드 컴포넌트는 집계에서 빠져 있다.

---

## 1. 사이트별 해부

### 1-1. Linear — "무채색 원리주의"

**타이포**: `Inter Variable` (self-host, `InterVariable.woff2?v=4.1`) + `Berkeley Mono`.
`font-feature-settings: "cv01","ss03"` / `font-variation-settings: "opsz" auto` 상시 적용.

CSS 토큰에 타입 스케일이 **9단 명시**되어 있다 (`--title-1` ~ `--title-9`):

| 토큰 | size | weight | letter-spacing | line-height |
|---|---|---|---|---|
| title-9 | 72px | 590 | -0.022em (-1.58px) | 1.0 |
| title-8 | 64px | 590 | -0.022em (-1.41px) | 1.06 |
| title-7 | 56px | 590 | -0.022em (-1.23px) | 1.1 |
| title-6 | 48px | 590 | -0.022em (-1.06px) | 1.0 |
| title-5 | 40px | 590 | -0.022em (-0.88px) | 1.1 |
| title-4 | 32px | 590 | -0.022em (-0.70px) | 1.125 |
| title-3 | 24px | 590 | -0.012em (-0.29px) | 1.33 |
| title-2 | 20px | 590 | -0.012em (-0.24px) | 1.33 |
| title-1 | 17px | 590 | -0.012em (-0.20px) | 1.4 |
| text-large | 17px | 400 | 0 | 1.6 |
| text-regular | 15px | 400 | -0.011em | 1.6 |
| text-small | 14px | 400 | -0.013em | 1.5 |
| text-mini | 13px | 400 | -0.01em | 1.5 |
| text-micro | 12px | 400 | 0 | 1.4 |
| text-tiny | 10px | 400 | -0.015em | 1.5 |

웨이트 스케일이 **정수가 아니다**: `300 / 400 / 510 / 590 / 680`. "medium"이 500이 아니라 **510**, "semibold"가 600이 아니라 **590**. 가변폰트라 가능한 미세 조정이고, 실측 h1도 정확히 `font-weight: 510`으로 찍힌다.

**실측 히어로**: 64px / **w510** / `-1.408px` (-0.022em) / lh **64px (비율 1.000)** / `#f7f8f8`.
본문: 15px / w400 / -0.165px / lh 24px (1.6) / **`#8a8f98`** — 히어로 서브카피가 흰색이 아니라 **3단계 회색**이다.

**컬러** (다크가 정본):

```
bg-level-0  #08090a   bg-level-1  #0f1011   bg-level-2  #141516   bg-level-3  #191a1b
text-primary #f7f8f8  secondary #d0d6e0  tertiary #8a8f98  quaternary #62666d
accent #7170ff / brand-bg #5e6ad2
```

실측 텍스트 색 빈도: `#f7f8f8` 219 / `#62666d` 117 / `#8a8f98` 105 / `#d0d6e0` 97. **4단계를 실제로 다 쓴다.**

가장 많이 쓰인 큰 배경면은 불투명 회색이 아니라 **`rgba(255,255,255,0.02)` (N=17)** 였다. 표면 상승을 반투명 흰색 오버레이로 만든다.

**간격**: 섹션 상하 패딩 **128px 고정**(5개 연속 섹션 전부 `padding: 128px 0`). 콘텐츠 폭 **1344px**, 바깥 패딩 46px → 총 1436px. 산문 폭 `--prose-max-width: 624px`.

**표면**: 보더는 압도적으로 **`1px rgba(255,255,255,0.05)` (N=50)**, 다음이 `0.08` (N=19). 불투명 회색 보더(`#23252a`)는 6회뿐. radius `6/2/4/9999/12/8`. 헤더는 73px, 배경 투명 + `backdrop-filter: blur(20px)` + 하단 1px `rgba(255,255,255,0.08)`.

그림자 1위가 **`rgba(0,0,0,0.03) 0 1.2px 0 0` (N=31)** — 흐림 0의 1.2px 밑선. 그림자라기보다 광학적 받침이다.

**모션**: 지배 duration **.16s**, easing `--ease-out-quad: cubic-bezier(.25,.46,.45,.94)`. 토큰상 `quickTransition .1s / regularTransition .25s`. `prefers-reduced-motion` 블록 7개.

**히어로 구성**: h1이 상단 272px에서 시작, 폭 1282px **전폭 중앙 정렬**. 제품 스크린샷은 1416×768인데 **radius 0, border 0, shadow 0**. 대신 위에 그라디언트를 덮어 배경으로 녹인다:

```css
radial-gradient(52.53% 57.5% at 50% 100%, rgba(8,9,10,0) 0%, rgba(8,9,10,.5) 100%),
linear-gradient(#08090a 10%, #d0d6e0 100%)
```

마퀴에는 좌우 80px 페이드 마스크: `linear-gradient(to right, transparent 0, #000 80px, #000 calc(100% - 80px), transparent 100%)`.

---

### 1-2. Vercel — "극단적 트래킹"

**타이포**: `GeistSans` (가변, `Geist_Variable-s.woff2`, weight 100–900) + `Geist Mono` + 장식용 `GeistPixel{Square,Grid,Circle,Triangle,Line}`.
폴백이 정교하다 — `local(Arial)`에 `ascent-override:94.56%; descent-override:27.76%; size-adjust:106.28%`로 메트릭을 맞춰 FOUT 시 리플로우가 없다.

**CSS 토큰의 `text-heading-*` 스케일** — 크기·행간·자간·굵기를 **한 클래스에 5종 세트로** 묶어 둔다. 이 표가 Vercel 타이포의 전부다:

| class | size | line-height | (비율) | letter-spacing | ls/size |
|---|---|---|---|---|---|
| `text-heading-72` | 72px | 72px | **1.000** | -4.32px | **-0.060em** |
| `text-heading-64` | 64px | 64px | **1.000** | -3.84px | **-0.060em** |
| `text-heading-56` | 56px | 56px | **1.000** | -3.36px | **-0.060em** |
| `text-heading-48` | 48px | 56px | 1.167 | -2.88px | -0.060em |
| `text-heading-40` | 40px | 48px | 1.200 | -2.40px | -0.060em |
| `text-heading-32` | 32px | 40px | 1.250 | -1.28px | **-0.040em** |
| `text-heading-24` | 24px | 32px | 1.333 | -0.96px | **-0.040em** |
| `text-heading-20` | 20px | 26px | 1.300 | -0.40px | **-0.020em** |
| `text-heading-16` | 16px | 24px | 1.500 | -0.32px | -0.020em |
| `text-heading-14` | 14px | 20px | 1.429 | -0.28px | -0.020em |

**트래킹이 정확히 3단**: ≤20px → -0.02em, 24–32px → -0.04em, ≥40px → **-0.06em**. 행간은 **56px 이상에서 1.0으로 붕괴**한다.

본문 계열(`text-copy-*`)은 **letter-spacing을 아예 선언하지 않는다**(=0): 13/18px · 14/20 · 16/24 · 18/28 · **20/36(1.8)** · 24/36. 라벨(`text-label-*`)은 행간이 더 좁다: 12/16 · 13/16 · 14/20 · 16/20 · 18/20.

실측 렌더 빈도도 이를 확인해 준다 — `14px/400/ls0/lh1.43` **N=91**, `16px/400/lh1.5` N=41, `11px/500/**+0.018em**/lh1.82` N=9.

토큰에서 `--font-weight-semibold: 450`으로 **재정의하는 유틸리티**(`.[--font-weight-semibold:450]`)가 따로 있다. 리터럴 `font-weight:450`이 40회. h1은 w400, h2는 w450 — 디스플레이가 **볼드가 아니다**.

유동 타입 토큰도 15종 있다(전부 `vi` 단위, 360→1440px 기준):
`--text-fluid-32-64: clamp(2rem, -1.4286rem + 5.7143vi, 4rem)` 식.

**컬러**: 페이지 배경 `--ds-background-200: #fafafa` (**순백 아님**), 카드가 `--ds-background-100: #fff`.
색을 **4겹**(hex → `lab()` → `hsla()` → `oklch()`)으로 정의해 광색역까지 대응하고, 최신 브라우저에선 oklch 층이 최종 승자다.

라이트 그레이 램프 (`--ds-gray-*`):
```
100 #f2f2f2 · 200 #ebebeb · 300 #e6e6e6 · 400 #eaeaea(기본 보더) · 500 #c9c9c9
600 #a8a8a8 · 700 #8f8f8f(3차) · 800 #7d7d7d · 900 #4d4d4d(2차) · 1000 #171717(1차)
gray-alpha: 100 #0000000d · 200 #00000014 · 300 #0000001a · 500 #00000036 · 1000 #000000e8
border #ebebeb · accent(focus) --ds-blue-700 #0070f7
```
실사용 빈도: `gray-1000` color 201회 → `gray-900` 101회 → `gray-700` 31회. **2단계(#171717/#4d4d4d)가 대부분**이고 계층을 적게 쓴다.

**다크 모드는 배경이 순수 `#000`** (표면 `#0a0a0a`). 회색 배경을 쓰지 않는다. 텍스트는 `#ededed → #a0a0a0 → #8f8f8f`.
테마 전환은 `.dark` **클래스**로만 — `prefers-color-scheme` 토큰 블록은 아예 없다.

**간격**: `--geist-page-width: 1200px` / `--ds-page-width: 1400px`(+24 마진 = **1448px**). 실사용 max-width 1위는 **624px (16회)** — 본문 폭. `--article-max-width: 640px`, 그 외 `28~50ch` 계열.
spacing은 4px 베이스(`--geist-space:4px`, 2x 8 · 3x 12 · 4x 16 · 6x 24 · 8x 32 · 10x 40 · 16x 64 · 24x 96 · 32x 128 · 48x 192 · 64x 256).

**마케팅 그리드의 실제 섹션 여백** (Tailwind `py-24`(96px)보다 크다):
```
--grid-padding-y : 69px(모바일) / 120px(중간) / 135px(데스크톱)
--grid-padding-x : 24px         / 40px        / 48px
--cell-padding   : 24px         / 40px        / 48px
그리드 폭: clamp(368px, 100vw - 2*margin, 1080px)
--guide-width: 1px, --guide-color: --ds-gray-200~500
```

**표면**: radius **6px가 압도적 (N=46)**. `--geist-radius: 6px`(프로덕트) / `--geist-marketing-radius: 8px`(마케팅). Material 프리셋이 radius와 shadow를 **쌍으로** 묶는다 — `base/small/tooltip` 6px, `medium/large/menu/modal` 12px, `fullscreen` 16px.

그림자의 핵심은 **이중 링**이다:
```css
--ds-shadow-border-base:       0 0 0 1px #00000014;
--ds-shadow-background-border: 0 0 0 1px var(--ds-background-200);   /* #fafafa */
--ds-shadow-border: var(--ds-shadow-border-base), var(--ds-shadow-background-border);
--ds-shadow-medium: 0px 2px 2px #0000000a, 0px 8px 8px -8px #0000000a;
--ds-focus-ring:    0 0 0 2px var(--ds-background-100), 0 0 0 4px var(--ds-focus-color);
```
보더 대신 `box-shadow: 0 0 0 1px`으로 헤어라인을 그려 **레이아웃 시프트를 없앤다**. 다크에서는 링 알파를 `#ffffff25`로 올린다.

버튼 높이 **32px**(내비) / 40px(히어로), padding `0 6px`~`0 14px`, 14–16px/w500.

**모션**: `cubic-bezier(0.4,0,0.2,1)` 단일 지배. duration **0.1s (N=77)** / **0.15s (N=37)**. transition 대상이 `color, background-color, border-color`로 명시 열거 — `all`은 9회뿐. `prefers-reduced-motion` 11개.

**히어로**: h1 상단 328px. 비주얼은 **1080×720 `<canvas>`** (WebGL) — radius·shadow·border 전부 0. 아래 섹션의 제품 스크린샷(921×486 webp)도 **프레임 없음**.

---

### 1-3. Stripe — "웨이트 300의 세계"

**타이포**: `sohne-var` (Klim Type Foundry, 상용 · `font-weight: 1 1000` 가변 · `font-display: block`) + `SourceCodePro-Medium`.

**HDS 토큰의 결정적 사실 — 거의 모든 텍스트가 weight 300이다.**

```
--hds-font-heading-{xxl,xl,lg,md,sm,hero-*}-weight: 300
--hds-font-text-{xxl,xl,lg,md,sm,xs}-weight: 300
--hds-font-heading-xs-weight: 400   ← 유일한 예외
--fontWeightNormal: 300
```

실측 빈도 1위가 **`16px / w300` (N=118)**, 3위 `16px / w400` (N=45). 48px 히어로도 w300.

letter-spacing이 **크기별 4단**으로 설계됨:

| 역할 | size (desktop) | ls | lh |
|---|---|---|---|
| heading-xxl | 56px (→48→34 반응형) | **-0.025em** | 1.03 |
| heading-xl | 48px | -0.02em | 1.03–1.07 |
| heading-lg / hero | 32px | -0.02em | 1.07–1.2 |
| heading-md | 26px | -0.01em | 1.1–1.2 |
| heading-sm / xs | 18–22px / 16px | **0em** | 1.2–1.25 |
| text-md | 16px | 0em | 1.4 |
| text-xs | 12–14px | 0em | 1.4–1.45 |

**실측 히어로 (1440px)**: 48px / **w300** / -0.96px (-0.02em) / lh 55.2px (**1.15**).
히어로 리드 카피가 **32px / w300 / lh 1.10 / `#64748d`** — 부제가 다른 사이트 h2급이다.

**컬러 — 중립색이 중립이 아니다.** neutral 램프 전체가 **파랑 쪽으로 기울어** 있다:

```
neutral-0   #ffffff    neutral-25  #f8fafd    neutral-50  #e5edf5
neutral-100 #d4dee9    neutral-300 #95a4ba    neutral-500 #64748d
neutral-700 #3c4f69    neutral-800 #273951    neutral-900 #1a2c44
neutral-950 #11273e    neutral-975 #0d253d    neutral-990 #061b31  ← 본문 잉크
brand-600   #533afd (CTA)              border  #e5edf5
```

본문 잉크가 `#000`이 아니라 **`#061b31`(짙은 남색)**. 보더도 회색이 아니라 `#e5edf5`(푸른 회색).

**간격**: `--hds-space-core-*` 가 **4px 배수로 0→200px 전 구간** 정의(2,4,6,8,12,16,20,24,28,32,36,40,44,48,56,64,72,80,88,96,…,200). 컨테이너 **max-width 1266px** + 좌우 16px, 히어로 블록 패딩 `36px 16px`. 섹션 간 gap 32/48/64px.

**표면**: radius 토큰 `xs 2 / sm 4 / md 6 / lg 16 / xl 32 / round 99999`. 실측 4px(N=48)·6px(N=45)로 **작은 쪽에 집중**. 보더 두께 토큰이 `sm 1px / md 1.25px / lg 2px` — **1.25px**라는 중간값을 둔 곳은 여기뿐.

그림자에 **파란 기가 섞여 있다** (Stripe의 서명):

```css
0 16px 32px rgba(50,50,93,.12)                      /* hds-canary-ui-shadow */
0 30px 60px -50px rgba(0,0,0,.1), 0 30px 60px -10px rgba(50,50,93,.25)
0 20.187px 40.374px -20.187px rgba(0,0,0,.1)        /* agentic-box-shadow */
```

**모션**: easing `cubic-bezier(.25,1,.5,1)` **40회**로 지배(easeOutQuart 계열). 스크롤 리빌은 `transform .8s cubic-bezier(.165,.84,.44,1)` (N=46) + `clip-path .8s` 동일 easing (N=12), 이동거리 **translateY(24px) → 0**. `prefers-reduced-motion` 6개.

**히어로**: 1044×752 `<canvas>` (유명한 애니메이션 그라디언트 웨이브) + 폴백 `wave-fallback-desktop.png`. 배경 그라디언트가 전부 **radial**:
`radial-gradient(circle, #7f7dfc, #f44bcc 33%, #e5edf5 66%)`.

버튼 padding이 **비대칭**: `15.5px 24px 16.5px` — 폰트 베이스라인 기준 광학 중앙 정렬.

---

### 1-4. Raycast — "네이티브 앱 흉내" (예외 사례)

측정된 6곳 중 **유일하게 반대 방향으로 가는 사이트**라 비교 기준으로 가치가 있다.

**타이포**: `Inter`. h1 **64px / w600 / letter-spacing normal(0) / lh 1.10 / `#ffffff`**.

**본문 트래킹이 양수다** — 13px `+0.008em`, 14px `+0.014em`, 16px `+0.019em`, 20px `+0.010em`. Linear/Vercel과 정확히 반대.

**타입 스케일이 아예 없다.** `--font-size-*` 토큰이 0개고, 모든 크기가 컴포넌트 클래스에 **리터럴 px**로 박혀 있다. 크기 분포는 14px(105회) · 16px(65) · 13px(58) · 12px(58) · 20px(36) — 무게중심 14px.
웨이트는 **500이 기본값**(191회) > 600(56) > 400(52).

**컬러**: **다크 전용** (`color-scheme: dark`, 라이트 테마 블록 없음).
```
--grey-900 #07080a(배경) · 800 #0c0d0f · 700 #111214 · 600 #1b1c1e · 500 #2f3031
--grey-400 #434345 · 300 #6a6b6c · 200 #9c9c9d · 100 #cdcece · 50 #e6e6e6
--color-fg hsl(240,11%,96%) · fg-200 rgb(194,199,202) · fg-300 #78787c · fg-400 rgb(94,99,102)
액센트: blue hsl(202,100%,67%) · green hsl(151,59%,59%) · red hsl(0,100%,69%) · yellow hsl(43,100%,60%)
        각각 alpha 0.15 짝(`--color-*-transparent`)을 갖는다
```
실측 텍스트: `#ffffff` (N=287) → `#9c9c9d` → `rgba(255,255,255,.6)` → `#6a6b6c` → `#434345`. **hex 계열과 alpha 계열을 섞어 쓴다** (Linear는 한쪽으로 통일).

**간격 — 스케일이 비선형이다.** 8px 등차로 64px까지 가다가 그 위에서 튄다:
```
0 · 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 56 · 64 ‖ 80 · 96 · 112 · 168 · 224
                                                    (여기부터 섹션 스케일)
--container-width 1204px (xs 746 · sm 1064 · lg 1280) · --navbar-height 58|76px
섹션 padding: --paddingY 96px | 168px, --paddingX 16 | 24px
```

**표면**: radius에 **이름 있는 스케일**이 있다 — `--rounding-xs 4 / sm 6 / normal 8 / md 12 / lg 16 / xl 20 / xxl 24 / full 100%`. 실측 최빈값은 11px(N=159, macOS 아이콘 곡률)이고 토큰 기준으로는 md(37회)·sm(33회)가 1·2위.

서명 그림자는 **물리적 키캡 시뮬레이션** (실측 N=159):

```css
0 1.5px .5px 2.5px rgba(0,0,0,.4),
0 0 .5px 1px rgb(0,0,0),
inset 0 2px 1px 1px rgba(0,0,0,.25),
inset 0 1px 1px 1px rgba(255,255,255,.2)
```

핵심 기법은 **inset 림라이트** — 위쪽에 밝은 1px inset, 아래쪽에 어두운 inset. 최대 **9겹**까지 쌓은 것도 있다. 깊이 램프는 8겹:
```css
0 0 0 1px rgba(255,255,255,.1), 0 0 0 1.5px rgba(0,0,0,.1),
0 2.8px 2.2px rgba(0,0,0,.034), 0 6.7px 5.3px rgba(0,0,0,.048),
0 12.5px 10px rgba(0,0,0,.06),  0 22.3px 17.9px rgba(0,0,0,.072),
0 41.8px 33.4px rgba(0,0,0,.086), 0 100px 80px rgba(0,0,0,.12)
```
그리고 **따뜻한 색의 글로우**: `rgba(215,201,175,.05) 0 0 20px 5px` — 중성 검정이 아니라 크림/황토색 빛.

**⚠ 6곳 중 유일하게 노이즈 텍스처를 쓴다** (단 1곳, `.page_featureGridItem:after`):
```css
background-image: url("data:image/svg+xml,…<feTurbulence type='fractalNoise'
                   baseFrequency='3' numOctaves='3' stitchTiles='stitch'/>…");
background-blend-mode: overlay;  opacity: .07;
```
`baseFrequency=3`(매우 고운 입자) · `numOctaves=3` · overlay 블렌드 · **불투명도 0.07**. 노이즈를 쓸 거면 이 정도가 상한선이라는 참고치.

**그라디언트를 압도적으로 많이 쓴다**: linear 195 · radial 119 · conic 4. 카드 표면이 `radial-gradient(100% 100% at 50% 0, var(--grey-800) 0, var(--grey-700) 100%)` 식.
backdrop-filter도 20종(`blur(2px)`~`blur(60px)`).

**모션**: 기본 duration **.3s**(119회) — 6곳 중 가장 느리다. 하우스 커브 `cubic-bezier(.23,1,.32,1)` (21회). 오버슈트 커브 `cubic-bezier(.34,1.56,.64,1)`도 쓰고, **101스톱 `linear()` 스프링**(피크 1.0428 @40%)까지 CSS에 구워 넣었다. @keyframes **67개**. `all 0.3s ease` 같은 게으른 선언도 N=37.

보더 `1px rgba(255,255,255,.1)` (N=25), `.06` (N=14).

> **판단**: Raycast의 "프리미엄"은 편집 디자인의 절제가 아니라 **OS 네이티브 질감의 재현**에서 온다. 문서 기반 챗봇에는 이 노선을 권하지 않는다 — 무거운 다층 그림자와 양수 트래킹은 텍스트 밀도가 높은 화면에서 역효과다.

---

### 1-5. Cursor — "종이" (본 과제에 가장 가까움)

문서 기반 제품에 **직접 이식 가능한 유일한 사례**다.

**타이포**: 전부 자체·라이선스 폰트다 — `CursorGothic`(Regular/Italic/Bold/BoldItalic 4컷) + `cursorDisplay`(Medium 1컷) + **`Berkeley Mono`** + **`EB Garamond`**(70페이스).
루트 폰트사이즈가 **15px → 900px 이상에서 16px** — 전 스케일이 모바일에서 6.25% 축소된다.

`.type-*` 9단 스케일이 **크기·행간·자간을 잠가** 둔다. 자간이 완벽한 단조 광학 램프다:

| class | size | line-height | letter-spacing |
|---|---|---|---|
| `type-2xl` | **72px** | 1.10 | **-0.030em** |
| `type-xl` | 52px | 1.15 | -0.025em |
| `type-lg` | 36px | 1.20 | -0.020em |
| `type-md-lg` | 26px | 1.25 | -0.0125em |
| `type-md` | 22px | 1.30 | -0.005em |
| `type-md-sm` | 18px | 1.40 | — (0) |
| `type-base` | 16px | 1.50 | **+0.005em** |
| `type-sm` | 14px | 1.50 | **+0.010em** |
| `type-xs` | 12px | 1.50 | **+0.010em** |

72px `-0.03em` → 12px `+0.01em`까지 **한 번도 역전 없이** 내려온다. 행간도 1.1 → 1.5로 단조 증가. 6곳 중 가장 교과서적인 램프다.

실측 히어로는 `type-md-lg`(26px)로 **작고**, 리드가 `EB Garamond 17.28px / lh 1.35 / rgba(38,37,30,.55)`.
CursorGothic은 400·700만 실제 파일이 있고 **500/600은 합성**된다. 히어로 일부에 임의값 `font-[510]`도 보인다.

**컬러 — 양쪽 테마 모두 따뜻하다** (Raycast의 차가운 `#07080a`와 정반대):

| | 라이트 | 다크 |
|---|---|---|
| `--color-theme-bg` | **`#f7f7f4`** | **`#14120b`** |
| `--color-theme-fg` | **`#26251e`** | `#edecec` |
| card 램프 | `#f2f1ed → #f0efeb → #ebeae5 → #e6e5e0 → #e1e0db` | `#1b1913 → #1d1b15 → #201e18 → #26241e → #2b2923` |

`#f7f7f4`는 황록 기가 도는 오프화이트, `#26251e`는 올리브 브라운, `#14120b`는 따뜻한 갈흑. **어느 것도 중성이 아니다.**

**텍스트·보더 계층 전부를 `color-mix`로 파생시킨다** (8자리 hex 폴백 동반):
```css
--color-theme-text-sec:      color-mix(in oklab, var(--color-theme-fg) 60%, transparent);  /* #26251e99 */
--color-theme-text-mid:      … 50% …                                                       /* #26251e80 */
--color-theme-text-tertiary: … 40% …                                                       /* #26251e66 */
--color-theme-border-01:  2.5%   --color-theme-border-02: 10%(기본)   --color-theme-border-02-5: 20%
```
잉크 하나로 텍스트 4단 + 보더 5단 + 채움 8단이 전부 나온다. **테마를 바꿔도 두 hex만 갈면 끝난다.**

액센트 `#f54e00`(번트 오렌지)은 **라이트·다크 동일**. 시맨틱도 테마 불변(`#1f8a65` 성공 / `#cf2d56` 오류).

**간격 — 가로·세로에 서로 다른 스케일을 쓴다.** 6곳 중 유일하고, 문서형 제품에 가장 중요한 발견이다:

```css
--g: calc(10rem / 16)   /* 0.625rem = 10px — 가로 그리드 단위 */
  g0.25 2.5 · g0.5 5 · g0.75 7.5 · g1 10 · g1.25 12.5 · g1.5 15 · g2 20 · g2.5 25 · g3 30px

--v: calc(1rem * 1.4)   /* 22.4px = 본문 1행 — 세로 베이스라인 단위 */
  v1/12 1.867 · v2/12 3.733 · … · v10/12 18.667      ← 1행의 12분의 1 단위
  v1 22.4 · v1.25 28 · v1.5 33.6 · v2 44.8 · v2.5 56 · v3 67.2
  v4 89.6 · v4.5 100.8 · v5 112 · v6 134.4 · v8 179.2px
```

**세로 여백을 "본문 한 줄의 1/12" 단위로 양자화**해서 전체 페이지가 베이스라인 그리드에 올라탄다. 섹션 패딩도 토큰이다 — `v3`(67.2) · `v5`(112) · `v6`(134.4) · `v8`(179.2px).

컨테이너는 `--max-width-container: 1300px` 토큰 + 브레이크포인트 사다리(420/660/900/1140/1380/**1470px**). 좁은 산문은 `.container--narrow{max-width:648px}`, prose 측정치는 `48ch / 80ch / 96ch`.

버튼 패딩이 **em 기반이고 상하 비대칭**이다 — `.89em 1.45em .91em`. 폰트 베이스라인 광학 보정 (Stripe의 `15.5px/16.5px`와 같은 발상).

**표면**: radius 상한이 **8px**다 (`--radius-2xs 2 / xs 4 / sm 4 / md 8 / lg 8 / xl 12 / 2xl 16`, 실사용 1위 `--radius-sm` 54회). Raycast(24px)보다 훨씬 각지다. 중첩 보정 `calc(var(--radius-sm) - 2px)`도 쓴다.

그림자가 **거의 안 보인다**: `--shadow-flyout: 0 0 1rem #00000005, 0 0 .5rem #00000002` (2%·0.8% 검정). 보더 역할은 `--shadow-outline-theme: 0 0 0 1px var(--color-theme-border-02)`가 한다.
유일한 림라이트는 글래스 컴포넌트 한 곳이고, 거기 앰비언트가 **`#1f435b1f`(청회색 틴트)** — 중성 검정이 아니다.
backdrop-filter에 **`blur(.8cqw)` / `blur(2.2cqw)`** 컨테이너 쿼리 상대 단위를 쓴다(블러가 컴포넌트 폭에 비례).

**노이즈·그레인 0건.** 완전 평면.

**모션**: `--duration: .14s` — 6곳 중 **가장 빠르다**(Raycast .3s의 절반 이하). 커브는 5종뿐이고 **오버슈트가 하나도 없다**. 진입 이동거리가 **2~4px**로 극도로 작다:
```css
@keyframes fadeSlideUp { from{opacity:0;transform:translateY(2px)} to{opacity:1;transform:translateY(0)} }
@keyframes tilePopIn   { from{opacity:0;transform:scale(.7) translateY(3px)} to{…} }
```

---

### 1-6. Framer — "순흑 + 상용 디스플레이체"

**타이포**: 헤드라인이 Inter가 아니라 **`GT Walsheim Medium`** (Grilli Type, 상용). 본문은 `Inter Variable`.

히어로 h1: **54px** (≥1200px) / **42px** (810–1199) / **36px** (<810) / w500 / **-0.04em** / lh **1em** / `#fff` / `font-feature-settings: "ss02"`.

본문 프리셋의 특징 두 가지:

- **optical size 축을 실제 px과 분리**해서 쓴다 — 12px 본문에 `opsz 14` 또는 `opsz 24`, 24px 리드에 `opsz 18`. 크기가 아니라 **역할**로 옵티컬 등급을 고른다.
- **웨이트가 소수점 단위 중간값** — `wght 440 / 450 / 460 / 500 / 540`. 400도 600도 쓰지 않는다. CTA 라벨만 540으로 페이지에서 가장 무겁다.

`--framer-text-wrap: balance`가 13개 선언 중 12개 — **디스플레이 텍스트 균형 줄바꿈이 기본값**.

**컬러**: 배경 **`#000` 순흑**. 근검정 램프가 아래쪽에 촘촘하다:

```
#000 → #050505 → #080808 → #111 → #141414 → #171717 → #1a1a1a → #1d1d1d → #1f1f1f → #212121 → #242424 → #303030 …
```

**#000과 #242424 사이에 7단계**를 두고 그 위로는 성기다. 표면 작업 전부가 명도 하위 14% 구간에서 일어난다.

텍스트 `#fff` → `#fff9`(60%) → `#fff6`(40%) → `#fff3`(20%). 보더 `rgba(255,255,255,.10)` (N=84+26) / `#212121` (N=119). 액센트 `#09f`.

**간격**: 컨테이너 **max-width 1200px**, 히어로 패딩 `100px 20px 40px` (모바일 `60px 20px 20px`), 콘텐츠 스택 gap 25px, 헤더 gap 20px, 버튼 gap 10px — **5px 기반 스케일** (4px도 8px도 아님).

**표면**: radius 8px(컨트롤)·20px(카드)·15px(필). 보더 1px 891회, 0.5px 14회. 그림자 ramp의 **y:blur 비율이 1:1.6 고정** (40/64, 26/41.6, 12/19.2). 링 그림자 `0 0 0 1px rgba(255,255,255,.1)`.
**노이즈/그레인 0건** — 2.1MB 전체에 `feTurbulence`·`noise`·`grain` 없음.

**모션**: 등장 애니메이션이 **전부 opacity 전용**. Framer Motion 페이로드에서 `x/y/scale/rotate/skew`가 initial·animate 모두 0/1이다. 단일 스펙:

```js
{ type: "spring", duration: 0.4, bounce: 0.2, delay: 0 }
```

초기 opacity가 `0`이 아니라 **`0.001`** — 레이어 승격을 유지시키는 의도적 트릭.
CSS transition은 전 문서에 6개뿐이고 대상이 전부 `color`, easing은 `cubic-bezier(.44,0,.56,1)`.

> 참고: 프로덕션에 버그가 실려 있다 — 인라인 `border-radius: NaNpx` 35건, `radial-gradient(NaNpx …)` 14건, 정의되지 않은 `box-shadow: var(--9xgf7k)` 15건. 베껴 쓸 때 따라가지 않도록.

---

## 2. 실측 비교표

### 2-1. 타이포

| | Linear | Vercel | Stripe | Raycast | Cursor | Framer |
|---|---|---|---|---|---|---|
| 디스플레이 폰트 | Inter Variable | GeistSans | **Söhne** (상용) | Inter | **CursorGothic** (자체) | **GT Walsheim** (상용) |
| 본문 폰트 | Inter Variable | GeistSans | Söhne | Inter | CursorGothic | Inter Variable |
| 세리프 사용 | 없음 | 없음 | 없음 | (미정의 참조) | **EB Garamond (리드)** | 없음 |
| 모노 | Berkeley Mono | Geist Mono | Source Code Pro | JetBrains Mono | **Berkeley Mono** | Azeret Mono |
| 폰트 조달 | 오픈(Inter)+상용 | 자체(Geist) | **상용(Klim)** | 오픈(Inter) | **자체+상용** | **상용(Grilli)** |
| 최대 디스플레이 | 72px (`title-9`) | **72px** (`heading-72`) | 56px (`xxl`) | **168px** (serif hero) | 72px (`type-2xl`) | 54px |
| **실측 h1 size** | 64px | 64px | 48px | 64px | **26px** (`type-md-lg`) | 54px |
| **h1 weight** | **510** | **400** | **300** | 600 | **400** | 500 |
| **h1 tracking** | -0.022em | **-0.060em** | -0.020em | **0** (168px에선 -2px) | -0.0125em | -0.040em |
| **h1 line-height** | **1.00** | **1.00** | 1.15 | 1.10 | 1.25 | **1.00** |
| 본문 size/weight | 15px/400 | 14–16px/400 | 16px/**300** | 14px/**500** | 16px/400 | 15–18px/w450 |
| 본문 tracking | -0.011em | **0** | **0** | **+0.014em** | **+0.005em** | -0.1~-0.2px |
| 본문 line-height | **1.6** | 1.43–1.60 | **1.4** | 1.6 | 1.5 | 1.35–1.4 |
| 소형(11–12px) tracking | -0.015em | **+0.018em** | 0 | +0.008em | **+0.010em** | -0.1px |
| 웨이트 스케일 | 300/400/**510**/**590**/680 | 400/**450**/500/600 | **300**/400 | **500**(기본)/600/400 | 400/700 실파일, 500·600 합성 | **440/450/460/500/540** |
| 타입 스케일 존재 | 토큰 9단 | 토큰 10단 | 토큰 8단 | **없음 (리터럴 px)** | **토큰 9단** | 프리셋 10종 |
| 루트 font-size | 16px | 16px | 16px | 16px | **15px → 16px @900** | 16px |

### 2-2. 컬러

| | Linear | Vercel | Stripe | Raycast | Cursor | Framer |
|---|---|---|---|---|---|---|
| 모드 | 다크(라이트 있음) | **라이트+다크** | 라이트 | **다크 전용** | **라이트+다크** | 다크 |
| **페이지 배경** | `#08090a` | **`#fafafa`** / 다크 `#000` | `#ffffff` | `#07080a` | **`#f7f7f4`** / `#14120b` | **`#000000`** |
| 표면 1단 | `#0f1011` | `#ffffff` / `#0a0a0a` | `#f8fafd` | `#0c0d0f` | `#f2f1ed` / `#1b1913` | `#111` |
| 표면 상승 방식 | **`rgba(255,255,255,.02)`** | 불투명 | 불투명 | 불투명 램프 | 불투명 5단 램프 | 불투명 7단 램프 |
| 텍스트 1 | `#f7f8f8` | `#171717` / `#ededed` | **`#061b31`** | `hsl(240,11%,96%)` | **`#26251e`** / `#edecec` | `#ffffff` |
| 텍스트 2 | `#d0d6e0` | `#4d4d4d` / `#a0a0a0` | `#64748d` | `#9c9c9d` | ink **60%** | `#fff` 60% |
| 텍스트 3 | `#8a8f98` | `#8f8f8f` | `#95a4ba` | `#6a6b6c` | ink **50%** | `#fff` 40% |
| 텍스트 4 | `#62666d` | `#a8a8a8` | — | `#434345` | ink **40%** | `#fff` 20% |
| 계층 생성법 | 별도 hex | 별도 hex + alpha램프 | 별도 hex | 혼합 | **`color-mix(in oklab)`** | **흰색 alpha** |
| 보더 | `rgba(255,255,255,.05)` | `#ebebeb` / alpha `#00000014` | `#e5edf5` | `rgba(255,255,255,.1)` | ink **10%** | `rgba(255,255,255,.1)` |
| 액센트 | `#5e6ad2` | `#0070f7` | `#533afd` | `hsl(202,100%,67%)` | **`#f54e00`** (테마 불변) | `#0099ff` |
| **뷰포트 내 액센트 면적** | **≈0%** (보이는 유채색 0) | ≈0% (canvas 제외) | **0.95%** (CTA 2개뿐) | — | — | — |
| 중립색 색조 | 무채 | 완전 무채 | **청색 편향** | 약한 청색 | **온색 편향(양 테마)** | 무채 |
| 색공간 | hex | **hex→lab→hsl→oklch 4겹** | hex | hex/hsl + p3 | **oklab + lab 트윈** | hex |

### 2-3. 간격·리듬

| | Linear | Vercel | Stripe | Raycast | Cursor | Framer |
|---|---|---|---|---|---|---|
| 컨테이너 max-width | **1344** (+46 패딩) | **1448** (+24 패딩) | **1266** (+16 패딩) | **1204** | **1300** (사다리 →1470) | **1200** |
| 내부 산문 폭 | **624** (`--prose`) | **624** (최빈) / 640 | 818 | 840 (최빈) | **648** / 48ch | 722 (h1 박스) |
| 좌우 거터 | 46px | **24 / 40 / 48px** | 16px | 16 / 24px | 10px 그리드 | 20px |
| **섹션 상하 패딩** | **128 / 128** | **69 / 120 / 135** (그리드) | 36(히어로 블록) | **96 / 168** | **67.2 / 112 / 134.4 / 179.2** | **100 / 40** (히어로) |
| 섹션 간 gap | — | 20 / 24 | 32 / 48 / 64 | 24 / 32 | 22.4 배수 | 25 (콘텐츠) |
| 간격 스케일 기반 | 4px | 4px (`--geist-space`) | **4px, 0→200 전구간 토큰** | 8px (64 이후 비선형) | **가로 10px + 세로 22.4px 이중** | **5px** |
| 헤더 높이 | 73 (토큰 57/64/65/72) | 64 | — | 58 / 76 | 52 / 56 | — |
| 헤더 처리 | 투명 + blur(20px) | **불투명 `#fafafa`** | — | — | sticky-top 64 | — |

### 2-4. 표면

| | Linear | Vercel | Stripe | Raycast | Cursor | Framer |
|---|---|---|---|---|---|---|
| radius 최빈값 | **6px** | **6px** | **4px** | **11px** (토큰 12px) | **4px** | **8px** |
| radius 스케일 | 4/6/8/12/16/24/32/pill | **6**(제품)/**8**(마케팅)/12/16 | 2/4/6/16/32/pill | 4/6/8/12/16/20/**24** | 2/4/**8**/12/16 | 8/15/20/pill |
| radius 상한 | 32 | 16 | 32 | **24** | **8** (가장 각짐) | 20 |
| 보더 두께 | 1px (0.5px 소수) | 1px | **1 / 1.25 / 2px** | 1px (0.5px 소수) | 1px | 1px (0.5px 14회) |
| 보더 불투명도 | **5%** 흰색 | 불투명 `#ebebeb` + alpha 8% | 불투명 `#e5edf5` | **6~10%** 흰색 | **10%** 잉크 | **10%** 흰색 |
| 보더 구현 | `border` | **`box-shadow` 이중 링** | `border` | `border` | **`box-shadow` 링** | per-side 변수 |
| 대표 그림자 | `0 1.2px 0 rgba(0,0,0,.03)` | `0 2px 2px #0000000a, 0 8px 8px -8px #0000000a` | `0 16px 32px rgba(50,50,93,.12)` | **8~9겹 inset 림라이트** | `0 0 1rem #00000005` (거의 무형) | `0 40px 64px rgba(0,0,0,.2)` |
| 그림자 색조 | 무채 | 무채 | **청색(50,50,93)** | **온색 글로우(215,201,175)** | 청회색 `#1f435b1f` | 무채 |
| **노이즈/그레인** | 없음 | 없음 | 없음 | **있음 (1건)** `feTurbulence baseFrequency=3, opacity .07, overlay` | 없음 | 없음 |
| 그라디언트 수 | 소수 | 194 linear / 20 radial (대부분 마스크) | 25 (radial 위주) | **195 / 119 / conic 4** | **38 / 6 / 2** (최소) | 마스크 위주 |
| backdrop-filter | blur 4/8/20/24/32 | 없음 (반투명 배경색으로 대체) | — | **blur 2~60px, 20종** | blur 8/12/16 + **`cqw` 상대 단위** | blur 3/5 |

### 2-5. 모션

| | Linear | Vercel | Stripe | Raycast | Cursor | Framer |
|---|---|---|---|---|---|---|
| 지배 duration | **.16s** | **.1s / .15s** | .3s (+.8s 리빌) | **.3s** (가장 느림) | **.14s** (가장 빠름) | .15/.2/.3s |
| 지배 easing | `cubic-bezier(.25,.46,.45,.94)` | `cubic-bezier(.4,0,.2,1)` | `cubic-bezier(.25,1,.5,1)` | `cubic-bezier(.23,1,.32,1)` | `cubic-bezier(.4,0,.2,1)` | `cubic-bezier(.44,0,.56,1)` |
| easing 종류 수 | 18 (토큰) | **25+** | 10+ | **12 + 101스톱 `linear()` 스프링** | **5, 오버슈트 0** | 1 (+malformed 1) |
| 스크롤 리빌 | 없음 (정적) | opacity .3s | **transform .8s + clip-path .8s, translateY 24px** | 없음 (JS `--scroll-progress`) | 없음 | **spring .4s bounce .2, opacity 전용** |
| 진입 이동거리 | — | translateY 8px / 75% | **24px** | 전면 slide+scale | **2~4px** (가장 작음) | **0px** (opacity만) |
| @keyframes 수 | 30+ | **84** | 9 | **67** | 27 (절반이 제품 데모) | 5 |
| transition 대상 | 속성 명시 | **속성 명시** (`all`은 9회) | 속성 명시 | `all` 다수 (N=37) | 속성 명시 | `color`만 |
| **CSS 스크롤 타임라인** | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 |
| prefers-reduced-motion | 7블록 | **15블록** | 6블록 | — | — | — |

### 2-6. 히어로 구성

| | 헤드라인 처리 | 제품 비주얼 | 프레임·원근·마스크 |
|---|---|---|---|
| Linear | 64px 전폭 중앙, 상단 272px | 1416×768 정적 이미지 | **프레임 전무.** 그라디언트 2겹으로 배경에 용해 |
| Vercel | 64px, 상단 328px | 1080×720 `<canvas>` (WebGL) | **프레임 전무** |
| Stripe | 48px + **32px 리드** | 1044×752 `<canvas>` 웨이브 + PNG 폴백 | 배경 전면. radial 그라디언트 3색 |
| Raycast | 64px/w600 | 앱 스크린샷 | 다층 그림자 + 온색 글로우로 **띄움** |
| Cursor | **26px (작음)** + Garamond 리드 | — | `0 28px 70px` 큰 소프트 그림자 |
| Framer | 54px, 722px 박스 | — | 마스크 다수 (edge fade), 링 그림자 |

**공통점**: 6곳 중 어느 곳도 제품 스크린샷에 **브라우저 크롬(주소창 목업)을 씌우지 않았다.** Linear·Vercel은 테두리조차 없다.

---

## 3. 프리미엄의 공식 10가지

실측에서 **교차 검증된 것만** 적는다. 각 항목에 반례가 있으면 함께 적었다.

---

### ① 본문 잉크는 순검정이 아니라 #17~#3a 대역, 그리고 색조가 있다

| 사이트 | 본문 잉크 | 순검정 대비 |
|---|---|---|
| Vercel | `#171717` | +23 |
| Cursor | `#26251e` | +38, **올리브 편향** |
| Stripe | `#061b31` | **청색 편향** (L≈11%) |
| Linear (반전) | `#f7f8f8` | 순백 아님 (-8) |
| Framer | `#ffffff` | ← 유일한 순색 |

라이트 모드 3곳 중 **`#000`을 본문에 쓴 곳은 0곳**. 다크 모드 3곳 중 배경에 `#000`을 쓴 곳은 Framer 1곳뿐이고 Linear `#08090a`, Raycast `#07080a`다.

> **규칙**: 라이트 본문 `#171717`~`#26251e`, 다크 배경 `#07080a`~`#0f1011`. 순검정·순백은 잉크가 아니라 **극단값**으로 남겨 둔다.

---

### ② 배경은 순백이 아니라 니어화이트, 카드가 그 위에서 흰색으로 뜬다

Vercel `#fafafa` 위에 `#ffffff` 카드. Cursor `#f7f7f4` 위에 `#f2f1ed`. Stripe만 `#fff` 배경.

명도차가 **2%(250 vs 255)** 밖에 안 되는데도 카드가 뜬다. 그림자 없이 표면을 분리하는 가장 싼 방법이다.

> **규칙**: 배경 `#fafafa`(중성) 또는 `#f7f7f4`(온색), 카드 `#ffffff`. 차이 5 이하.

---

### ③ 트래킹은 상수가 아니라 **크기의 함수**다 — 작으면 +, 크면 −

가장 일관되게 나타난 규칙이다.

| size | Vercel | **Cursor** | Linear | Stripe | Framer |
|---|---|---|---|---|---|
| 12px | — | **+0.010em** | 0 | 0em | -0.1px |
| 14px | **0** | **+0.010em** | -0.013em | 0em | -0.01px |
| 16px | 0 (`copy`) / -0.02 (`heading`) | **+0.005em** | -0.011em | **0em** | -0.1px |
| 18px | 0 | **0** | -0.012em | 0em | -0.2px |
| 22–26px | -0.04em | **-0.005 → -0.0125em** | -0.012em | -0.01em | — |
| 32–36px | -0.04em | **-0.020em** | -0.022em | -0.02em | -0.04em |
| 48–52px | -0.06em | **-0.025em** | -0.022em | -0.02em | -0.04em |
| 64–72px | **-0.06em** | **-0.030em** | -0.022em | -0.025em | — |
| 11px | **+0.018em** | +0.0044em | -0.015em | 0em | — |

**Cursor가 가장 교과서적이다** — 72px `-0.03em`부터 12px `+0.01em`까지 한 번도 역전 없이 단조 감소한다. Vercel은 3단 계단(-0.02 / -0.04 / -0.06), Stripe는 4단, Linear는 2단(≤24px -0.012 / ≥32px -0.022)이다.

**네 곳 모두 이 곡선을 토큰 이름 안에 박아** 뒀다 — `--title-6-letter-spacing`(Linear), `--hds-font-heading-xxl-letterSpacing`(Stripe), `.text-heading-64`(Vercel), `.type-2xl`(Cursor). 크기와 자간이 **한 몸으로 묶여** 절대 분리되지 않는다.

행간도 같은 방향으로 움직인다 (Cursor: 1.1 → 1.15 → 1.2 → 1.25 → 1.3 → 1.4 → 1.5 단조 증가).

> **규칙**: ≤12px → `+0.01em`, 14–18px → `0`, 24–32px → `-0.02em`, ≥48px → `-0.03em`.
> 그리고 **size · letter-spacing · line-height를 한 토큰 세트로 묶어라.** 따로 두면 반드시 어긋난다.

---

### ④ 디스플레이 웨이트는 볼드가 아니다 — 300~510 구간

| 사이트 | h1 weight |
|---|---|
| Stripe | **300** |
| Vercel | **400** (h2는 450) |
| Cursor | **400** |
| Framer | 500 |
| Linear | **510** |
| Raycast | 600 ← 유일한 반례 |

600 이상은 6곳 중 1곳. Vercel은 아예 `--font-weight-semibold: 450`으로 **재정의**했고, Linear는 `510/590`이라는 **비정수 웨이트**를 쓴다.

큰 글씨는 크기 자체가 위계다. 거기에 웨이트까지 얹으면 **둔해진다**.

> **규칙**: 디스플레이 400–510. "굵게"가 필요하면 웨이트가 아니라 **크기와 색**으로 해결.

---

### ⑤ 디스플레이 line-height는 1.0, 본문은 1.5~1.6 — 중간이 없다

| | h1 lh | 본문 lh |
|---|---|---|
| Linear | **1.00** | **1.60** |
| Vercel | **1.00** | 1.43–1.60 |
| Framer | **1.00** | 1.35–1.40 |
| Stripe | 1.15 | 1.40 |
| Raycast | 1.10 | 1.60 |
| Cursor | 1.25 | 1.50 |

디스플레이 1.0–1.15, 본문 1.35–1.6. **1.2~1.3 구간이 비어 있다.** 큰 글씨를 "덩어리"로, 본문을 "흐름"으로 다루는 이분법.

> **규칙**: ≥40px → `line-height: 1.0~1.1`. 16px 본문 → `1.5~1.6`. 그 사이 크기만 1.25~1.35.

---

### ⑥ 텍스트 계층은 4단, 그리고 실제로 4단을 다 쓴다

Linear 실측 빈도: `#f7f8f8` 219 / `#62666d` 117 / `#8a8f98` 105 / `#d0d6e0` 97 — 네 계층이 **고르게** 나온다.
Cursor: 잉크 1개 + 92/60/50/40%. Framer: `#fff` + 80/60/40/20%.

핵심은 **히어로 서브카피가 1단계 색이 아니라는 것**. Linear는 3단계 `#8a8f98`, Stripe는 `#64748d`, Framer는 60% 흰색, Cursor는 55% 잉크.

생성 방식은 두 갈래다:

- **별도 hex 램프** — Linear / Vercel / Stripe. 각 단계를 손으로 고를 수 있어 색조 조정이 정밀하다.
- **단일 잉크 + alpha 파생** — Cursor / Framer. Cursor가 가장 정교하다:

```css
--color-theme-fg: #26251e;                                    /* 라이트 */
--color-theme-text-sec:      color-mix(in oklab, var(--color-theme-fg) 60%, transparent);
--color-theme-text-mid:      color-mix(in oklab, var(--color-theme-fg) 50%, transparent);
--color-theme-text-tertiary: color-mix(in oklab, var(--color-theme-fg) 40%, transparent);
--color-theme-border-02:     color-mix(in oklab, var(--color-theme-fg) 10%, transparent);
```

잉크 hex **하나**를 바꾸면 텍스트 4단 + 보더 5단 + 채움 8단이 전부 따라온다. 다크 테마 전환도 `--color-theme-fg`/`--color-theme-bg` 두 값 교체로 끝난다. `in oklab`으로 섞어야 중간 단계가 탁해지지 않는다.

> **규칙**: 4단 계층을 정의하고, **본문 기본값은 2단계**로 둔다. 1단계는 헤드라인과 강조에만.
> 관리 편의와 테마 전환을 고려하면 **`color-mix(in oklab, ink N%, transparent)` 방식**을 권한다. 구형 브라우저용 8자리 hex 폴백을 함께 적어 두면 된다(Cursor가 그렇게 한다).

---

### ⑦ 보더는 회색이 아니라 **불투명도 5~10%**, 두께는 1px 고정

| 사이트 | 최빈 보더 | N |
|---|---|---|
| Linear | `1px rgba(255,255,255,0.05)` | **50** |
| Raycast | `1px rgba(255,255,255,0.10)` | 25 |
| Framer | `1px rgba(255,255,255,0.10)` | 84+26 |
| Cursor | `1px ink/0.1` | 23 |
| Vercel | `1px #ebebeb` (불투명) | — |
| Stripe | `1px #e5edf5` (불투명) | — |

다크 4곳은 **전부 반투명**. Linear가 5%로 가장 옅다. 라이트 2곳도 불투명이지만 배경과 명도차가 5~20에 불과하다.

> **규칙**: 보더 `1px`, 색은 전경색의 **6~10% alpha**. `#333` 같은 고정 회색을 쓰면 배경이 바뀔 때 다 깨진다.

---

### ⑧ radius는 4~8px 한 값에 집중한다 — 스케일이 있어도 안 쓴다

| 사이트 | 최빈 radius | 점유 |
|---|---|---|
| Cursor | **4px** | N=71 (2위 pill 36) |
| Stripe | **4px** | N=48 (2위 6px 45) |
| Vercel | **6px** | N=46 (2위 8px 3) |
| Linear | **6px** | N=40 |
| Framer | **8px** | N=23 |
| Raycast | 11px | N=159 ← macOS 모방 |

Linear는 `4/6/8/12/16/24/32`를 정의해 놓고 실제로는 6px에 몰려 있다. **정의된 스케일 ≠ 사용되는 값.**

> **규칙**: 컨트롤 `6px`, 카드 `12px`, 칩·뱃지 `pill`. **3개면 충분**하다.

---

### ⑨ 액센트 컬러는 뷰포트의 **1% 미만**을 차지한다

직접 측정했다 (1440×900 첫 화면, 채도 >0.25인 불투명 배경면의 가시 면적 합):

| 사이트 | 유채색 면적 | 내역 |
|---|---|---|
| **Linear** | **≈0%** | 유채색 요소가 스크린리더용 skip 링크 하나뿐 (화면 밖) |
| **Stripe** | **0.95%** | CTA 버튼 2개 (`#533afd`) — 0.52% + 0.42% |
| Vercel | ≈0% | (canvas 내부 제외) |

Linear 히어로 첫 화면에는 **보이는 유채색이 단 하나도 없다.** Stripe도 1% 미만이고 그마저 전부 CTA다.

> **규칙**: 액센트는 **CTA·링크·포커스링에만**. 첫 화면 유채색 면적 목표 **1% 이하**.
> 브랜드 컬러로 섹션 배경을 칠하는 순간 프리미엄에서 멀어진다.

---

### ⑩ 모션은 100~200ms, 대상을 명시하고, 스크롤 연출은 opacity 위주

| 사이트 | 지배 duration | `all` 사용 |
|---|---|---|
| Vercel | **0.1s / 0.15s** | 9회 (속성 명시가 114회) |
| Cursor | **0.15s** | 3회 |
| Linear | **0.16s** | 없음 (속성 명시) |
| Framer | 0.15/0.2/0.3s | `color`만 |
| Stripe | 0.3s (리빌 0.8s) | 없음 |
| Raycast | 0.2/0.3s | **37회** ← 반례 |

스크롤 리빌은 두 진영:
- **Framer**: spring 0.4s / bounce 0.2, **opacity 전용** (transform 전부 0)
- **Stripe**: `transform .8s cubic-bezier(.165,.84,.44,1)`, **translateY 24px**
- **Linear**: 스크롤 리빌 **없음** (정적)

easing은 전부 **ease-out 계열**. `ease-in-out`이나 `ease`를 지배적으로 쓴 곳은 없다.

> **규칙**: 호버·상태 전환 **150ms / `cubic-bezier(0.4,0,0.2,1)`**. 진입 연출은 **opacity + translateY 최대 24px**, 400ms 이하. `transition: all` 금지. `prefers-reduced-motion` 필수(3곳 확인: 6·7·11블록).

---

### 보너스: 노이즈·그레인은 사실상 쓰지 않는다 (6곳 중 5곳 0건)

`feTurbulence` / `noise` / `grain` 검색 결과 — **Linear·Vercel·Stripe·Cursor·Framer는 0건**. Framer는 2.1MB 문서 전체에 한 건도 없다.

**유일한 예외가 Raycast**, 그것도 카드 하나(`.page_featureGridItem:after`)뿐이다:

```css
background-image: url("data:image/svg+xml,…<feTurbulence type='fractalNoise'
                   baseFrequency='3' numOctaves='3' stitchTiles='stitch'/>…");
background-blend-mode: overlay;
opacity: .07;               /* ← 7% */
```

즉 "쓰지 마라"가 아니라 **"쓴다면 baseFrequency 3(아주 고운 입자) · overlay 블렌드 · 불투명도 0.07 이하 · 페이지 전체가 아니라 카드 한 종류에만"** 이 실측된 상한선이다.

질감의 주된 출처는 텍스처가 아니라 ① **근검정 램프의 촘촘함**(Framer는 `#000`~`#242424` 사이에만 7단계), ② **반투명 헤어라인**, ③ **1px 그리드 가이드선**(Vercel `--guide-width:1px`)이다.

---

## 4. 문서 기반 멀티봇 챗봇 랜딩 이식 스펙

이 제품의 조건 — ① 인용·근거 표시가 핵심 UI, ② 텍스트 밀도가 높음, ③ 봇이 여러 개라 **구분은 필요하되 알록달록하면 안 됨**, ④ 한글 본문.

가장 가까운 참조는 **Cursor(종이 팔레트 + 세리프 리드)** 와 **Linear(4단 텍스트 계층 + 반투명 헤어라인)** 의 교배다.

---

### 4-1. 타입 스케일 1벌

한글은 라틴 대비 시각적 크기가 커서 **동일 px에서 더 크게 보이고**, 자간을 라틴만큼 조이면 자소가 뭉갠다. 위 실측 곡선에서 **음수 자간을 60~70%로 완화**해 적용했다.

```css
:root {
  /* ── 폰트 ───────────────────────────────────────── */
  --font-sans: "Pretendard Variable", Pretendard, -apple-system,
               BlinkMacSystemFont, system-ui, sans-serif;
  --font-serif: "RIDIBatang", "Nanum Myeongjo", Georgia, serif;  /* 인용문 전용 */
  --font-mono: "Berkeley Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

  /* ── 디스플레이: size·tracking·leading 3종 세트로 묶음 ── */
  --display-1-size: 56px;  --display-1-ls: -0.030em; --display-1-lh: 1.05; --display-1-wt: 450;
  --display-2-size: 40px;  --display-2-ls: -0.025em; --display-2-lh: 1.10; --display-2-wt: 450;
  --display-3-size: 30px;  --display-3-ls: -0.018em; --display-3-lh: 1.20; --display-3-wt: 500;

  /* ── 타이틀 ─────────────────────────────────────── */
  --title-1-size: 24px;    --title-1-ls: -0.012em;  --title-1-lh: 1.35;  --title-1-wt: 500;
  --title-2-size: 20px;    --title-2-ls: -0.008em;  --title-2-lh: 1.40;  --title-2-wt: 500;
  --title-3-size: 17px;    --title-3-ls: -0.005em;  --title-3-lh: 1.45;  --title-3-wt: 500;

  /* ── 본문 ───────────────────────────────────────── */
  --body-lg-size: 17px;    --body-lg-ls: 0;         --body-lg-lh: 1.65;  --body-lg-wt: 400;
  --body-size:    15px;    --body-ls:    0;         --body-lh:    1.70;  --body-wt:    400;
  --body-sm-size: 13px;    --body-sm-ls: +0.005em;  --body-sm-lh: 1.60;  --body-sm-wt: 400;

  /* ── 라벨·캡션 (인용 출처, 봇 이름, 메타) ─────────── */
  --label-size:   12px;    --label-ls:   +0.010em;  --label-lh:   1.45;  --label-wt:   500;
  --caption-size: 11px;    --caption-ls: +0.015em;  --caption-lh: 1.50;  --caption-wt: 500;
}
```

**사용 규칙 3가지**

1. **size와 ls·lh는 절대 분리하지 않는다.** Linear·Stripe가 토큰 이름에 묶어둔 이유. 유틸리티 클래스로 세트 배포:
   ```css
   .t-display-1 { font-size: var(--display-1-size); letter-spacing: var(--display-1-ls);
                  line-height: var(--display-1-lh); font-weight: var(--display-1-wt); }
   ```
2. **웨이트 상한 500.** 600·700은 쓰지 않는다 (실측 6곳 중 5곳이 ≤510). 강조는 색으로.
3. **본문 line-height 1.7.** 라틴 1.5~1.6보다 한 단계 넉넉하게 — 한글은 어센더/디센더가 없어 행간이 좁으면 답답하다. 문서 인용이 길게 붙는 제품이라 더 중요.

**세리프의 자리**: Cursor가 EB Garamond를 리드 카피에 쓴 것처럼, **RAG가 인용한 원문 블록**에만 `--font-serif`를 쓴다. "AI가 쓴 말"과 "문서에 적힌 말"을 폰트로 분리하면 인용 신뢰도가 시각적으로 올라간다. 남용 금지 — 인용 블록 **단 한 곳**.

---

### 4-2. 간격 스케일 1벌

Stripe식 4px 전구간 토큰을 기본으로 하되, **Cursor의 세로 베이스라인 그리드**를 함께 채택한다. 문서 인용이 길게 이어지는 제품이라 세로 리듬이 어긋나면 바로 티가 난다.

```css
:root {
  /* ── 가로: 4px 기반 ──────────────────────────────── */
  --sp-1:  4px;   --sp-2:  8px;   --sp-3:  12px;  --sp-4:  16px;
  --sp-5:  20px;  --sp-6:  24px;  --sp-8:  32px;  --sp-10: 40px;
  --sp-12: 48px;  --sp-16: 64px;  --sp-20: 80px;  --sp-24: 96px;

  /* ── 세로: 본문 1행 = 25.5px 를 단위로 (Cursor 방식) ── */
  --v: calc(1rem * 1.7);          /* 15px 본문 × lh 1.7 ≈ 25.5px */
  --v-half:  calc(var(--v) * 0.5);   /* 12.75px */
  --v-1:     var(--v);               /* 25.5px  — 문단 간격 */
  --v-2:     calc(var(--v) * 2);     /* 51px    — 블록 간격 */
  --v-3:     calc(var(--v) * 3);     /* 76.5px  — 모바일 섹션 */
  --v-4:     calc(var(--v) * 4);     /* 102px   — 태블릿 섹션 */
  --v-4-5:   calc(var(--v) * 4.5);   /* 114.75px — 데스크톱 섹션 */
  --v-6:     calc(var(--v) * 6);     /* 153px   — 대형 구획 */

  /* ── 레이아웃 ───────────────────────────────────── */
  --container:      1200px;   /* Framer 1200 · Stripe 1266 · Cursor 1300 하단 */
  --container-wide: 1360px;   /* 봇 카드 그리드 등 넓게 쓸 때 */
  --prose:          660px;    /* Cursor 648 · Vercel 624 · Linear 624 */
  --gutter:         24px;     /* 데스크톱 (모바일 20px) */

  /* ── 섹션 리듬 ──────────────────────────────────── */
  --section-y:      var(--v-4-5);  /* ≈115px 데스크톱 */
  --section-y-sm:   var(--v-3);    /* ≈77px  태블릿 */
  --section-y-xs:   var(--v-2);    /* ≈51px  모바일 */
  --stack-gap:      var(--sp-6);   /* 헤드라인↔리드 24px */
}
```

**여백 밀도의 수치 기준** (실측 대비 이 제품의 목표):

| 항목 | 실측 범위 | 채택값 | 근거 |
|---|---|---|---|
| 섹션 상하 | 67~179px (Cursor) · 69~135 (Vercel) · 128 (Linear) | **≈115px** (`v×4.5`) | Linear 128은 순수 마케팅용. 정보 밀도 있는 제품엔 이쪽 |
| 컨테이너 | 1200~1448px | **1200px** | 좁을수록 편집적. Framer·Stripe 라인 |
| 산문 폭 | 624~660px | **660px** | 한글 15px 기준 약 45자/줄 |
| 헤드라인↔리드 | 20~25px | **24px** | Framer 25 · 일반 24 |
| 거터 | 16~48px | **24px** | Vercel 24 (데스크톱 48까지 확장 가능) |
| 문단 간격 | — | **25.5px** (`v×1`) | 본문 1행과 정확히 일치 |

**왜 세로만 따로 두는가**: Cursor는 세로 여백을 "본문 한 줄의 1/12" 단위로 양자화해서 페이지 전체를 베이스라인 그리드에 올린다. 인용 블록·응답 카드·각주가 반복적으로 쌓이는 화면에서 이게 있으면 **스크롤할 때 리듬이 흔들리지 않는다.** 4px 그리드만 쓰면 24px과 25.5px이 섞이면서 미세하게 어긋난다.

---

### 4-3. 표면 처리 규칙

```css
:root {
  /* ── 배경 (라이트 = 종이) ────────────────────────── */
  --bg-page:      #faf9f7;   /* 온색 니어화이트 — Cursor #f7f7f4 계열 */
  --bg-surface:   #ffffff;   /* 카드 = 순백으로 띄움 (공식 ②) */
  --bg-sunken:    #f4f2ef;   /* 인용문·코드 블록 */
  --bg-hover:     rgba(28,27,24,0.035);

  /* ── 잉크 + color-mix 파생 (공식 ⑥ 후자 방식) ────── */
  --ink:          #1c1b18;               /* 온색 근검정 — Cursor #26251e 계열 */
  --text-1:       var(--ink);                                        /* 헤드라인 */
  --text-2:       color-mix(in oklab, var(--ink) 72%, transparent);  /* 본문 기본값 */
  --text-3:       color-mix(in oklab, var(--ink) 54%, transparent);  /* 보조·메타 */
  --text-4:       color-mix(in oklab, var(--ink) 38%, transparent);  /* 비활성 */

  /* ── 보더: 전부 잉크 파생 (공식 ⑦) ──────────────── */
  --border:        color-mix(in oklab, var(--ink)  9%, transparent);
  --border-strong: color-mix(in oklab, var(--ink) 16%, transparent);
  --border-faint:  color-mix(in oklab, var(--ink)  5%, transparent);

  /* ── radius: 3개만 (공식 ⑧) ─────────────────────── */
  --r-control: 6px;
  --r-card:    12px;
  --r-pill:    999px;

  /* ── 그림자: 2단만 ──────────────────────────────── */
  --shadow-rest:  0 1px 2px rgba(28,27,24,0.04),
                  0 0 0 1px rgba(28,27,24,0.05);
  --shadow-lift:  0 8px 24px -6px rgba(28,27,24,0.10),
                  0 2px 6px  -2px rgba(28,27,24,0.06),
                  0 0 0 1px rgba(28,27,24,0.05);

  /* ── 액센트: 1% 규칙 (공식 ⑨) ───────────────────── */
  --accent:       #4338ca;
  --accent-hover: #3730a3;
  --accent-tint:  rgba(67,56,202,0.08);   /* 인용 하이라이트 배경 */

  /* ── 모션 (공식 ⑩) ──────────────────────────────── */
  --ease:      cubic-bezier(0.4, 0, 0.2, 1);
  --ease-out:  cubic-bezier(0.25, 1, 0.5, 1);
  --dur-fast:  120ms;
  --dur:       160ms;
  --dur-enter: 400ms;
}
```

**다크 테마는 두 값만 갈면 된다** (Cursor 방식의 실질적 이점):

```css
[data-theme="dark"] {
  --ink:        #ece9e3;   /* 온색 근백색 */
  --bg-page:    #14120b;   /* 온색 갈흑 — Cursor와 동일 계열 */
  --bg-surface: #1b1913;
  --bg-sunken:  #201e18;
  /* --text-*, --border-* 는 --ink 파생이라 자동으로 따라온다 */
}
```

`color-mix` 미지원 환경 대비가 필요하면 각 토큰 아래에 8자리 hex 폴백을 붙인다 (`--text-2: #1c1b18b8;`를 먼저 쓰고 그 뒤에 `color-mix` 선언). Cursor가 정확히 이 패턴을 쓴다.

**적용 규칙 6가지**

1. **그림자는 2단 이상 만들지 않는다.** `rest`(정지)와 `lift`(호버·모달)뿐. 두 값 모두 마지막 레이어에 `0 0 0 1px` 헤어라인 링을 포함해 보더와 그림자를 한 몸으로 붙인다(Framer·Raycast 공통 기법).
2. **액센트 면적 1% 상한.** CTA 버튼, 활성 탭 인디케이터, 포커스 링, 인용 하이라이트 — **여기까지만**. 봇 카드 배경을 브랜드색으로 칠하지 않는다.
3. **멀티봇 구분은 색이 아니라 형태로.** 실측 6곳 어디도 카테고리를 색으로 나누지 않았다. 봇 구분은 ⓐ 모노스페이스 라벨(`--font-mono` + `--label-size`), ⓑ 아바타 이니셜, ⓒ 좌측 2px 세로 규칙선 정도로. 색을 쓴다면 `--text-3` 수준의 **탈채도 버전**만.
4. **인용 블록**: `--bg-sunken` + 좌측 `2px solid var(--border-strong)` + `--font-serif` + `--body-lg`. 그림자·radius 없음(문서는 뜨지 않는다).
5. **노이즈·그레인 금지.** 6곳 중 5곳이 0건이고 Raycast만 카드 1종에 `opacity .07`로 쓴다. 질감이 필요하면 `--bg-page`/`--bg-surface`/`--bg-sunken` 3단 명도차로 해결한다.
6. **헤더**: 높이 64px, 배경 `--bg-page` **불투명**(Vercel 방식) 또는 `rgba(250,249,247,0.8)` + `backdrop-filter: blur(20px)`(Linear 방식). 하단 보더는 `--border-faint` 1px. 둘 중 하나만, 섞지 않는다.

**히어로 구성 지침** (실측 공통점 반영)

- 헤드라인 `--display-1` (56px), 상단 여백 **240~280px** (Linear 272 · Vercel 328).
- 리드 카피는 **`--text-2`나 `--text-3`으로 낮춘다.** 1단계 색 금지 (실측 5곳 공통).
- 제품 스크린샷에 **브라우저 크롬 목업을 씌우지 않는다** — 6곳 전부 안 씀.
- 프레임을 쓴다면 `--r-card` + `--shadow-lift`까지. Linear처럼 하단을 배경색 그라디언트로 용해시키는 편이 더 고급스럽다:
  ```css
  mask-image: linear-gradient(to bottom, #000 60%, transparent 100%);
  ```
- 진입 애니메이션: `opacity 0→1` + `translateY(16px)→0`, `--dur-enter` `--ease-out`, 스태거 60ms. **그 이상 금지.**

---

## 5. 한 장 요약

```
잉크      라이트 #1c1b18~#171717 · 다크 #07080a~#14120b   (순검정·순백 금지)
배경      #faf9f7 위에 #ffffff 카드                        (명도차 5 이하)
계층      color-mix(in oklab, ink N%) 100/72/54/38%       (본문 기본 = 2단계)
보더      1px, 잉크 9%                                     (고정 회색 금지)
radius    6 / 12 / pill                                    (3개면 충분, 상한 16)
그림자    2단, 마지막 레이어에 0 0 0 1px 헤어라인 링
트래킹    ≤12px +0.01em · 14~18px 0 · 24~32px -0.02em · ≥48px -0.03em
          (size·tracking·leading 을 한 토큰 세트로 잠글 것)
웨이트    400~500 상한                                     (600+ 금지)
행간      디스플레이 1.05~1.10 · 한글 본문 1.70            (1.2~1.3 구간 회피)
간격      가로 4px 기반 · 세로 25.5px(=본문 1행) 베이스라인 그리드
          섹션 ≈115px · 컨테이너 1200 · 산문 660
액센트    뷰포트 1% 이하, CTA·링크·포커스·인용 하이라이트만
모션      160ms cubic-bezier(.4,0,.2,1) · 진입 opacity + 최대 16px / 400ms
          transition: all 금지 · prefers-reduced-motion 필수
질감      노이즈·그레인 0                                   (6곳 중 5곳 미사용,
          쓴다면 feTurbulence baseFrequency 3 / overlay / opacity ≤0.07)
```

---

## 부록 — 원자료 위치

세션 스크래치패드에 원본이 남아 있다 (세션 종료 시 삭제됨):

```
<scratchpad>/teardown/
  {linear,vercel,stripe,raycast,cursor,framer}.html    원본 HTML
  css_{linear,vercel,stripe,raycast,cursor}/*.css      CSS 번들 76개
  _linear_all.css / _stripe_all.css / _vercel_all.css  병합본
```

측정 재현: Playwright 1440×900, `getComputedStyle` 전수 조사. 위 표의 `N=` 수치는 상위 5,000 노드 기준 상대 빈도다.
