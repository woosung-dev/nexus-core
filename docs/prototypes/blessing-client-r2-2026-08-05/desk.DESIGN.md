---
version: alpha
name: 창구 (The Desk)
description: >
  블레싱 네비게이션 클라이언트의 공적 창구 변형. 정부24의 정보 구조를 토스의 손끝
  정밀도로 다시 짠 민원 창구. 그림자 0, radius 8px 단일값, 두 굵기만 쓰는 활자, 그리고
  답변 문장과 근거 원문이 서로를 가리키는 양방향 하이라이트. 색은 브랜드 바이올렛이
  행동을 맡고, 골드는 오직 검증된 근거 한 곳에만 나타난다.
colors:
  paper: "#F4F7FB"
  surface: "#FFFFFF"
  surface-sunk: "#E9EFF7"
  ink: "#0E1A2E"
  ink-2: "#33445E"
  ink-3: "#5A6A82"
  brand: "#00337A"
  brand-press: "#00234F"
  brand-tint: "#E3EBF7"
  on-brand: "#FFFFFF"
  gold: "#C08A1E"
  gold-ink: "#7A5600"
  gold-tint: "#FAF0D8"
  hairline: "#DCE4EF"
  hairline-strong: "#BCC9DB"
  danger: "#9A1C14"
  danger-tint: "#FBECEA"
  focus: "#00337A"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-paper: "#0B1220"
  dark-surface: "#131C2E"
  dark-surface-sunk: "#0E1626"
  dark-ink: "#E6ECF5"
  dark-ink-2: "#A9B7CC"
  dark-ink-3: "#82909F"
  dark-brand: "#8FB4F0"
  dark-gold: "#E0B95E"
  dark-hairline: "#222E44"
  hc-paper: "#FFFFFF"
  hc-ink: "#000814"
  hc-brand: "#00234F"
  hc-hairline: "#000814"
typography:
  display:
    fontFamily: Pretendard Variable
    fontSize: 34px
    fontWeight: "700"
    lineHeight: 1.4
    letterSpacing: 0.5px
  heading-lg:
    fontFamily: Pretendard Variable
    fontSize: 24px
    fontWeight: "700"
    lineHeight: 1.5
    letterSpacing: 0
  heading-md:
    fontFamily: Pretendard Variable
    fontSize: 19px
    fontWeight: "700"
    lineHeight: 1.5
    letterSpacing: 0
  heading-sm:
    fontFamily: Pretendard Variable
    fontSize: 17px
    fontWeight: "700"
    lineHeight: 1.5
    letterSpacing: 0
  body:
    fontFamily: Pretendard Variable
    fontSize: 17px
    fontWeight: "400"
    lineHeight: 1.7
    letterSpacing: 0
  body-sm:
    fontFamily: Pretendard Variable
    fontSize: 15px
    fontWeight: "400"
    lineHeight: 1.65
    letterSpacing: 0
  caption:
    fontFamily: Pretendard Variable
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 1.55
    letterSpacing: 0
    fontFeature: "tnum"
rounded:
  none: 0
  DEFAULT: 8px
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  gutter: 24px
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.on-brand}"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.md}"
    height: 56px
  button-primary-pressed:
    backgroundColor: "{colors.brand-press}"
    textColor: "{colors.on-brand}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.DEFAULT}"
    height: 56px
  text-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.md}"
    height: 56px
  text-input-focused:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
  evidence-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.md}"
  evidence-card-linked:
    backgroundColor: "{colors.gold-tint}"
    textColor: "{colors.ink}"
  doc-row:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.sm}"
  chip-suggestion:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.md}"
    height: 56px
  answer-verdict:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.heading-md}"
    rounded: "{rounded.none}"
    padding: "{spacing.lg}"
---

# 창구 (The Desk)

## Overview

**참조물: 정부24의 정보 구조를, 토스의 손끝 정밀도로 다시 짠 민원 창구.**

