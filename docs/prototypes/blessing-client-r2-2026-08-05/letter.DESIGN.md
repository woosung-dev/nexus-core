---
version: alpha
name: 곁 (Beside)
description: >
  블레싱 네비게이션 클라이언트의 동행 변형. 채팅 로그를 없애고 한 번에 문답 한 쌍만
  붙든다. 지난 문답은 위로 접혀 날짜와 첫 구절만 남는 한 줄이 된다. 답변 안에서는
  근거의 실이라는 금빛 세로선이 문서에서 온 문장 옆을 따라 내려가다가, 시스템의
  안내가 시작되는 자리에서 끊긴다. 규정과 마음이 눈으로 구분된다.
colors:
  field: "#131725"
  field-fold: "#0E1220"
  ink: "#E9ECF4"
  ink-2: "#B2B9CC"
  ink-3: "#8B93A8"
  brand: "#9DB6F2"
  brand-press: "#BFD0F8"
  on-brand: "#0C1120"
  gold: "#E2A94B"
  gold-ink: "#F0C77E"
  edge: "#2A3145"
  edge-soft: "#212739"
  alarm: "#F0938B"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  day-field: "#EEF0F6"
  day-field-fold: "#E3E6EF"
  day-ink: "#151A28"
  day-ink-2: "#414A63"
  day-ink-3: "#5F6980"
  day-brand: "#23428C"
  day-gold: "#B07A16"
  day-gold-ink: "#7A5410"
  day-edge: "#CFD5E4"
  day-alarm: "#93231D"
typography:
  ask:
    fontFamily: Gowun Batang
    fontSize: 30px
    fontWeight: "700"
    lineHeight: 1.55
    letterSpacing: -0.3px
  answer:
    fontFamily: Gowun Batang
    fontSize: 19px
    fontWeight: "400"
    lineHeight: 1.9
    letterSpacing: 0
  answer-lead:
    fontFamily: Gowun Batang
    fontSize: 22px
    fontWeight: "700"
    lineHeight: 1.75
    letterSpacing: -0.2px
  aside:
    fontFamily: Gowun Batang
    fontSize: 17.5px
    fontWeight: "400"
    lineHeight: 1.9
    letterSpacing: 0
  source:
    fontFamily: Gowun Batang
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 1.85
    letterSpacing: 0
  label:
    fontFamily: Pretendard Variable
    fontSize: 12.5px
    fontWeight: "600"
    lineHeight: 1.5
    letterSpacing: 0
  meta:
    fontFamily: Pretendard Variable
    fontSize: 12.5px
    fontWeight: "400"
    lineHeight: 1.6
    letterSpacing: 0
    fontFeature: "tnum"
  control:
    fontFamily: Pretendard Variable
    fontSize: 15px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: 0
rounded:
  none: 0
  pill: 999px
spacing:
  base: 8px
  xs: 4px
  sm: 10px
  md: 18px
  lg: 30px
  xl: 48px
  xxl: 76px
  thread: 26px
  measure: 31rem
components:
  ask-line:
    textColor: "{colors.ink}"
    typography: "{typography.ask}"
    rounded: "{rounded.none}"
  grounded-passage:
    textColor: "{colors.ink}"
    typography: "{typography.answer}"
    rounded: "{rounded.none}"
    padding: "{spacing.thread}"
  ungrounded-passage:
    textColor: "{colors.ink-2}"
    typography: "{typography.aside}"
    rounded: "{rounded.none}"
    padding: "{spacing.thread}"
  fold-row:
    backgroundColor: "{colors.field-fold}"
    textColor: "{colors.ink-3}"
    typography: "{typography.meta}"
    rounded: "{rounded.none}"
    padding: "{spacing.sm}"
  source-note:
    textColor: "{colors.ink-2}"
    typography: "{typography.source}"
    rounded: "{rounded.none}"
    padding: "{spacing.md}"
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.on-brand}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "{spacing.lg}"
    height: 52px
  button-primary-pressed:
    backgroundColor: "{colors.brand-press}"
    textColor: "{colors.on-brand}"
  button-quiet:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink-2}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    height: 52px
  reach-row:
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    height: 48px
---

# 곁 (Beside)

## Overview

**참조물: 정성 들여 쓴 답장 한 장.** 날짜가 있고, 서명이 있고, 접힌 자국이 있는.

이 화면이 상대하는 사람은 지금 혼자 판단하려 하고 있다. 밤 열한 시에 매칭을 앞두고 규정집을 붙들고 있는 2세 청년이거나, 지하철에서 서류를 확인하는 가정부장이다. 이 화면의 일은 대화를 이어가는 것이 아니라 **한 사람에게 정직한 답 하나를 주고, 그 사람을 혼자 두지 않는 것**이다.

