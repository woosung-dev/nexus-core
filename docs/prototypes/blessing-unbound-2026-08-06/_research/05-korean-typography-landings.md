# 한국어 프리미엄 랜딩의 조판 해부 — 실측 조사

조사일: 2026-08-06
조사자 관점: 한국어 타이포그래피 기준의 브랜드 디자인 해부

**방법론**: 라틴 레퍼런스를 번역해 옮기면 왜 어색해지는지를 수치로 확정하기 위해, 감상이 아니라 **실제 배포 CSS와 실제 폰트 파일의 메트릭**을 받아서 측정했다.

1. HTML: `curl` (UA 위장) → 403이면 `curl_cffi` TLS 임퍼소네이션(`impersonate="chrome"`) → 그래도 막히면 Jina Reader(`r.jina.ai`)
2. CSS: 각 사이트의 디자인 시스템 번들을 직접 내려받아 `font-size` / `line-height` / `letter-spacing` / `font-weight` 를 같은 규칙 블록 안에서 **쌍으로 파싱** 후 em 비율로 정규화
3. 폰트: `.otf` 원본을 받아 `fontTools` 로 `unitsPerEm`, `hmtx`(자폭), 글리프 잉크 바운딩박스, `hhea` 기본 행간을 직접 측정

측정 스크립트와 원본 CSS 사본은 세션 스크래치패드에 있고 레포에는 커밋하지 않았다.

**대상**: 토스(toss.im) · 당근(team.daangn.com) · 채널톡(channel.io/ko) · 리디(ridibooks.com + ridicorp.com) · 29CM(29cm.co.kr + content.29cm.co.kr) · 무신사(musinsa.com) · 우아한형제들(woowahan.com) · 클래스101 · 컬리 · 센드버드(sendbird.com/ko) — 총 10곳

**실측 실패 명시**:
- `woowahan.com` 본문 HTML은 403(WAF)으로 카피 수집 실패. 단, **CSS 번들(`chunk-common.554ed250.css`, 172KB)은 정상 취득**해서 폰트·조판 수치는 1차 실측했다.
- `ridicorp.com/` 루트는 403, `ridicorp.com/ko/`는 200. 다만 이 사이트는 WordPress 기반이라 조판 토큰이 거의 없어 **리디의 조판 실측은 `ridibooks.com`(자체 프론트엔드) 쪽 수치를 사용**했다.
- 올리브영은 봇 차단 페이지(2.4KB)만 반환되어 제외.
- 클래스101·컬리는 CSS 토큰이 런타임 생성이라 폰트 스택만 확인하고 수치는 미측정.

---

## 0. 먼저, 왜 라틴 수치를 그대로 옮기면 깨지는가 — 폰트 파일 실측

`fontTools`로 실제 폰트 파일을 뜯어 재본 값. **이 표가 이 문서 전체의 근거다.**

| 폰트 | unitsPerEm | 한글 자폭(advance) | 한글 잉크 폭 | **좌우 여백** | 'H' 높이 | '한' 잉크 높이 | hhea 기본 행간 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pretendard | 2048 | **0.8643em** | 0.8076em | **0.0566em** | 0.707em | 0.849em | 1.193 |
| SUIT | 1000 | 0.8740em | 0.8060em | 0.0680em | 0.722em | 0.854em | 1.248 |
| Wanted Sans | 2048 | **0.8643em** | 0.8057em | 0.0586em | 0.707em | 0.848em | 1.193 |
| 고운바탕 | 1000 | 0.9300em | 0.8601em | 0.0699em | 0.695em | 0.915em | 1.448 |
| Noto Sans KR | 1000 | 0.9200em | 0.8330em | **0.0870em** | 0.733em | 0.884em | 1.448 |

여기서 세 가지가 바로 나온다.

**(1) 한글은 자간을 줄 여백 자체가 라틴의 60% 밖에 없다.**
Pretendard 기준 한글 한 글자의 좌우 여백 총합은 **0.0566em**. 같은 폰트의 대문자 'H'는 자폭 0.6455em에 잉크 0.551em → 여백 **0.0945em**.
→ `letter-spacing: -0.05em`을 걸면 라틴은 여백의 53%가 사라지지만 **한글은 88%가 사라진다.** 라틴에서 "타이트하고 세련된" 값이 한글에서는 글자가 서로 붙어 뭉개지는 값이다. 이게 라틴 레퍼런스를 그대로 옮겼을 때 헤드라인이 지저분해지는 1차 원인이다.

여기서 실무 공식이 도출된다:

```
안전 자간 하한 = -(해당 폰트의 한글 좌우여백 × 0.5)
절대 하한     = -(해당 폰트의 한글 좌우여백 × 0.7)
```

- Pretendard / Wanted Sans → 안전 -0.028em(**-0.03em**), 절대 -0.040em
- SUIT → 안전 -0.034em, 절대 -0.048em
- Noto Sans KR → 안전 -0.044em, 절대 -0.061em

그리고 이 계산값이 **당근 Seed 디자인 시스템의 실제 토큰과 정확히 일치한다**(뒤 §2). 즉 당근은 폰트 여백의 절반/70% 지점에 자간 토큰을 끊어놓은 셈이다.

**(2) 한글은 라틴보다 20% 커 보인다. 그래서 본문 크기와 행간이 달라진다.**
'한' 잉크 높이 0.849em vs 'H' 0.707em → **1.20배**. 소문자 x-height(0.530em) 대비로는 **1.60배**.
→ 라틴 18px 본문의 시각적 크기 = 한글 15px. 라틴 레퍼런스의 px 값을 그대로 쓰면 한글은 항상 한 치수 크게 나온다.
→ 더 중요한 건 세로다. 한글 글자는 베이스라인 **아래로도 -0.061em 내려간다**('한'의 y 범위 -0.061 ~ 0.788). 라틴 대문자는 베이스라인 위에만 있다(0 ~ 0.707). 즉 한글은 위아래를 다 쓰기 때문에 **같은 line-height에서 라틴보다 훨씬 답답해진다.** 라틴에서 1.4가 편안하면 한글은 1.5~1.6이 필요하다.

**(3) 폰트의 기본 행간을 믿으면 안 된다.**
Pretendard의 `hhea` 기본 행간은 **1.193**. `line-height`를 명시하지 않으면 한글이 거의 붙어버린다. (Noto Sans KR·고운바탕은 1.448로 그나마 낫다.) 조사한 10개 사이트 전부가 `line-height`를 예외 없이 명시하고 있었다.

---

## 1. 토스 — toss.im

### 서체 전략
```
'Toss Product Sans', 'Tossface',
  -apple-system, BlinkMacSystemFont, 'Basier Square', 'Noto Sans KR',
  'Segoe UI', 'Apple SD Gothic Neo', Roboto, ... sans-serif
word-break: keep-all; overflow-wrap: break-word;
-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
```
- **전용 서체 단일 운용.** 국문·영문·숫자 전부 `Toss Product Sans` 하나로 처리한다. 국·영문 분리 폰트 없음.
- 폴백 레이어는 라틴=`Basier Square`(자체 호스팅 woff2), 한글=`SD Gothic Neo`(산돌, `static.toss.im/fonts/sandoll/`)로 **분리 페어링을 준비**해 뒀다. 즉 전용 서체가 안 뜨면 "라틴 전용 + 한글 전용" 2폰트 조합으로 떨어진다.
- 이모지까지 자체 서체(`Tossface`)로 가져갔다. 브랜드 표면 전체를 소유하겠다는 태도.
- 폴백 웨이트는 400/500/700 **3단**만 정의(`static.toss.im/fonts/all.css` 실측).

### 자간 — **0. 전 시스템에 letter-spacing 선언이 한 줄도 없다**
| 파일 | 크기 | `letter-spacing` 등장 횟수 |
|---|---:|---:|
| `tds.min.css` (Toss Design System 42.61.2) | 143,799 B | **0** |
| `tds-pc/main.css` (마케팅 사이트) | 210,106 B | **0** |
| `assets-fe.toss.im/tds/style.css` | 10,605 B | **0** |
| `toss.im` 인라인 스타일 | 99,561 B | **0** |

이건 누락이 아니라 정책이다. 자체 한글 서체를 만들면서 **자간을 폰트 안에서 이미 해결**했기 때문에 CSS에서 더 건드리지 않는다. "한글은 자간을 안 준다"의 가장 강한 실증.

### 크기·행간 — **비율이 아니라 고정 여백(leading)**

마케팅 사이트 토큰(`:root`):
```css
--font-size-h1: 56px;  --font-size-h2: 48px;  --font-size-h3: 36px;
--font-size-h4: 32px;  --font-size-h5: 24px;  --font-size-h6: 20px;
--font-size-h7: 17px;  --font-size-p:  15px;  --font-size-sm: 13px;
--font-size-xsmall: 11px;
--line-height-adjust: 1.3;   /* h1~h4 (32~56px) */
--line-height-base:   1.6;   /* h5~xsmall (24px 이하) */
```
`.typography--h1,--h2,--h3,--h4 { line-height: 1.3 }` / `.typography--h5 … --xsmall { line-height: 1.6 }`
→ **중간값이 없는 이진 규칙.** 32px 이상은 1.3, 24px 이하는 1.6.

제품 디자인 시스템(TDS)의 11~30px 구간은 더 정교하다. 실측한 line-height 비율을 px로 환산하면:

| font-size | line-height(비율) | line-height(px) | 여백 |
|---:|---:|---:|---:|
| 30 | 1.333 | 40 | +10 |
| 29 | 1.310 | 38 | +9 |
| 28 | 1.321 | 37 | +9 |
| 26 | 1.346 | 35 | +9 |
| 24 | 1.375 | 33 | +9 |
| 22 | 1.409 | 31 | +9 |
| 20 | 1.450 | 29 | +9 |
| 18 | 1.500 | 27 | +9 |
| 17 이하 | 1.500 고정 | — | — |