사람이 창구에 와서 묻고, 담당자가 규정집을 펴서 해당 쪽을 짚어 보여주고, 다음에 할 일을 알려주고, 사람은 돌아간다. 이 화면의 목표는 대화를 길게 만드는 것이 아니라 **확인된 답을 주고 사용자를 보내는 것**이다.

읽는 사람은 30~60대이고, 노안이 시작됐을 수 있고, 급하고, 이 일을 처음 한다. 그래서 이 시스템은 정부24·KRDS가 이미 그 사람들을 훈련시켜 놓은 관습 위에 선다. 본문 17px, 굵기는 두 개뿐, 컨트롤은 56px, 초점 링은 항상 보인다. 대신 반응 속도와 마감은 관공서가 아니라 금융 앱의 것이다.

**Key Characteristics**

- 그림자가 하나도 없다. 위계는 표면 색과 1px 헤어라인으로만 만든다.
- 모서리 반경은 8px 하나뿐이다. 크기로 위계를 만들지 않는다.
- 활자 굵기는 400과 700 두 개뿐이다. 500도 600도 없다.
- 골드는 화면 전체에서 "이 대목이 실제로 근거가 되었다"는 표시 하나에만 쓴다.
- 사용자가 글자 크기를 90~150%로 직접 바꾼다. 브라우저 확대에 기대지 않는다.

## Colors

**팔레트는 목업이 아니라 엠블럼에서 나왔다.** 목업 원본을 실측하면 로고에는 보라가 한 픽셀도 없다. 원반은 `#F8C800`, 인물과 태양은 `#003D84`다. 보라는 목업 제작자가 UI에 덧입힌 색이었고, 그래서 보라를 늘려 쓸수록 화면이 로고에서 멀어졌다.

이 시스템은 엠블럼의 코발트를 잉크와 행동의 축으로 세운다. 코발트와 금은 여권, 학위기, 훈장, 학회 인장의 조합이라 관공서로도 스타트업으로도 읽히지 않는다.

- **Ink `#0E1A2E`** — 본문과 제목. 페이퍼 위에서 16.2:1. 검정이 아니라 아주 어두운 감청이라 코발트 계열 안에 머문다.
- **Ink-2 `#33445E`** (9.2:1) — 보조 문장. **Ink-3 `#5A6A82`** (5.1:1) — 메타 정보, 날짜, 쪽수.
- **Brand `#00337A`** (11.1:1) — 링크, 주요 버튼, 활성 상태. 흰 글씨를 얹으면 12.0:1. 엠블럼의 `#003D84`를 본문 대비가 서도록 한 단계 내린 값이다.
- **Gold `#C08A1E`** — 페이퍼 위 2.8:1이므로 **글자에 절대 쓰지 않는다.** 밑선, 규칙선, 근거 번호 테두리 전용. 글자급이 필요하면 **Gold-ink `#7A5600`** (6.2:1)을 쓴다.
- **Paper `#F4F7FB`** — 순백이 아니다. 파랑 쪽으로 아주 살짝 기운 흰색이라 코발트가 그 위에서 탁해지지 않는다.
- 다크 모드는 라이트의 반전이 아니다. 배경 `#0B1220`(밤의 감청), 잉크 `#E6ECF5`(15.8:1), 브랜드는 `#8FB4F0`로 올려 어두운 면에서도 링크로 읽히게 한다.
- **선명한 화면 모드**는 세 번째 팔레트다. 배경이 순백으로, 잉크가 `#000814`(20.1:1)로, **헤어라인이 잉크 농도로** 올라온다. 저시력 사용자에게 회색 실선은 없는 것과 같기 때문이다.

엠블럼은 어느 모드에서도 재채색하지 않는다. 로고는 브랜드이지 UI가 아니다.

## Typography

Pretendard 한 패밀리. 한국어와 라틴이 같은 패밀리 안에서 정렬되므로 라틴 폰트를 겹쳐 쌓지 않는다.