그래서 이 화면에는 채팅 로그가 없다. 화면은 한 번에 문답 한 쌍만 붙들고, 지난 문답은 위로 접혀 날짜와 첫 구절만 남는 한 줄이 된다. **이 제품의 답은 대화가 아니라 한 번 읽고 실행하는 안내문이고, 자기 불안의 기록이 머리 위로 쌓여 있을 이유가 없다.**

**Key Characteristics**

- 그릇이 없다. 카드도, 낱장도, 패널도 없다. 글이 바탕 위에 바로 놓인다.
- 더 밝은 표면이 없다. 화면 전체가 저녁 빛 한 장이다.
- 모양이 있는 것은 누르는 것뿐이다. 나머지는 형태를 갖지 않는다.
- 읽는 글씨는 바탕체 한 벌, 작은 글씨만 고딕이다.
- 어른에게 잇는 길이 모든 화면 아래에 조용히 있다.

## Colors

**밤이 기본값이다.** 축복을 앞두고 규정집을 붙드는 시각은 대개 밤 열한 시고, 그때 흰 화면은 그 자체로 부담이다. 낮 모드는 기기 설정이 밝음일 때, 또는 직접 고를 때 나온다.

방은 차갑고 등불만 따뜻하다. **차가운 인디고 실내에 따뜻한 앰버 광원 하나**라는 대비가, 화면 전체를 따뜻하게 칠하는 것보다 실제 밤과 가깝고 브랜드로도 더 정확하다.

- **Field `#131725`** — 인디고 밤. 이 위에 더 밝은 면을 올리지 않는다. 카드를 띄우는 순간 편지가 아니라 앱이 된다.
- **Ink `#E9ECF4`** (15.1:1) — 문서에서 온 문장.
- **Ink-2 `#B2B9CC`** (9.1:1) — **문서에 없는 안내 문장.** 농도를 한 단계 낮추는 것이 의미다. 옅게 보이라고 옅은 게 아니라 근거가 다르다는 표시다.
- **Ink-3 `#8B93A8`** (5.8:1) — 날짜, 라벨, 접힌 줄.
- **Gold `#E2A94B`** (8.5:1) — **근거의 실.** 등불의 색이다. 글자에 쓰지 않고, 문서에서 온 문장 왼쪽을 따라 내려가는 2px 세로선이 전부다.
- **Brand `#9DB6F2`** — 누르는 것에만. 화면에 한두 개뿐이다.
- **Alarm `#F0938B`** — 안전 우선 화면에만.
- 낮 모드는 밤의 반전이 아니다. 바탕 `#EEF0F6`, 잉크 `#151A28`(15.2:1), 실은 `#B07A16`으로 내려 밝은 면에서도 실선으로 읽히게 한다.
- 엠블럼만 원색을 갖는다. 어두운 방에서 금빛 원반 하나가 켜져 있는 셈이다.

## Typography

**고운바탕** 한 벌이 읽는 글씨를 전부 맡는다. 굵기는 400과 700 두 개뿐이라 위계는 크기와 여백이 만든다. 13px 이하의 날짜·라벨·버튼만 **Pretendard**로 내린다. 작은 크기에서 바탕체는 읽히지 않기 때문이다.

| 역할 | 서체 | 크기 | 굵기 | 행간 |
|---|---|---|---|---|
| 오늘의 물음 | 고운바탕 | 30px | 700 | 1.55 |
| 답의 첫 문단 | 고운바탕 | 22px | 700 | 1.75 |
| 답변 본문 | 고운바탕 | 19px | 400 | **1.9** |
| 안내 문장 | 고운바탕 | 17.5px | 400 | 1.9 |
| 원문 인용 | 고운바탕 | 16px | 400 | 1.85 |
| 라벨·버튼 | Pretendard | 12.5–15px | 400/600 | 1.5 |

행폭은 31rem에서 멈춘다. 한글 38자 안팎이라 눈이 한 번에 잡는다. 행간 1.9는 편지의 속도다.

## Layout

단일 열, 왼쪽 정렬. 가운데 정렬하지 않는다. 왼쪽 26px는 **근거의 실이 지나갈 자리**로 항상 비워 둔다.

```
   2026.08.04  40일 정성은 무엇인가요        ← 접힌 지난 문답
   2026.08.03  봉헌식 순서를 알려주세요
  ────────────────────────────────────

   축복후보자 서류는
   무엇이 필요한가요                        ← 오늘의 물음

 ┃ 축복후보자 등록에는 서류 3종이            ← 금선: 문서에서 온 문장
 ┃ 필요합니다.
 ┃
 ┃ 등록에 필요한 서류는 신청서와
 ┃ 확인서와 가정 확인 자료 3종으로
 ┃ 정해져 있습니다.

   서류 형식이 지역마다 조금씩              ← 선 없음, 한 칸 안으로,
   다를 수 있으니 제출 전에                    농도 한 단계 낮게
   확인하시는 편이 좋습니다.

 ┃1 등록 신청서를 작성합니다               ← 절차 번호가 실 자리에 산다
 ┃2 가정부장님 확인 서명을 받습니다
 ┃3 지역 축복가정국에 제출합니다

  ────────────────────────────────────
   근거  『축복후보자 등록 안내』 6쪽
        축복후보자 등록에 필요한 서류는…

  ────────────────────────────────────
   이 이야기는 사람과 하는 게 좋아요
   부모님 · 가정부장님 · 목회자 · 109
```