**행간 = 글자크기 + 9px (18~29px 구간)**. 비율이 아니라 상수 여백으로 잡혀 있다. 그 결과 비율은 크기가 커질수록 자동으로 내려간다(1.5 → 1.31).

### 카피 — 해요체, 수동 개행, 한 줄 6~12자
헤드라인 실측(개행 문자 기준, `white-space: pre-wrap` 사용 14회):

| 헤드라인 원문 | 줄 구조 |
|---|---|
| 금융을 넘어 / 일상을 더 편리하게 | 6자(2어절) / 9자(3어절) |
| 내 돈 관리, / 지출부터 일정까지 / 똑똑하게 | 7자(3) / 9자(2) / 4자(1) |
| 간편하고 안전하게 / 수수료는 평생 무료로, / 이런 송금 써보셨나요? | 9자(2) / 12자(3) / 12자(3) |
| 여러 은행의 조건을 / 1분 만에 / 확인해보세요 | 10자(3) / 5자(2) / 6자(1) |
| 금융 생활의 첫 걸음, / 신용점수를 / 미리 무료로 관리하세요 | 12자(4) / 5자(1) / 12자(3) |
| 투자, / 모두가 할 수 있도록 | 3자(1) / 11자(4) |
| 결제는 간편하게, / 할인과 적립은 두둑히 | 8자(2) / 11자(3) |

- 전체 수동 개행 라인 113개의 **길이 중앙값 12자, p90 27자**.
- 헤드라인 1줄 = **3~12자, 1~4어절**. 2~3줄 구성.
- 종결: `~하세요` `~해 보세요` `~예요` `~어요` — **전부 해요체.** `~합니다`는 등장하지 않는다.
- 부사형 종결(`더 편리하게`, `똑똑하게`, `모두가 할 수 있도록`, `두둑히`)로 문장을 안 끝내고 끊는 게 세련됨의 핵심 장치.