| 역할 | 크기 | 굵기 | 행간 | 자간 |
|---|---|---|---|---|
| Display | 34px | 700 | 1.4 | +0.5px |
| Heading L | 24px | 700 | 1.5 | 0 |
| Heading M | 19px | 700 | 1.5 | 0 |
| Heading S | 17px | 700 | 1.5 | 0 |
| Body | **17px** | 400 | **1.7** | 0 |
| Body S | 15px | 400 | 1.65 | 0 |
| Caption | 13px | 400 | 1.55 | 0 (tnum) |

**원칙**

- 본문 17px가 하한이다. 16px는 이 사용자층에게 작다.
- 한글 행간은 1.7이다. 라틴 기준 1.5는 한글에서 빽빽하게 읽힌다.
- 자간은 0이다. 반사적으로 넣는 `-0.02em`이 한국어 UI를 스타트업처럼 보이게 만든다. Display에만 `+0.5px`을 줘서 제목이 "타이핑된" 게 아니라 "새겨진" 것처럼 느려지게 한다.
- 굵기는 400과 700뿐이다. 위계는 크기와 여백이 만든다.
- `word-break: keep-all`로 어절이 쪼개지지 않게 하고, `overflow-wrap: break-word`로 긴 라틴 문자열만 예외를 둔다.
- 쪽수·날짜·건수는 `tabular-nums`로 자릿수를 맞춘다.

## Layout

12열 격자, 8px 기본 단위. 데스크톱은 세 개의 열이 항상 보인다.

```
┌──────────┬───────────────────────┬──────────────┐
│ 문서함    │ 답변                   │ 근거          │
│ 264px    │ 1fr (max 62ch)        │ 336px        │
│          │                       │              │
│ 무엇을    │ 결론                   │ 이 답변이     │
│ 근거로    │ 근거                   │ 실제로 쓴     │
│ 답하는가  │ 절차                   │ 원문 대목     │
│ (상시)    │ 다음 행동              │              │
└──────────┴───────────────────────┴──────────────┘
```

좌측 문서함이 접히지 않는 이유는, **무엇을 근거로 답하는지가 이 제품의 신뢰 그 자체**이기 때문이다. 숨기면 "어디선가 가져온 답"이 된다.

- 본문 열은 62자에서 멈춘다. 한글 장문은 행이 길면 되읽기가 생긴다.
- 여백 단계는 4·8·16·24·32·48. 그 사이 값은 없다.
- 1024px 미만에서 문서함은 상단 드로어로, 근거는 하단 시트로 내려간다.
- 하단 고정 입력창 높이만큼 본문에 인셋을 준다. 마지막 문장이 가려지지 않는다.

## Elevation & Depth

| 단계 | 처리 | 쓰는 곳 |
|---|---|---|
| 0 | 평면 | 페이지 대부분 |
| 1 | `paper` → `surface` 표면 전환 | 카드, 입력창 |
| 2 | 1px `hairline` | 열 경계, 목록 구분 |
| 3 | 1px `hairline-strong` + `surface-sunk` | 활성 항목, 선택된 근거 |
| 4 | 3px 초점 링 | 키보드 초점 |

**그림자는 쓰지 않는다.** 색으로 뜨는 것처럼 보이게 만드는 대신, 표면이 실제로 바뀐다. 모달만 예외로 40% 스크림을 깐다.

## Shapes

반경은 **8px 하나**다. 버튼도 입력창도 카드도 칩도 8px이다. 원형은 아바타와 상태 점에만 쓴다.

크기가 다른 반경을 섞는 순간 화면이 "요소들의 모음"으로 보인다. 하나로 고정하면 화면이 하나의 서식(form)으로 읽힌다. 이건 관공서 서류의 감각이고, 이 제품에는 그게 맞다.

## Components

### Buttons & Inputs

모든 컨트롤 높이 **56px**, 터치 영역 하한 44×44. 반경 8px. 주요 버튼은 `brand` 면에 흰 글씨(9.2:1), 누르면 `brand-press`로 어두워진다. 보조 버튼은 흰 면에 1px 헤어라인.

입력창은 **라벨이 항상 보인다.** placeholder를 라벨로 쓰지 않는다. 초점을 받으면 테두리가 `brand`로 바뀌고 바깥에 3px 링이 생긴다. 오류는 필드 바로 아래에 `danger`로 붙고, `role="alert"`로 읽힌다.