- 여백 단계 4·10·18·30·48·76.
- 900px 미만에서도 짜임은 같다. 실 자리는 20px로 줄어든다.
- 화면마다 짜임이 다르다. 접힌 목록, 편지 한 장, 원문 한 대목, 출입, 항목 대조.

## Elevation & Depth

깊이가 없다. 그림자도 없고, 표면 전환도 없다.

유일한 예외는 접힌 자국 위쪽이다. 지난 문답이 놓인 영역만 `field-fold`로 반 톤 가라앉아, 지금 읽는 것과 지나간 것이 구분된다. 그 외에는 화면 전체가 한 장이다.

## Shapes

**형태를 갖는 것은 누르는 것뿐이고, 그것은 알약이다.** 버튼과 어른에게 잇는 줄이 `999px`이고, 나머지는 어떤 모서리도 갖지 않는다.

편지에는 상자가 없다. 상자를 하나라도 그리면 이 화면의 논지가 무너진다.

## Components

### Grounded / Ungrounded Passage

이 시스템의 시그니처다. `grounded-passage`는 왼쪽에 2px 금선을 두고, 연달아 오는 문단끼리는 선이 **이어진다**. `ungrounded-passage`는 선이 없고 한 칸 안으로 들어가며 잉크 농도가 한 단계 낮다.

그래서 한 답변 안에서 **선이 끊기는 자리**가 바로 규정이 끝나고 안내가 시작되는 자리다. 근거 없는 문장을 근거 있는 문장과 똑같이 그리지 않는다는 원칙을 위젯이 아니라 지면 전체로 옮긴 것이다.

절차의 번호는 이 금선 자리 안에 산다. 순서가 실제로 정보이므로 번호를 쓰되, 별도의 장치를 하나 더 만들지 않고 시그니처가 흡수한다.

### Fold Row

`fold-row`는 지난 문답 하나를 한 줄로 접은 것이다. 날짜와 물음의 첫 구절만 남는다. 펼치면 그 문답이 오늘 자리로 온다. 전체 펼치기는 없다.

### Source Note

근거는 카드가 아니라 괘선 아래 들여쓴 조용한 단락이다. 문서 이름, 판본, 쪽수가 한 줄로 흐르고 그 아래 원문 발췌가 온다. 발췌 안에서 실제로 근거가 된 대목만 금선을 받는다.

### Reach Row

어른에게 잇는 줄은 모든 화면 아래에 있다. 부모님 → 가정부장님 → 공직자·목회자·사모님 → 신뢰하는 어른 순서는 고정이고 바뀌지 않는다. 침범하지 않되 사라지지도 않는다.

## Motion

움직이는 것은 하나뿐이다. **답이 도착하면 금선이 위에서 아래로 그어진다.** 700ms, 문단마다 60ms씩 늦게. 이 선이 그어지는 것이 "이 문장들에는 뒷받침이 있다"는 뜻이다.

나머지는 색 전환 150ms다. `prefers-reduced-motion`을 존중하고, 수동 토글이 그보다 우선한다.

## Do's and Don'ts

### Do

- 근거 있는 문장과 없는 문장을 다르게 그린다. 이것이 이 화면의 전부다.
- 한 화면에 문답 한 쌍만 둔다.
- 어른에게 잇는 길을 늘 아래에 둔다.
- 문서 이름과 쪽수를 답과 같은 자리에 둔다.

### Don't

- 상자를 만들지 않는다. 카드도 패널도 없다.
- 금색을 글자에 쓰지 않는다. 실 하나가 전부다.
- 답변을 흘려 쓰지 않는다. 스트리밍은 이 화면의 속도가 아니다.
- 1인칭으로 말하지 않는다.

## Responsive Behavior

| 폭 | 처리 |
|---|---|
| ≥900px | 행폭 31rem, 실 자리 26px, 접힌 줄 상단 고정 |
| 600–899px | 행폭 유지, 실 자리 22px |
| <600px | 좌우 여백 18px, 실 자리 20px, 어른에게 잇는 줄은 가로 스크롤 없이 두 줄로 |

터치 목표는 어느 폭에서도 44×44 아래로 내려가지 않는다.

## Known Gaps

- 지난 문답을 검색하는 길이 없다. 접힌 줄을 훑는 것이 전부다. 문답이 수십 개로 늘면 다시 봐야 한다.
- 「검색했으나 인용되지 않은 문서」 목록은 현재 API에 없다.