### 색
```
grey900 #191f28  grey800 #333d4b  grey700 #4e5968  grey600 #6b7684
grey500 #8b95a1  grey400 #b0b8c1  grey300 #d1d6db  grey200 #e5e8eb
grey100 #f2f4f6  grey50  #f9fafb
blue500 #3182f6 (주조)  blue700 #1b64da  blue50 #e8f3ff
--background: #fff  --greyBackground: #f2f4f6
```
- **순수 검정(#000)이 없다.** 가장 어두운 값이 `#191f28`(파랑 기운의 근검정, hue ≈ 218°).
- 그레이 램프 10단계가 전부 파랑 쪽으로 틀어져 있다. 이게 "차갑고 정돈된" 인상의 실체.
- 아티클 본문 실측: `.p-post { font-size:17px; line-height:1.6; color:#4e5968 }` — **본문은 grey700**, 제목은 `#333d4b`(grey800). 본문에 최암부를 쓰지 않는다.
- 배경은 `#fff` ↔ `#f2f4f6` 교대. 그림자·보더 대신 배경색 교대로 섹션을 나눈다.

### 레이아웃
- `.p-container--default { max-width: 1140px }`
- 브레이크포인트 `max-width: 639/640px` 13회 + `min-width: 640px` 4회 → **데스크톱 퍼스트 + 640px 단일 분기**.

---

## 2. 당근 — team.daangn.com (Seed 디자인 시스템)

### 서체 전략
```css
font-family: 'Karrot Sans', sans-serif;
```
- **전용 서체 단일 운용.** 국·영문 분리 없음.
- `KarrotSans.css` 실측 결과 웨이트는 **400 / 700 / 900 딱 3단**. 500·600이 없다. → 웨이트 대비를 만들려면 400↔700, 700↔900의 큰 점프만 가능.

### 자간 — **em 토큰 4단, 그리고 실제 페이지에선 px 고정**

Seed 토큰(실측):
```css
--seed-scale-letter-spacing-none:       0em;
--seed-scale-letter-spacing-narrow-200: -0.02em;
--seed-scale-letter-spacing-narrow-300: -0.03em;
--seed-scale-letter-spacing-narrow-400: -0.04em;
```
**-0.04em 이 최대치다. 그 이상은 토큰 자체가 존재하지 않는다.** (§0에서 계산한 Pretendard급 폰트의 "절대 하한 -0.040em"과 정확히 일치)

역할별 배정:

| 역할 | 크기 | 자간 | 행간 | 웨이트 |
|---|---:|---:|---:|---|
| h1 | 48px | **-0.04em** | 135% | bold |
| h2 | 42px | **-0.04em** | 135% | bold |
| h3 | 34px | -0.03em | 135% | bold |
| h4 | 26px | -0.03em | 135% | bold |
| title1/2/3 | 24 / 20 / 18px | -0.03em | 135% | bold·regular |
| subtitle1/2 | 16 / 14px | -0.02em | 135% | bold·regular |
| body-l1/l2 | 16 / 14px | -0.02em | **162% / 150%** | — |
| body-m1/m2 | 16 / 14px | -0.02em | 135% | — |
| label1-bold | 18px | **0em** | 135% | bold |
| caption1/2 | 13 / 12px | **-0.04em** | 150% / 135% | — |

읽는 법:
- **디스플레이(42px↑)와 초소형 캡션(12~13px) 양 극단에만 -0.04em을 준다.** 중간대(14~24px)는 -0.02 ~ -0.03em. 라틴의 "크면 조이고 작으면 푼다"와 **정반대는 아니지만 대칭 구조**다. 한글에서 캡션을 조이는 이유는 작은 크기에서 글자가 부표처럼 떠 보이는 걸 막기 위해서다.
- 행간 토큰은 **135% / 150% / 162% 딱 3단.** 제목·라벨=135%, 캡션·본문 표준=150%, 긴 본문=162%.

### 실제 마케팅 페이지에서는 px 고정 자간
`styles.*.css` 실측 — 토큰이 아니라 하드코딩된 값들:

| 용도 | font-size | line-height | letter-spacing | 환산 em | 부가 |
|---|---:|---:|---:|---:|---|
| 히어로 | 64px | 84px (1.313) | 없음 | 0 | `word-break: keep-all` |
| 히어로 ≤1024 | 52px | 74px (1.423) | — | — | |
| 히어로 ≤640 | 36px | 52px (1.444) | — | — | |
| 섹션 헤드라인 | 42px | 58px (1.381) | **-0.6px** | **-0.0143em** | `white-space: pre-wrap`, `max-width: 1152px` |
| 섹션 헤드라인 ≤640 | 28px | 42px (1.500) | **-0.6px** | **-0.0214em** | |
| 서브 헤드 | 28px | 44px (1.571) | -0.6px | -0.0214em | `keep-all` |

**중요한 함정 하나.** 당근은 자간을 `-0.6px` **고정**으로 걸어놨다. px 고정이면 em 환산값이 **크기가 커질수록 작아진다**(42px에서 -0.014em, 28px에서 -0.021em). 즉 큰 헤드라인일수록 자간이 느슨해진다 — 라틴 조판의 표준 관행(클수록 조인다)과 **정반대**다. 그런데 결과는 오히려 안정적이다. §0에서 봤듯 한글은 큰 크기에서도 여백 여유가 늘지 않기 때문에(em 상대값이므로), px 고정은 "작은 글씨는 조이고 큰 글씨는 안 건드린다"는 한글 친화적 결과를 우연히 만들어낸다.

→ **실무 권고: 한글 자간은 px가 아니라 em으로 선언하고, 크기가 커질 때 조이지 말고 그대로 두거나 아주 약간만 조여라.**

### 카피
| 헤드라인 원문 | 줄 구조 | 문형 |
|---|---|---|
| 동네를 여는 문, / 당근 | 9자(3어절) / 2자(1) | 명사형 종결 + 브랜드명 단독 배치 |
| 로컬의 모든 것을 연결해, / 동네의 숨은 가치를 깨워요 | 13자 / 14자 | 연결어미 + 해요체 |
| 우리에게 동네의 연결이 / 필요한 이유 | 12자 / 6자 | 명사형 종결(`~한 이유`) |
| 당근은 이웃들이 / 함께 살아가는 동네를 꿈꿔요 | 8자 / 15자 | 해요체 |
| 당근은 매일 / 새로운 역사를 쓰고 있어요 | 6자 / 14자 | 해요체 진행형 |
| 유수한 글로벌 투자자들이 / 당근과 함께해요 | 13자 / 8자 | 해요체 |

- 수동 개행 라인 길이 **중앙값 14자**.
- `white-space: pre-wrap` 18회 — 헤드라인 줄바꿈을 전부 사람이 지정한다.
- 종결 전부 **해요체**. 토스와 동일.

### 색
```
#1a1c20 (본문 최암부, 근검정)   #212124
#eaebee  #d1d3d8  #adb1ba  #868b94 (그레이 램프)
#f2f3f6 (배경)
theme-color: #ff7e36 (당근 오렌지)
톤 배경: #fff5f0 #fff7e6 #fff3f2 #e8faf6 #ebf7fa (아주 옅은 컬러 필드)
```
- 여기도 **#000 없음**. `#1a1c20`이 최암부.
- 주조색 오렌지는 텍스트에 쓰지 않고 **아주 옅은 배경 필드(#fff5f0 등)** 로만 등장. 컬러를 면으로 쓰고 글자는 뉴트럴로 두는 전략.

### 레이아웃
- 콘텐츠 컨테이너 `max-width: 1152px` (헤드라인 자체에도 `max-width:1152px` 명시)
- 카드 `max-width: 570px`
- 브레이크포인트 `max-width: 640px` / `max-width: 1024px` → **데스크톱 퍼스트 3단**
- 히어로 축소비 64 → 52 → 36px (1.78배), 섹션 헤드라인 42 → 28px (1.5배)

---

## 3. 채널톡 — channel.io/ko

### 서체 전략 — 로케일별 스택 분기
```css
/* 한국어 */
'Pretendard', 'Pretendard Fallback', -apple-system, BlinkMacSystemFont,
'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif

/* 다국어(일본어 포함) */
'Inter', 'Inter Fallback', 'NotoSansKR', 'NotoSansKR Fallback',
'NotoSansJP', 'NotoSansJP Fallback', ...
```
- **한국어 페이지는 Pretendard 단일**, 다국어 페이지는 Inter(라틴) + Noto Sans KR/JP(CJK) **분리 페어링**. 로케일 단위로 폰트 전략 자체를 바꾼다.
- `Pretendard Fallback` / `Inter Fallback` 같은 **로컬 폴백 메트릭 폰트**를 지정해 FOUT 시 레이아웃 시프트를 막는다 (Next.js `next/font` 패턴).

### 자간·행간 실측 (동일 규칙 블록에서 쌍으로 추출)

| font-size | 자간(em 환산) | 행간 비율 | 웨이트 |
|---:|---:|---:|---|
| 54px | **-0.020em** | 1.296 | 600 |
| 44px | -0.020em | 1.409 | 600 |
| 40px | -0.020em | 1.400 | — |
| 36px | -0.020em | 1.333 | — |
| 30px | -0.020 ~ -0.033em | 1.333 ~ 1.400 | — |
| 25px | -0.010 ~ -0.020em | 1.200 ~ 1.280 | 600 |
| 22px | -0.008 ~ -0.020em | 1.273 ~ 1.364 | 500·600 |
| 18px | -0.010 ~ -0.022em | 1.444 ~ 1.556 | 400 |
| 17px | -0.006 ~ -0.010em | 1.529 ~ 1.588 | 400 |
| 16px | -0.010 ~ -0.025em | 1.500 ~ 1.591 | 400·500·600 |
| 15px | -0.010 ~ -0.015em | 1.467 ~ 1.733 | 400·500·600 |
| 14px | -0.008 ~ -0.010em | 1.429 ~ 1.571 | 400·500 |
| 12px | -0.008em | 1.167 ~ 1.500 | 400 |

가장 흔한 값은 `-0.16px`(96회), `-0.01em`(64회), `-0.18px`(60회) — 즉 **본문 자간의 사실상 표준은 -0.01em**.
디스플레이(36~54px)는 일관되게 **-0.02em**. -0.05em은 65px 라틴 디스플레이 한 곳에만 등장한다.

정리: **디스플레이 -0.02em / 본문 -0.01em / 행간은 디스플레이 1.30~1.41, 본문 1.53~1.59.**

### 카피 — **여기만 합니다체다**
| 원문 | 어절 | 문형 |
|---|---:|---|
| 고객 상담에 최적화된 AI 솔루션 | 4 | 명사형 종결 |
| 상담 80%를 효율화하는 AI | 3 | 명사형 종결(숫자 선행) |
| 거짓말하는 AI를 방지하는 '규칙' | 4 | 명사형 종결(따옴표 강조) |
| 앵무새 답변이 아니라 직접 실행까지 | 5 | 조사 종결(`~까지`) |
| 체계적으로 관리해야 AI의 '지식'이 됩니다 | 5 | **합니다체** |
| 강력한 연동, 쓰시는 플랫폼 계속 쓰셔도 됩니다 | 7 | **합니다체** |
| 흩어진 비즈니스 데이터를 한 곳으로 모으세요 | 5 | 하세요체(CTA) |
| 일주일 넘게 걸리던 분석을 5분만에 해줍니다 | 5 | **합니다체** |

- 본문 전부 `~합니다`. B2C(토스·당근)의 `~해요`와 **명확히 갈린다.**
- CTA만 `~하세요`로 전환.
- 헤드라인 어절 수 3~7 — B2C보다 길다. 명사형 종결 비중이 높다.
- 라틴 대문자를 그대로 섞는다(`All-as-One 워크스페이스`, `AI CoS`, `ALF`) — 번역하지 않고 그대로 둔다.

### 색·레이아웃
- `#242428`(근검정), 액센트 `#5e56f0`(보라) + `#00a6ff`(파랑), 배경 틴트 `#f1f3ff`
- 브레이크포인트 `991 / 767 / 1280px` — **min-width 우세(1025px 11회) → 부분 모바일 퍼스트**
- 컨테이너 `1280px`(107회), 서브 `1160 / 1320px`

---

## 4. 리디 — ridibooks.com / ridicorp.com

### 서체 전략 — **국·영문 분리 페어링의 교과서**
```css
font-family: 'Pretendard Variable', 'Pretendard Std Variable', 'Pretendard JP Variable',
  -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue',
  'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', ... sans-serif;
```
그리고 별도로:
```css
@font-face { font-family: 'ridi-roboto'; src: url(https://static.ridicdn.net/web-font/ridi-roboto-{regular,medium,semibold,bold}-webfont.woff2) }
@font-face { font-family: 'exp-ridi-roboto-bold-italic'; ... }
```
- 한글 = **Pretendard Variable 자체 호스팅**(`static.ridicdn.net/web-font/pretendard.css`)
- 라틴·숫자 = **`ridi-roboto` 커스텀**(Roboto 파생 4웨이트 + Bold Italic)
- → **조사 대상 중 국·영문 폰트를 명시적으로 분리한 유일한 국내 서비스.** 콘텐츠(도서 제목·저자명)에 라틴이 많이 섞이는 서비스 특성 때문으로 보인다.
- 리디는 자체 세리프 **RIDIBatang(리디바탕)** 을 배포하지만 **랜딩/커머스 화면에는 쓰지 않는다.** 소스 전체에서 `ridibatang` 문자열이 1회(뷰어 폰트 선택 옵션 추정)만 등장.

### 자간·행간 — **-0.01em 단일 토큰**
| 값 | 등장 |
|---|---:|
| `-0.01em` | **17회 (압도적)** |
| `-0.03em` | 2회 |
| `-0.02em` | 1회 |
| px 개별값(-0.22 / -0.2 / -0.16 / -0.14px) | 각 1회 |

행간은 **1.12 ~ 1.31의 매우 좁은 대역**(26px→1.231, 16px→1.125~1.188, 14px→1.143~1.286). 정보 밀도가 높은 커머스 리스트라 의도적으로 압축한 것. **이건 랜딩 조판이 아니라 앱 UI 조판이므로 랜딩 레퍼런스로 그대로 쓰면 안 된다.**

### 실측 실패
`ridicorp.com`은 WordPress + `forced-style.css`(2.7KB)뿐이라 조판 토큰이 없다. 채용/브랜드 페이지의 헤드라인 조판은 수집하지 못했다. 뉴스룸 h1 표본만 확보: "리디, 추석연휴에 뭐 볼까…한가위 특급 이벤트 진행"(보도자료 문체라 브랜드 카피 표본으로는 부적합).

---

## 5. 29CM — 29cm.co.kr / content.29cm.co.kr (Ruler 디자인 시스템)

### 서체 전략
```css
font-family: 'Pretendard Variable', 'Apple SD Gothic Neo', NanumBarunGothic,
  '나눔바른고딕', 'Malgun Gothic', '맑은 고딕', dotum, sans-serif;
/* 자체 CDN 서브셋: d13fzx7h5ezopb.cloudfront.net/fonts/pretendard/PretendardVariable.subset.N.woff2 */
```
- **Pretendard Variable 단일**, 유니코드 레인지별로 수십 개 서브셋 woff2로 쪼개 자체 CDN 호스팅. `format("woff2-variations")`.
- 국·영문 분리 없음.

### 자간 — **단일 토큰, 값은 0**
```css
--ruler-scale-letter-spacing: 0;
```
Ruler 디자인 시스템의 **모든** 시맨틱 타이포그래피 토큰(text-xxs ~ title-xxl, 48개)이 예외 없이 이 하나를 참조한다.
→ 토스와 같은 결론. **"감도 깊은" 커머스 에디토리얼의 대표 브랜드가 자간을 0으로 둔다.**

### 크기·행간 스케일 (전량 실측)
```css
/* 크기 */ 10 11 12 13 14 15 16 18 20 22 24 28 30 32 48px
/* 행간 */ --ruler-scale-line-height-1:100%  -2:120%  -3:136%  -4:140%  -5:150%  -6:160%
/* 웨이트 */ 100 300 400 500 600 700
```
| 역할 | 크기 | 행간 |
|---|---:|---:|
| title-xxl / xl / l / m / s / xs | 30 / 28 / 24 / 22 / 20 / 18px | **136%** |
| text-xxl / l / m | 16 / 14 / 13px | **140%** |
| text-xl | 15px | **150%** |
| text-s / xs | 12 / 11px | 136% |
| text-xxs | 10px | 120% |

실측 CSS에서도 그대로 확인된다: **18~30px 전 구간 1.360 고정**, 14~16px 1.400, 15px 1.500.
→ **29CM은 "제목=136%, 본문=140~150%" 두 값으로 사이트 전체를 운영한다.** 이 단순함이 잡지 같은 정연함의 실체다.

- 토큰 스케일 최대치가 **48px**. 그 이상 디스플레이는 이미지로 처리한다.
- 웨이트 사용 실측: 700(70회) / 400(44) / 500(40) / 600(5). **400·500·700 3단**이 실질.

### 커머스 에디토리얼을 웹에서 구현하는 법 (핵심)
`content.29cm.co.kr`(29Magazine)의 조판 토큰은 **본 사이트와 완전히 동일**하다. 즉 "잡지 느낌"을 조판 파라미터로 만들지 않는다. 대신:

1. **네비게이션·라벨은 전부 영문 대문자.** `Special-Order` / `Showcase` / `PT` / `29Magazine` / `Latest Post` / `WOMEN` `MEN` `INTERIOR` `KITCHEN` `ELECTRONICS` `BEAUTY` `EARTH`. 한글은 콘텐츠 카피에만 쓴다. → **국문/영문의 역할 분리를 서체가 아니라 정보 위계로 한다.**
2. **에디토리얼 제목 = 짧은 명사구, 부제 = 해요체 한 문장.**
   - "29 에디터스 픽 생기 가득 레몬빛" / "보기만 해도 기분이 좋아지는 색. 레몬빛으로 우리 집에 생기를 불어넣어요."
   - "29 에디터스 픽 귀여운 건 못 참지" / "이렇게 귀여운 건 또 어디 있었나 싶은 사랑스러운 홈 아이템만 모았어요."
   - "29 테크 트렌드 리포트 Ep.57 매일의 케어를 더 쉽게" / "간편하게 시작하는 나만의 뷰티 루틴, 셀프케어의 즐거움을 더해줄 거예요."
   - 시리즈명(`29 에디터스 픽`, `Ep.57`)을 제목 앞에 붙여 **잡지 목차 구조**를 만든다.
3. **이미지 비율을 16:9로 고정**하고 그 아래 제목/부제/날짜만 놓는다. 여백과 그리드가 조판 대신 리듬을 만든다.
4. 색은 뉴트럴(`#19191a` `#303033` `#474747` `#5d5d5d` `#8a8a8a` `#a0a0a0` `#c4c4c4` `#e4e4e4` `#f4f4f4` `#f7f7f7`) — **완전 무채색 램프 10단** + 액센트 `#375fff` 한 점.

### 레이아웃
- 컨테이너 `1280px` / `1025px` / `1040px`
- `min-width` 브레이크포인트 우세(1280·1025·541·320px) → **모바일 퍼스트**

---

## 6. 무신사 — musinsa.com (MDS)

### 서체 전략 — 로케일별 CJK 스택 스위칭
```css
/* 기본(한국어) */ Pretendard Variable, Pretendard, sans-serif
/* ko 상세      */ Pretendard, 'Apple SD Gothic Neo', sans-serif
/* ja          */ 'Hiragino Sans', 'Noto Sans JP', system-ui, Pretendard, 'Apple SD Gothic Neo', sans-serif
/* zh-CN       */ 'PingFang SC', 'Noto Sans', MiSans, Pretendard, ...
/* zh-TW       */ 'PingFang TC', 'Noto Sans CJK TC', 'Noto Sans', Pretendard, ...
```
- Pretendard 정적 4웨이트(Regular/Medium/SemiBold/Bold)를 자체 호스팅. `src: local("☺")` 트릭으로 로컬 폰트 오탐을 막는 구현.
- 글로벌 확장 시 **Pretendard를 폴백 뒤로 밀고 로캘 네이티브 CJK를 앞세우는** 구조. 한국어 브랜드가 다국어로 나갈 때의 실무 표준.

### 자간 — **0 (명시적으로)**
`letter-spacing: 0` 17회, 그 외 없음. MDS 타이포그래피 클래스가 전부 `letter-spacing: 0`을 **명시**한다(상속 차단 목적).

### 행간 — **글자크기 + 6px 고정 여백**
| 클래스 | size | line-height | 여백 | 비율 |
|---|---:|---:|---:|---:|
| `.text-etc_9px_semibold` | 9 | 11 | +2 | 1.222 |
| `.text-etc_10px_semibold` | 10 | 12 | +2 | 1.200 |
| `.text-etc_11px_semibold` | 11 | 14 | +3 | 1.273 |
| `.text-body_13px_reg/semi` | 13 | 18 | +5 | 1.385 |
| `.text-body_14px_reg/semi` | 14 | 20 | +6 | 1.429 |
| `.text-etc_16px_med` | 16 | 22 | +6 | 1.375 |
| `.text-title_18px_semi` | 18 | 24 | +6 | 1.333 |
| `.text-title_20px_med` | 20 | 26 | +6 | 1.300 |
| `.text-title_22px_semi` | 22 | 28 | +6 | 1.273 |
| `.text-title_26px_med` | 26 | 32 | +6 | 1.231 |
| `.text-etc_42px_reg` | 42 | 48 | +6 | **1.143** |

**13~42px 전 구간이 +6px 고정.** 그래서 비율은 1.385 → 1.143으로 계속 떨어진다. 극단적으로 밀도 높은 커머스 UI 조판. **랜딩에는 부적합**하지만, "행간을 비율이 아니라 상수로 관리한다"는 한국 UI의 공통 문법을 가장 선명하게 보여주는 사례다.

- 클래스 이름이 `text-title_22px_semi` 처럼 **크기와 웨이트를 이름에 박아 넣는다.** 시맨틱 네이밍을 포기한 실용 노선.
- 웨이트 사용: 500(24) / 400(16) / 600(14) / 700(3) — **500이 기본값.** 한글은 400이 얇아 보여서 UI 기본을 Medium으로 올리는 관행.
- 색: `#2a2a2a` `#4a4a4a` `#8a8a8a` `#e0e0e0` `#ebebeb` `#f5f5f5` + 액센트 `#245eff`/`#3a6eff`, 경고 `#f31110`/`#f73c3b`
- 컨테이너 `1279px`(11회) → 데스크톱 퍼스트

---

## 7. 우아한형제들 — woowahan.com

### 서체 전략 — **본문 중성 산세리프 + 디스플레이 브랜드 서체**
```css
/* 본문·UI */
font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont,
  system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo',
  'Noto Sans KR', 'Malgun Gothic', ... sans-serif;

/* 디스플레이 전용 (자체 폰트, static/fonts/ 자체 호스팅) */
'BM HANNA Pro' / 'BM HANNA Air' / 'BM HANNA 11yrs old'
'BM DoHyeon' / 'BM JUA' / 'BM YEONSUNG' / 'BM KIRANGHAERANG'
'BM EULJIRO' / 'BM Euljiro oraeorae' / 'BM Euljiro 10 years later' / 'BM Kkubulim'
```
- 배민체 11종을 자체 보유하면서도 **본문은 Pretendard**로 간다. 브랜드 서체는 **디스플레이·장식에만** 쓴다.
- → 이게 "브랜드 서체를 가진 회사"의 정답 패턴이다. 개성 있는 한글 서체는 본문 가독성이 무조건 떨어지므로 역할을 갈라야 한다.

### 실측 수치
| size | 자간 | 행간 | 웨이트 |
|---:|---:|---:|---|
| 48px | 0 | 1.350 | 700 |
| 42px | 0 | 1.200 ~ 1.524 | 700 |
| 40px | **-0.030em** | 1.300 | 700 |
| 32px | 0 | 1.312 ~ 1.400 | 700 |
| 30px | 0 | 1.400 | 400·700 |
| 24px | -0.017em | 1.100 ~ 1.333 | 700 |
| 20px | -0.020em | 1.400 ~ 1.600 | 400·700 |
| 18px | -0.022em | 1.400 | 400 |
| 16px | -0.013 ~ -0.020em | 1.438 ~ 1.750 | 400·700 |

- 웨이트 사용: **700(93회) / 400(48회)** — 사실상 2단 이진. 500은 3회뿐.
- `word-break: keep-all` 7회.
- 컨테이너 `980px`(224회) — 다른 곳보다 좁다. 브레이크포인트도 `980px`(216회) 단일. **데스크톱 퍼스트 + 980px 고정 그리드**라는 다소 구세대 구조.

### 실측 실패
`woowahan.com` HTML은 403(WAF). Jina Reader도 403. 헤드라인 카피 원문은 수집하지 못했다.

---

## 8. 센드버드 — sendbird.com/ko (글로벌 → 한국어 로컬라이즈)

**라틴 디자인을 한국어로 옮길 때 실제로 무엇을 바꾸는가**의 유일한 직접 증거.

기본(영문) 스택:
```css
font-family: 'Helvetica Now Text Medium', system-ui, -apple-system,
  'Segoe UI', Roboto, Ubuntu, Cantarell, 'Noto Sans', sans-serif;
/* 디스플레이: Gellix (Regular/Medium/SemiBold/Bold, 자체 호스팅 woff2) */
```
한국어 페이지 오버라이드(`custom-css/fork.css` 실측):
```css
.site-ko .fork-page__title .wysiwyg h1 {
  font-family: "Pretendard", "Noto Sans KR", sans-serif !important;
}
.default-layout.site-ko .fork-page__left .copy-block h2,
.default-layout.site-ko .fork-page__right .copy-block h2 {
  font-family: "Gellix", "Noto Sans KR", sans-serif;
  font-optical-sizing: auto;
}
```
- **로케일 클래스(`.site-ko`)로 헤드라인 서체만 갈아끼운다.** h1은 Pretendard로 완전 교체, h2는 Gellix를 유지하되 한글 폴백으로 Noto Sans KR을 붙인다(= 라틴 부분만 Gellix, 한글은 Noto).
- 자간은 `-0.2px`(21회)이 지배적 — 16px 기준 **-0.0125em**. 라틴 원본의 타이트한 트래킹을 한국어에서 완만하게 낮춘 값.
- 다만 h2에서 Gellix + Noto Sans KR을 섞는 방식은 **두 서체의 자폭·무게가 안 맞아 한글 부분이 뭉툭해 보이는** 전형적 실패 패턴이다. h1처럼 Pretendard로 통일하는 쪽이 낫다. (§10 공식 7 참고)

---

## 9. 나머지 확인 사항

| 서비스 | 한글 서체 | 비고 |
|---|---|---|
| 컬리 (kurly.com) | `'Pretendard', 'malgun gothic', 'AppleGothic', 'dotum', sans-serif` | Pretendard 단일 |
| 클래스101 (class101.net/ko) | `'Pretendard Variable', 'Pretendard JP Variable', 'Pretendard JP', Pretendard, system-ui, ...` | jsDelivr CDN의 **variable dynamic subset** 사용. 액센트 `#ff5d00`, 근검정 `#0c0c0c`. `min-width: 640/1024/1312px` → **모바일 퍼스트** |

### 줄바꿈 정책 전수 조사 (조사 대상 전체)

| 사이트 | `keep-all` | `break-word` | `pre-wrap` | `pre-line` | `break-all` |
|---|---:|---:|---:|---:|---:|
| 토스 | 8 | 6 | **14** | 0 | 1 |
| 당근 | **15** | 3 | **18** | 4 | 1 |
| 채널톡 | 8 | 14 | 4 | 2 | 21 |
| 29CM | 2 | 10 | 4 | 4 | 4 |
| 무신사 | 2 | 3 | 6 | 1 | 2 |
| 우아한형제들 | 7 | 1 | 0 | 3 | 3 |
| 리디북스 | 9 | 10 | 0 | 4 | 2 |
| 클래스101 | 1 | 3 | 1 | 2 | 2 |
| 센드버드 | 1 | 1 | 1 | 0 | 0 |

**10곳 전부가 `word-break: keep-all`을 쓴다. 예외 없음.** 한국어 웹에서 이건 선택 옵션이 아니라 리셋 CSS 수준의 전제다.

### 명조/세리프 사용 현황
전 사이트 CSS·HTML에서 `RIDIBatang / Nanum Myeongjo / Noto Serif KR / Source Han Serif / 본명조 / 고운바탕 / 마루부리 / Hahmlet` 을 전수 검색한 결과 — **실사용 0건.**
(유일한 히트는 ridibooks의 `ridibatang` 1회, 전자책 뷰어 폰트 선택 옵션으로 추정)

→ **한국 프리미엄 웹 랜딩에서 한글 세리프는 사실상 쓰이지 않는다.** 세리프는 출판·독서앱·긴 에세이의 영역이다. 랜딩에 명조를 쓰면 "고급"이 아니라 "예스러움/관공서"로 읽힐 위험이 있고, 실제로 아무도 그렇게 하지 않고 있다. (예외적으로 쓰려면 §11의 폰트 추천 참고 — 단, 디스플레이 1~2줄에 한정)

---

## 10. 한국어 프리미엄 조판의 공식 8가지

### 공식 1 — 자간: 본문 0 ~ -0.01em, 디스플레이 0 ~ -0.03em. **-0.04em이 절대 하한.**

| 크기대 | 권장 자간 | 근거 |
|---|---|---|
| 11~13px (캡션) | `-0.02em ~ -0.04em` | 당근 caption -0.04em / 채널톡 -0.008em |
| 14~18px (본문) | **`0` ~ `-0.01em`** | 채널톡 -0.01em(64회 최빈) / 리디 -0.01em(17회) / 토스·29CM·무신사 0 |
| 20~30px (서브헤드) | `0` ~ `-0.02em` | 당근 -0.03em(title) / 채널톡 -0.02em |
| 36px+ (디스플레이) | `-0.02em ~ -0.03em` | 채널톡 -0.02em / 우아한형제들 -0.03em / 당근 h1·h2 -0.04em |
| **금지** | `-0.05em 이하` | Pretendard 한글 좌우 여백 0.0566em의 88%가 소멸 |

- **자간은 반드시 `em`으로.** px 고정은 크기별로 의도치 않은 결과를 낸다(당근 §2 참조).
- 조사 대상 10곳 중 **4곳(토스·29CM·무신사·우아한형제들 대부분)은 자간이 그냥 0이다.** 확신이 없으면 0이 정답이다.
- 폰트별 하한 조정: Noto Sans KR은 여백이 0.087em로 넓어 -0.05em까지 견딘다. Pretendard/Wanted Sans는 -0.03em이 안전선.

### 공식 2 — 행간은 비율이 아니라 **고정 여백(leading)** 으로 잡는다.

```
행간(px) = 글자크기(px) + C
  랜딩·마케팅  C = 14 ~ 16px   (당근: 42→58, 36→52, 28→44)
  제품 UI      C = 8 ~ 10px    (토스 TDS: 18~29px 구간 전부 +9px)
  고밀도 커머스 C = 6px         (무신사 MDS: 13~42px 전부 +6px)
```

이 방식의 결과 = **크기가 커지면 비율이 자동으로 내려간다.** 최종 비율 대역:

| 크기 | 행간 비율 | 실측 출처 |
|---|---|---|
| 11~13px | 1.20 ~ 1.40 | 29CM 136%, 토스 1.5 |
| 14~18px | **1.50 ~ 1.62** | 토스 1.5·1.6 / 당근 body-l1 162% / 채널톡 1.53~1.59 / 29CM 140~150% |
| 20~30px | **1.36 ~ 1.45** | 토스 1.45~1.31 / 29CM 136% 고정 / 채널톡 1.33~1.40 |
| 36~48px | **1.30 ~ 1.38** | 토스 1.3 / 당근 1.381 / 채널톡 1.296~1.333 |
| 56px+ | **1.25 ~ 1.32** | 당근 히어로 64/84 = 1.313 |

**라틴 대비 +0.1~0.15를 더한 값이다.** 한글 글자가 베이스라인 아래로 -0.061em 내려가고 잉크 높이가 라틴 대문자의 1.20배이기 때문(§0-2). 라틴 레퍼런스에서 `leading-tight`(1.25)를 봤다면 한글은 1.35~1.4로 올려야 같은 인상이 된다.

**그리고 `line-height`를 반드시 명시하라.** Pretendard의 폰트 내장 기본 행간은 1.193이다.

### 공식 3 — `word-break: keep-all`은 리셋 수준의 필수 선언.

```css
:root, body, * {
  word-break: keep-all;      /* 어절 단위로만 줄바꿈 */
  overflow-wrap: break-word; /* 단, 긴 URL·영문 단어는 깨뜨림 */
}
```
조사 대상 **10곳 전부** 사용. 토스는 아예 `body` 리셋에 넣었다.
이게 없으면 "축복가정 안내"가 "축복가정 안/내"로 잘려서 인상이 즉시 무너진다. 한글은 모든 글자 사이가 잠재적 줄바꿈 지점이라 기본값(`normal`)이 CJK에서 어절을 무시하기 때문.

### 공식 4 — 헤드라인 줄바꿈은 CSS가 아니라 사람이 정한다. 한 줄 6~12자.

```css
.headline { white-space: pre-wrap; }  /* 토스 14회, 당근 18회 사용 */
```
실측 규범:
- **헤드라인 한 줄 = 6~12자 / 1~4어절.** (토스 실측 3~12자, 당근 2~15자)
- **헤드라인은 2~3줄.** 1줄이면 힘이 없고 4줄이면 카피가 긴 것이다.
- 첫 줄을 짧게, 마지막 줄을 길게 하거나 그 반대로 — **줄 길이를 일부러 어긋나게** 놓는다. (`투자, / 모두가 할 수 있도록`, `당근은 매일 / 새로운 역사를 쓰고 있어요`)
- 반응형에서 개행 위치가 바뀌어야 하면 `<br class="pc-only">` 대신 브레이크포인트별로 다른 텍스트 노드를 쓰거나, 컨테이너에 `max-width`를 걸어 자연 줄바꿈을 유도한다(당근: 헤드라인 자체에 `max-width: 1152px`).

### 공식 5 — 웨이트는 400 / 500 / 700 3단. 100~300은 본문 금지.

| 사이트 | 실제 사용 웨이트 (빈도순) |
|---|---|
| 토스 | **500**(38) · 700(25) · 400(17) · 600(15) |
| 당근 | 700(17) · 400(8) — **폰트가 400/700/900만 제공** |
| 채널톡 | 400(50) · 600(32) · 500(15) · 700(14) |
| 29CM | 700(70) · 400(44) · 500(40) · 600(5) |
| 무신사 | **500**(24) · 400(16) · 600(14) · 700(3) |
| 우아한형제들 | 700(93) · 400(48) — **사실상 2단** |

권장 페어링:
```
디스플레이 700 (또는 800)   ↕ 큰 점프
서브헤드   600 또는 700
본문       400  (또는 한글 UI에서는 500)
보조·캡션  400
비활성     400 + 밝은 그레이 (얇은 웨이트로 죽이지 말 것)
```
- **한글은 400이 라틴보다 얇아 보인다.** 토스·무신사 둘 다 UI 기본을 **500(Medium)** 으로 올렸다. 밝은 배경의 작은 글씨라면 500이 안전하다.
- **100~300(Thin/Light)은 한글 본문에 절대 쓰지 않는다.** 획이 가늘어 자모가 뭉개진다. 29CM이 토큰으로는 100~300을 가지고 있지만 실사용은 2회뿐이다.
- 웨이트 대비는 **크게** 준다. 400↔700(당근·우아한형제들)이 400↔500↔600↔700 4단보다 결과가 낫다. 한글은 중간 웨이트 간 차이가 눈에 잘 안 띈다.

### 공식 6 — 검정을 쓰지 않는다. 근검정 + 냉기 있는 그레이 램프.

| 사이트 | 본문 최암부 | 성격 |
|---|---|---|
| 토스 | `#191f28` | 파랑 기운(hue 218°) |
| 당근 | `#1a1c20` | 아주 약한 냉기 |
| 채널톡 | `#242428` | 중성 |
| 29CM | `#19191a` | 거의 완전 무채색 |
| 무신사 | `#2a2a2a` | 무채색 |
| 클래스101 | `#0c0c0c` | 가장 어두움 |

**조사 대상 어디도 `#000`을 본문에 쓰지 않는다.**

토스의 10단 램프를 그대로 참고할 만하다 — 파랑 쪽으로 3~5° 틀어놓으면 "정돈된 차가움"이 나온다:
```
900 #191f28  800 #333d4b  700 #4e5968  600 #6b7684  500 #8b95a1
400 #b0b8c1  300 #d1d6db  200 #e5e8eb  100 #f2f4f6   50 #f9fafb
```
운용 규칙(토스 실측):
- 제목 = 800(`#333d4b`) 또는 900, **본문 = 700(`#4e5968`)**. 본문에 최암부를 쓰지 않는다.
- 배경은 `#fff` ↔ `#f2f4f6` 교대. 그림자·보더 대신 **배경색 교대로 섹션을 나눈다.**
- 액센트는 **한 색만**. 토스 `#3182f6`, 29CM `#375fff`, 무신사 `#245eff`, 당근 `#ff7e36`, 클래스101 `#ff5d00`, 채널톡 `#5e56f0`.
- 컬러를 텍스트에 쓰지 말고 **아주 옅은 배경 필드**로 쓴다(당근 `#fff5f0` `#e8faf6` `#ebf7fa`).

### 공식 7 — 국문·영문을 **한 폰트로 통일한다.** 분리는 예외.

실측 결과:

| 전략 | 사이트 |
|---|---|
| **단일 서체(전용)** | 토스(Toss Product Sans) · 당근(Karrot Sans) |
| **단일 서체(Pretendard)** | 29CM · 무신사 · 컬리 · 클래스101 · 채널톡(ko) |
| **본문 Pretendard + 디스플레이 브랜드체** | 우아한형제들(BM 배민체 11종) |
| **국·영문 분리** | 리디(한글 Pretendard + 라틴 ridi-roboto) · 채널톡(다국어 페이지 Inter+Noto) · 센드버드(Gellix/Helvetica Now + `.site-ko`에서 Pretendard) |

- **기본값은 단일 서체다.** Pretendard는 라틴 글리프가 Inter 계열로 잘 만들어져 있어 굳이 나눌 이유가 없다.
- 나눠야 한다면 리디처럼 **한글 = 중성 산세리프 / 라틴·숫자 = 별도 폰트**로 명확히 분리하되, 두 폰트의 x-height와 웨이트를 반드시 맞춰라. 센드버드의 `Gellix + Noto Sans KR` 혼용처럼 안 맞으면 한글 쪽이 뭉툭하게 튄다.
- **브랜드 서체가 있다면 디스플레이에만.** 우아한형제들도 본문은 Pretendard다.
- 다국어 확장 시엔 무신사 패턴 — 로캘별로 스택을 갈아끼우고 Pretendard를 폴백 뒤로 민다.
- 숫자는 별도 처리 필요 시 `font-variant-numeric: tabular-nums`만 추가한다(가격·통계 정렬).

### 공식 8 — 컨테이너 1140~1280px, 본문 단 640~800px, 한 줄 25~45자.

측정된 컨테이너 폭:

| 사이트 | 컨테이너 | 텍스트 단 |
|---|---|---|
| 토스 | 1140px | — |
| 당근 | **1152px** | 헤드라인 1152px / 카드 570px |
| 채널톡 | 1280px (서브 1160·1320) | — |
| 29CM | 1280 / 1040 / 1025px | — |
| 무신사 | 1279px | — |
| 우아한형제들 | 980px | 780 / 680px |

**한 줄 글자수 산출 공식** (§0 실측 자폭 기반):
```
한글 평균 자폭 = 0.864em (글자) , 0.251em (공백)
한국어 문장은 어절 평균 2.7자 → 문자당 평균 자폭 ≈ 0.70em

한 줄 최대 글자수 ≈ 컨테이너 폭 ÷ (0.70 × font-size)
```
| 단 폭 | 본문 크기 | 이론상 한 줄 |
|---:|---:|---:|
| 640px | 16px | 57자 |
| 720px | 17px | 60자 |
| 800px | 18px | 63자 |

**하지만 실제 디자이너들은 그 절반에서 끊는다.** 토스 본문 수동 개행 라인 중앙값 **12자**, 당근 **14자**. 문단 텍스트는 이론상 57자가 가능해도 실제 편안한 한국어 measure는 **25~45자**다.

권장:
- 본문 단 `max-width: 640~720px` (16~17px 기준 → 40~45자 부근에서 자연 줄바꿈)
- 헤드라인 컨테이너는 넓게 두되(1140~1152px) **수동 개행으로 6~12자씩 끊는다**
- 페이지 컨테이너 **1152px** 또는 **1280px**
- 브레이크포인트 **640 / 1024 / 1280px** (당근·토스·클래스101 공통)
- 데스크톱 퍼스트(토스·당근·무신사·우아한형제들) vs 모바일 퍼스트(29CM·클래스101·채널톡 일부) — **국내 랜딩은 아직 데스크톱 퍼스트가 근소 우세.** 다만 최근 스택(Next.js 기반: 29CM·클래스101)일수록 모바일 퍼스트다.

---

## 11. 무료 임베딩 가능 한글 서체 — 성격별 추천

> 라이선스는 **전부 1차 출처(폰트 파일의 `name` 테이블, 공식 GitHub LICENSE, Google Fonts METADATA.pb, 배포처 공식 페이지)에서 직접 확인**했다. 각 행 끝에 근거 URL을 붙였다.

### 라이선스 총괄표

| 폰트 | 라이선스 | woff2 임베딩 | 웨이트 | 가변 | 공식 배포 | 한글 자폭(실측) |
|---|---|---|---:|---|---|---:|
| **Pretendard** | SIL OFL 1.1 | ✅ 공식 CDN | 9 | ✅ 45–920 | jsDelivr `orioncactus/pretendard` | 0.8643em |
| **Wanted Sans** | SIL OFL 1.1 | ✅ 공식 CDN + 동적 서브셋 | 7 | ✅ | jsDelivr `wanteddev/wanted-sans` | **0.8643em (동일)** |
| **SUIT** | SIL OFL 1.1 | ✅ 공식 woff2 zip + jsDelivr | 9 | ✅ 100–900 | `sun-typeface/SUIT` | 0.8740em |
| **IBM Plex Sans KR** | SIL OFL 1.1 (RFN "Plex") | ✅ Google Fonts | 7 (100–700) | ❌ (가변은 라틴만) | Google Fonts / `IBM/plex` | 미측정 |
| **마루 부리** | SIL OFL 1.1 (네이버, RFN `MaruBuri`) | ✅ **네이버 공식 웹폰트 CSS** | 5 | ❌ | `hangeul.pstatic.net/hangeul_static/css/maru-buri.css` | 미측정 |
| **고운바탕** | SIL OFL 1.1 | ✅ Google Fonts | **2 (400/700)** | ❌ | Google Fonts / `yangheeryu/Gowun-Batang` | 0.9300em |
| **Hahmlet** | SIL OFL 1.1 | ✅ Google Fonts | 9 | ✅ 100–900 | Google Fonts / `hyper-type/hahmlet` | 미측정 |
| **Noto Serif KR** | SIL OFL | ✅ Google Fonts | 가변 1파일 | ✅ 200–900 | Google Fonts | 미측정 |
| **Nanum Myeongjo** | SIL OFL | ✅ Google Fonts | 3 (400/700/800) | ❌ | Google Fonts | 미측정 |
| **Noto Sans KR** | SIL OFL | ✅ Google Fonts | 가변 | ✅ | Google Fonts | 0.9200em |
| **RIDIBatang** | SIL OFL 1.1 | ⚠️ **공식은 OTF 단일** → woff2 자가 변환 | **1 (Regular)** | ❌ | ridicorp.com/ridibatang/ | 미측정 |
| **Paperlogy** | SIL OFL | ⚠️ **공식은 TTF만** → 서드파티 woff2 경유 | 9 | ❌ | **freesentation.blog** (한국출판인회의 아님) | 미측정 |
| **Nanum Gothic Coding** | SIL OFL | ✅ Google Fonts | 2 | ❌ | Google Fonts | 미측정 |
| **D2Coding** | SIL OFL | ⚠️ **공식은 TTF만** | 2 ×2빌드 | ❌ | `naver/d2-coding-font` | 미측정 |

**OFL 공통 의무 (위 전 항목 동일)**: ① 폰트 파일 단독 판매 금지 ② 저작권 고지 + 라이선스 전문 동봉 ③ 파생물도 OFL 유지 ④ Reserved Font Name을 파생물 이름에 사용 금지. **웹페이지 임베딩·상용 제품 번들은 전부 허용** (Google Fonts 공식 FAQ: "you can use them commercially, and even include them within a product that is sold commercially").

### 본문용 산세리프 (1순위)

**Pretendard** — SIL OFL 1.1 *(폰트 파일 `name` ID 13을 직접 읽어 확인: "This Font Software is licensed under the SIL Open Font License, Version 1.1")*
- 9웨이트(100~900) + Variable(45~920). 변종: Std(라틴 최적화) / JP / GOV(공공)
- 한글 자폭 0.8643em, 좌우 여백 0.0566em → **자간 안전 하한 -0.03em, 절대 하한 -0.04em**
- 폰트 내장 기본 행간 1.193 → `line-height` 필수 명시
- CDN(가변 동적 서브셋, 클래스101·29CM 실사용 확인):
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
  ```
- **조사 대상 10곳 중 7곳이 쓴다.** 사실상 한국 웹의 기본값. 안전하지만 동시에 "차별화 없음"을 의미하므로, 차별화는 크기·여백·색으로 만들어야 한다.

**Wanted Sans** — SIL OFL 1.1 (`wanteddev/wanted-sans/OFL.txt`: "Copyright 2024 The Wanted Sans Project Authors"). 기본 7굵기 + 가변. 공식 jsDelivr 웹폰트 + 동적 서브셋 제공.
- 폰트 메트릭 실측 결과 **Pretendard와 한글 자폭이 완전히 동일**(2048 upm / 1770 units / 0.8643em). 잉크 폭·'H' 높이·기본 행간까지 일치.
- → **Pretendard와 메트릭 호환.** `font-family` 한 줄만 바꿔도 레이아웃이 밀리지 않는다. **차별화가 필요한데 리스크는 지고 싶지 않을 때 최적의 선택.**
- 라이선스 문구도 관대: "글꼴 단독 판매 및 글꼴 라이선스 변경을 제외한 모든 상업적 행위·수정·재배포 가능"

**SUIT** — SIL OFL 1.1 (`sun-typeface/SUIT/LICENSE`). 9웨이트(Thin~Heavy) + `SUIT-Variable.woff2`(`font-weight: 100 900`).
- 한글 자폭 0.8740em, **좌우 여백 0.0680em (Pretendard보다 20% 넉넉)** → 자간을 **-0.034em까지** 안전하게 줄 수 있다. 기본 행간 1.248.
- 한글 글리프가 본고딕 기반이라 Pretendard보다 약간 넓고 부드럽다. **자간을 좀 조이고 싶은 디스플레이 조판이라면 Pretendard보다 SUIT가 낫다.**

**IBM Plex Sans KR** — SIL OFL 1.1 (RFN "Plex", © 2017 IBM Corp.). 정적 7웨이트(100~700). **가변폰트 없음** — IBM 레포에 `plex-sans-variable`은 있으나 KR 패키지에는 가변이 없다. 기술·개발자 톤이 필요할 때.

### 디스플레이 / 브랜드용

**Paperlogy** — ⚠️ **본문용 아님. 이 프로젝트에서는 사용 금지 권고.**
- 배포처 정정: **한국출판인회의(pagi.or.kr)가 아니다.** 해당 도메인은 DNS 미해석(NXDOMAIN). 실제 1차 배포처는 `freesentation.blog`이고 크레딧은 이주임(피티꾼)·김도균이다.
- 공식 페이지가 스스로 **"프레젠테이션을 위한 두 번째 폰트", "파워포인트에서 사용하면 좋은 폰트"** 라고 규정한다. 한글 베이스는 **G마켓산스**(디스플레이 성향 산스)를 자폭 5% 좁힌 파생, 라틴은 Montserrat, 일본어는 M PLUS 2.
- 라이선스는 SIL OFL로 문제없으나 **공식 배포 포맷이 TTF뿐**이라 웹에는 서드파티 아카이브(`fonts-archive/Paperlogy`)를 경유하거나 자가 변환해야 한다.
- 이 조사 대상 10개 사이트 **어디에서도 사용 흔적이 없다.**

**브랜드 서체를 도입한다면 우아한형제들 패턴을 따르라**: 디스플레이 1~2줄에만 쓰고, 본문·UI는 전부 중성 산세리프로.

### 세리프 / 명조

**마루 부리(MaruBuri)** — 한글 세리프 중 **웹 도입이 가장 쉽다.**
- 네이버 글꼴 라이선스 = SIL OFL 1.1 (RFN 목록에 `MaruBuri` 명시). 수정·재배포·상용 번들 자유, 폰트 단독 유료판매만 금지.
- **네이버가 공식 웹폰트 CSS + woff2를 직접 서빙**한다: `https://hangeul.pstatic.net/hangeul_static/css/maru-buri.css`
- **5웨이트**(ExtraLight/Light/Regular/SemiBold/Bold) — 세리프 중 유일하게 위계를 제대로 만들 수 있다. 네이버가 "용도: 본문용"으로 분류.
- 가변폰트는 없음(네이버 CDN에 variable 파일 404).

**고운바탕(Gowun Batang)** — SIL OFL 1.1. **2웨이트(400/700)뿐.**
- 폰트 메트릭 실측: 자폭 0.9300em, 여백 0.0699em, '한' 잉크 높이 0.915em, 기본 행간 1.448.
- 자폭이 Pretendard보다 **7.6% 넓다** → 같은 글자수에 더 넓은 컨테이너가 필요하고, 산세리프와 섞어 쓰면 줄바꿈이 어긋난다.
- 기본 행간 1.448로 여유가 있어 `line-height`를 깜빡해도 덜 망가진다.

**Hahmlet(함렡)** — SIL OFL 1.1, **가변 `wght 100–900`**. 세리프 중 유일하게 가변폰트가 제대로 제공된다. 디스플레이에서 굵기를 미세 조정하고 싶을 때.

**Noto Serif KR** — SIL OFL, 가변 `wght 200–900`. **Nanum Myeongjo** — SIL OFL, 3웨이트(400/700/800).

**RIDIBatang** — SIL OFL 1.1이고 리디 공식 페이지가 "자유롭게 수정하고 재배포" 명시. 단 ⚠️ **굵기 1종(Regular)뿐이고 공식 배포가 OTF 단일 파일**이다. 볼드 위계를 못 만들므로 본문 세리프로는 부적합. 인용문·에피그래프 한 덩어리에만.

**⚠️ 다만 §9 실측대로 한국 프리미엄 랜딩에서 한글 명조 실사용은 0건이다.** 쓴다면 디스플레이 한 줄이나 인용문에 한정하고, 본문은 반드시 산세리프로. 명조는 "고급"이 아니라 "예스러움/관공서"로 읽힐 위험이 있다.

### 다국어 폴백
- **Noto Sans KR** — 자폭 0.9200em, 여백 **0.0870em(측정한 것 중 가장 넉넉)** → 자간을 -0.05em까지 견딘다. 기본 행간 1.448. 전용 서체가 없는 환경의 폴백으로 견고하다. 단 자폭이 Pretendard보다 6.4% 넓어 폴백으로 쓰면 FOUT 시 레이아웃이 밀린다.
- **폴백 시프트 방지**: 채널톡처럼 `'Pretendard Fallback'` 같은 메트릭 오버라이드 폰트(`@font-face { size-adjust; ascent-override; descent-override }`)를 정의하는 게 정석.
- **Google Fonts 한글은 unicode-range 분할 서브셋**으로 서빙된다(고운바탕 400 하나만으로도 `@font-face` 블록이 수백 개). 자체 호스팅으로 옮기면 이 최적화가 사라져 파일이 통째로 커진다는 점을 Google 공식 FAQ가 명시한다.

### 모노스페이스 (한글 글리프 포함)

| 후보 | 한글 | 라이선스 | 웨이트 | 판단 |
|---|---|---|---:|---|
| **Nanum Gothic Coding** | ✅ (`subsets: korean`) | SIL OFL | 2 (400/700) | **웹에 가장 쉬움** — Google Fonts CSS2 API가 그대로 서빙. 한자 없음 |
| **D2Coding** | ✅ 한글 11,172자 전부 + 한자 4,620자 | SIL OFL | 2 ×(표준/ligature) | 코드 정렬 최적(한글 = 라틴 2배폭). ⚠️ **공식 배포 TTF만** → woff2 자가 변환 필요 |
| **Sarasa Mono K** | ✅ (본고딕 K 기반) | SIL OFL | 다수 | 파일 용량이 매우 큼. 웹폰트로는 서브셋 필수 |
| ~~IBM Plex Mono~~ | ❌ | — | — | **한글 없음.** Google Fonts subsets가 `cyrillic/latin/vietnamese`뿐 |

- 웹에서 CDN 한 줄로 끝내려면 **Nanum Gothic Coding**, 코드·터미널 정렬 품질이 중요하면 **D2Coding**.
- 표·가격 정렬 목적이라면 모노를 도입하지 말고 **`font-variant-numeric: tabular-nums`** 로 숫자만 정렬하는 편이 낫다. Pretendard도 지원한다.

### woff2 자가 변환이 필요한 폰트 (빌드 단계 추가 주의)
**Paperlogy**(공식 TTF만) · **RIDIBatang**(공식 OTF만) · **D2Coding**(공식 TTF만). OFL이 포맷 변환을 "Modified Version"으로 허용하므로 합법이지만 파이프라인이 늘어난다.

---

## 12. 헤드라인 카피 문형 표본 10 + 문형 분류

전부 **2026-08-06 실제 사이트에서 수집한 원문**이다.

| # | 원문 (`/` = 실제 줄바꿈 위치) | 출처 | 어절 | 문형 |
|---:|---|---|---:|---|
| 1 | **금융을 넘어 / 일상을 더 편리하게** | toss.im | 5 | **B. 부사형 미완결 종결** — 문장을 끝내지 않고 `~하게`로 끊는다 |
| 2 | **내 돈 관리, / 지출부터 일정까지 / 똑똑하게** | toss.im | 6 | B. 명사구 + 범위(`~부터 ~까지`) + 부사형 종결 |
| 3 | **투자, / 모두가 할 수 있도록** | toss.im | 5 | B. 주제어 단독 배치 + 연결어미 `~도록` |
| 4 | **동네를 여는 문, / 당근** | team.daangn.com | 4 | **A. 명사형 종결 + 브랜드명 동격 배치** |
| 5 | **우리에게 동네의 연결이 / 필요한 이유** | team.daangn.com | 5 | A. 명사형 종결(`~한 이유`) — 다음 섹션을 여는 장치 |
| 6 | **당근은 매일 / 새로운 역사를 쓰고 있어요** | team.daangn.com | 5 | **E. 해요체 서술(진행형)** — 브랜드 서사 |
| 7 | **고객 상담에 최적화된 AI 솔루션** | channel.io/ko | 4 | A. 명사형 종결 — 라틴 약어를 번역하지 않고 그대로 |
| 8 | **앵무새 답변이 아니라 직접 실행까지** | channel.io/ko | 5 | **B. 조사 종결(`~까지`)** + 대조 구문(`~이 아니라 ~`) |
| 9 | **강력한 연동, 쓰시는 플랫폼 계속 쓰셔도 됩니다** | channel.io/ko | 7 | **D. 합니다체 단정** — B2B 톤 |
| 10 | **여러 은행의 조건을 / 1분 만에 / 확인해보세요** | toss.im | 6 | **C. 해요체 청유(CTA)** + 숫자 삽입 |
| 보 | **감도 깊은 취향 셀렉트샵** | 29cm.co.kr | 3 | A. 명사형 종결 — 형용사구 2개 중첩 |
| 보 | **보기만 해도 기분이 좋아지는 색. / 레몬빛으로 우리 집에 생기를 불어넣어요.** | content.29cm.co.kr | 9 | E. 명사 종결 문장 + 해요체 문장의 2단 구성 |
| 보 | **원하는 모든 것, 나답게 배우다** | class101.net/ko | 4 | **F. 해라체 서술형(`~다`)** — 선언형, 슬로건 톤 |

### 문형 5분류 (실측 기반)

| 코드 | 문형 | 어미 | 쓰는 곳 | 인상 |
|---|---|---|---|---|
| **A** | 명사형 종결 | `~솔루션` `~이유` `~문` `~셀렉트샵` | 섹션 타이틀, 기능명 | 단정적·정보적. 가장 안전 |
| **B** | 부사형·연결어미 미완결 종결 | `~하게` `~도록` `~까지` `~부터` | **메인 헤드라인** | **세련됨의 핵심 장치.** 문장을 끝내지 않아 여운이 남는다 |
| **C** | 해요체 청유 | `~하세요` `~해 보세요` | CTA, 기능 유도 | 친근·행동 유도 |
| **D** | 합니다체 단정 | `~합니다` `~됩니다` | **B2B 본문** | 신뢰·전문. B2C에 쓰면 딱딱함 |
| **E** | 해요체 서술 | `~해요` `~어요` `~거예요` | **B2C 본문·브랜드 서사** | 따뜻함. 토스·당근 본문 100% |
| **F** | 해라체 선언 | `~다` `~하다` | 슬로건 한 줄 | 강한 선언. 남발하면 광고 카피 티가 남 |

### 실무 규칙 요약
1. **B2C면 본문 전부 `~해요`. B2B면 전부 `~합니다`.** 섞지 마라. 토스·당근은 `~합니다`가 한 번도 안 나오고, 채널톡은 `~해요`가 CTA 외에 안 나온다.
2. **메인 헤드라인은 문장을 끝내지 마라.** `~하게` `~도록` `~까지`로 끊는 게 가장 세련되게 읽힌다(공식 B). 완결 문장은 서브카피에 둔다.
3. **어절 3~6개.** 7어절을 넘으면 헤드라인이 아니라 문장이다.
4. **주제어를 쉼표로 떼어 첫 줄에 단독 배치**하는 구조가 반복된다(`투자,` / `내 돈 관리,` / `동네를 여는 문,` / `강력한 연동,`). 리듬이 생기고 첫 줄이 짧아 조판도 안정된다.
5. **숫자를 넣으면 힘이 붙는다** — `1분 만에`, `상담 80%를`, `일주일 넘게 걸리던 분석을 5분만에`.
6. **영문 약어는 번역하지 않는다** — `AI`, `All-as-One`, `PT`, `Showcase`. 다만 문장 안에 섞을 뿐 한글 카피를 영문으로 대체하지는 않는다(29CM은 네비게이션만 영문).

---

## 13. 이 프로젝트에 바로 적용할 CSS 골격

```css
:root {
  /* 서체 — 단일 스택 (공식 7) */
  --font-sans: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont,
    system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo',
    'Malgun Gothic', sans-serif;

  /* 크기 — 토스/당근 실측 기반 */
  --fs-display: 56px;  --fs-h1: 42px;  --fs-h2: 32px;  --fs-h3: 24px;
  --fs-h4: 20px;       --fs-lead: 18px; --fs-body: 16px; --fs-sm: 14px; --fs-xs: 13px;

  /* 행간 — 글자크기 + 고정 여백 (공식 2) */
  --lh-display: 1.28;  /* 56 → 72px */
  --lh-h1: 1.36;       /* 42 → 57px */
  --lh-h2: 1.38;       /* 32 → 44px */
  --lh-h3: 1.42;       /* 24 → 34px */
  --lh-body: 1.60;     /* 16 → 26px */
  --lh-lead: 1.62;     /* 18 → 29px */

  /* 자간 — em only, -0.04em 하한 (공식 1) */
  --ls-display: -0.03em;
  --ls-heading: -0.02em;
  --ls-body: -0.01em;
  --ls-none: 0;

  /* 색 — 근검정 + 냉기 그레이 (공식 6) */
  --ink-900: #191f28;  --ink-800: #333d4b;  --ink-700: #4e5968;
  --ink-600: #6b7684;  --ink-500: #8b95a1;  --ink-400: #b0b8c1;
  --ink-300: #d1d6db;  --ink-200: #e5e8eb;  --ink-100: #f2f4f6;  --ink-50: #f9fafb;
  --surface: #fff;     --surface-alt: #f2f4f6;

  /* 레이아웃 (공식 8) */
  --container: 1152px;
  --measure: 680px;   /* 본문 단 → 16px 기준 약 42자 */
}

/* 필수 리셋 (공식 3) */
html { font-family: var(--font-sans); }
body {
  word-break: keep-all;
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  letter-spacing: var(--ls-body);
  color: var(--ink-700);          /* 본문에 최암부를 쓰지 않는다 */
  background: var(--surface);
}

/* 헤드라인 — 사람이 줄을 끊는다 (공식 4) */
.headline {
  font-size: var(--fs-h1);
  line-height: var(--lh-h1);
  letter-spacing: var(--ls-heading);
  font-weight: 700;               /* 400 ↔ 700 큰 점프 (공식 5) */
  color: var(--ink-900);
  white-space: pre-wrap;          /* 원문의 개행을 그대로 지킨다 */
  max-width: var(--container);
}
@media (max-width: 640px) { .headline { font-size: 28px; line-height: 1.5; } }

p { max-width: var(--measure); }
```

---

## 14. 한 문장 요약

한국어 프리미엄 조판은 **라틴에서 빼는 것(자간)을 빼지 않고, 라틴에서 안 주는 것(행간·어절 보호·수동 개행)을 준다.** Pretendard 한글의 좌우 여백은 라틴의 60%뿐이라 `-0.05em`은 파괴적이고, 글자 잉크는 라틴 대문자의 1.20배에 베이스라인 아래까지 내려가 행간 1.5~1.6을 요구한다. 나머지는 색을 검정 대신 냉기 있는 근검정으로, 웨이트를 400↔700 큰 점프로, 헤드라인을 6~12자씩 사람 손으로 끊는 일이다.

---

## 부록 A. 실측 소스 목록

### 사이트 CSS (전량 직접 다운로드, 2026-08-06)
| 사이트 | 취득 파일 | 크기 | 취득 방법 |
|---|---|---:|---|
| 토스 | `static.toss.im/tds/42.61.2/css/tds.min.css` | 143,799 B | curl (UA 위장) |
| 토스 | `static.toss.im/tds-pc/3.257.0/main.css` | 210,106 B | curl |
| 토스 | `static.toss.im/fonts/all.css` | 4,420 B | curl |
| 토스 | `assets-fe.toss.im/tds/style.css` | 10,605 B | curl |
| 당근 | `team.daangn.com/styles.c88a01e792330d680d2a.css` | 61,685 B | curl |
| 당근 | `assets.krrt.io/daangn/branding-assets/0.0.2/typography/fonts/KarrotSans.css` | 643 B | curl |
| 채널톡 | `channel.io/_next/static/chunks/0394n6n63i8rr.css` + `05nge14tpntpn.css` | 38,454 B | curl |
| 리디 | `ridibooks.com` (HTML 인라인 CSS) | 630,727 B | **curl_cffi (403 우회)** |
| 리디 | `ridicorp.com/ko/` + `forced-style.css` | 74,816 B | **curl_cffi (403 우회)** |
| 29CM | `cdn-resource-microservice.29cm.co.kr/home/v1/...css` ×4 | 209,082 B | curl_cffi |
| 29CM | `cdn-resource-microservice.29cm.co.kr/content/v1/...css` | 212,715 B | curl_cffi |
| 무신사 | `static.msscdn.net/static/cached/mds/2.0.0/mds@ced53515d6d8.css` 외 2 | 107,938 B | curl_cffi |
| 우아한형제들 | `woowahan-cdn.woowahan.com/static/css/chunk-common.554ed250.css` | 172,180 B | curl_cffi |
| 센드버드 | `sendbird.com/_nuxt/css/a08a542.css` + `custom-css/fork.css` + `fonts/*.css` | 274,000 B | curl_cffi |
| 클래스101 | `class101.net/_next/static/css/6a7a9a3ea06d2df4.css` | 135,182 B | curl_cffi |
| 컬리 | HTML만 (CSS 런타임 생성) | 16,053 B | curl_cffi |

### 폰트 파일 (fontTools로 메트릭 직접 측정)
- `Pretendard-Regular.otf` — jsDelivr `npm/pretendard@1.3.9/dist/public/static/`
- `SUIT-Regular.otf` — jsDelivr `gh/sun-typeface/SUIT@2/fonts/static/otf/`
- `WantedSans-Regular.otf` — jsDelivr `gh/wanteddev/wanted-sans@v1.0.3/packages/wanted-sans/fonts/otf/`
- `Gowun Batang 400` / `Noto Sans KR 400` — jsDelivr `fontsource/fonts/*/korean-400-normal.woff`

### 라이선스 1차 출처
- Pretendard: 폰트 `name` 테이블 ID 13/14 직접 판독
- Gowun Batang / Hahmlet / IBM Plex Sans KR / Nanum Myeongjo / Noto Serif KR / Nanum Gothic Coding: `raw.githubusercontent.com/google/fonts/main/ofl/*/METADATA.pb`
- 마루 부리: `help.naver.com/service/30016/contents/18088` + `hangeul.pstatic.net/hangeul_static/css/maru-buri.css` (HTTP 200 확인)
- SUIT: `raw.githubusercontent.com/sun-typeface/SUIT/main/LICENSE`
- Wanted Sans: `raw.githubusercontent.com/wanteddev/wanted-sans/main/OFL.txt`
- Paperlogy: `freesentation.blog/paperlogyfont` — **`pagi.or.kr`은 NXDOMAIN으로 확인됨(배포처 전제 오류)**
- RIDIBatang: `ridicorp.com/ridibatang/`
- D2Coding: `github.com/naver/d2-coding-font` (`api.github.com/.../contents/fonts` → `ttf/`만 존재)
- OFL 상업 이용 가부: `fonts.google.com/faq`

### 미측정·실패 항목 (재조사 시 우선순위)
1. `woowahan.com` HTML 403 — 헤드라인 카피 원문 미수집. Playwright 실브라우저로 재시도 필요
2. `ridicorp.com` 브랜드/채용 페이지 조판 — WordPress라 토큰 부재
3. 올리브영 — 봇 차단(2.4KB 응답)
4. 컬리·클래스101 — CSS 토큰이 런타임 생성이라 수치 미측정(폰트 스택만 확인)
5. 마루 부리 / Hahmlet / IBM Plex Sans KR / Noto Serif KR의 한글 자폭·좌우 여백 미측정 — §0 표에 추가하면 자간 하한 계산이 완성됨