### Evidence Strip

`evidence-card`는 문서 제목, 시행일, 발행처, 쪽수를 머리에 달고, 본문에는 원문 발췌를 싣는다. 발췌 안에서 **실제로 근거가 된 대목만 골드 밑선**을 받는다.

카드와 답변 문장은 서로를 가리킨다. 답변 문장에 마우스나 초점이 오면 대응하는 카드가 `evidence-card-linked`로 바뀌고, 반대로 카드에 오면 답변 문장에 골드 밑선이 켜진다. 이 연결이 이 화면의 시그니처다.

### Answer

`answer-verdict`(결론)는 반경 0의 띠로 본문 맨 위에 놓인다. 그 아래로 근거 → 절차 → 다음 행동이 고정 순서로 온다. 절차는 번호 목록이고, 한 항목에 행동 하나만 담는다.

### Document Drawer

`doc-row`는 문서 제목 + 시행일 + 쪽수를 한 줄로 싣는다. 이 목록은 로그인 화면에도 나온다. 사용자가 로그인하기 **전에** 이 서비스가 무엇을 근거로 답하는지 알 수 있어야 한다.

## Do's and Don'ts

### Do

- 답변은 결론부터 쓴다. 배경 설명은 접어 둔다.
- 근거가 없으면 "무엇을 얼마나 찾아봤는지"를 먼저 보여주고, 그다음 사람에게 연결한다.
- 문서를 주어로 쓴다. "『축복 행정 규정집』 12쪽에 따르면"이라고 쓴다.
- 쪽수·시행일·발행처를 항상 함께 낸다. 셋이 모여야 근거가 된다.
- 초점 링을 3px로 항상 보이게 둔다.

### Don't

- 골드를 글자에 쓰지 않는다. 밑선과 마크 전용이다.
- 신뢰도를 숫자로 쓰지 않는다. 상태는 근거 있음 / 근거 불충분 / 문서에 없음 셋뿐이다.
- 브랜드 바이올렛으로 큰 면을 칠하지 않는다. 그라디언트는 어떤 형태로도 만들지 않는다.
- 1인칭으로 말하지 않는다. "제가 찾아봤는데요"는 도구를 사람처럼 보이게 만들어 신뢰를 부풀린다.
- 내부 분류나 검색 방식을 노출하지 않는다.

## Responsive Behavior

| 폭 | 처리 |
|---|---|
| ≥1280px | 3열 전개, 본문 62자 |
| 1024–1279px | 3열 유지, 근거 열 296px로 축소 |
| 768–1023px | 문서함은 상단 드로어, 근거는 본문 아래 접이식 |
| <768px | 단일 열, 근거는 하단 시트, 입력창 고정 |

터치 목표는 어느 폭에서도 44×44 아래로 내려가지 않는다. 가로 스크롤은 어느 폭에서도 생기지 않는다.

## Accessibility

- 본문 대비 12.0:1, 보조 7.1:1, 메타 5.2:1. 전부 AA를 넘고 본문은 AAA다.
- 글자 크기 컨트롤 90 / 100 / 110 / 130 / 150%. 모든 치수가 `calc()`로 따라 커진다.
- 색으로만 의미를 전달하지 않는다. 근거 표시는 골드 밑선 **과** "근거" 라벨을 함께 낸다.
- `prefers-reduced-motion`을 존중하되 수동 토글이 이기게 한다. 시스템 설정을 켠 사용자가 이 화면에서 모션을 다시 켤 수 있다.
- 키보드만으로 다섯 화면을 모두 돈다. 답변 문장은 `tabindex`를 받아 근거 연결이 초점으로도 동작한다.

## Known Gaps

- 「검색했으나 인용되지 않은 문서」 목록은 현재 API에 없다. 화면은 그 상태를 그리지만 값은 채워야 한다.
- 음성 입력은 이 시안에 없다. 이 사용자층에는 실제로 필요한 기능이다.
