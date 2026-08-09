---
version: alpha
name: 채광 (The Light Well)
description: >
  블레싱 멀티봇 클라이언트의 도상 변형. 명제는 하나다. 답이 아니라 근거가 주인공이고,
  화면은 문서에 빛을 들이는 장치다. 시그니처는 채광창이다. 엠블럼의 원반과 광선을 실선 호로만
  그린 도형을 왼쪽에 두고 문장과 입력을 오른쪽에 둔다. 그 아래 승인 문서를 폭으로 부호화한
  띠가 있고 폭은 그 문서를 보는 창구 수다. 장식이 아니라 실제 값의 그림이다. 인용은 본문 왼쪽
  여백의 방주로 열린다. 각지고 반경은 4px 하나뿐이다.
colors:
  paper: "#FCFBFD"
  surface: "#FFFFFF"
  shade: "#EDE9F2"
  shade-2: "#E2DCEA"
  ink: "#241A38"
  ink-2: "#514765"
  ink-3: "#786E8C"
  rule: "#E4DFEC"
  rule-2: "#CFC7DC"
  act: "#523A82"
  primary: "#523A82"
  on-act: "#FFFFFF"
  act-soft: "#EEE8F7"
  act-line: "#B5A2D2"
  gold: "#C9A227"
  gold-ink: "#6B5000"
  gold-soft: "#FAF3DC"
  danger: "#A3231B"
  danger-soft: "#FBEDEB"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-paper: "#12101A"
  dark-surface: "#1A1624"
  dark-shade: "#221C2F"
  dark-shade-2: "#2B2439"
  dark-ink: "#EFEBF6"
  dark-ink-2: "#B9B0CA"
  dark-ink-3: "#8F86A2"
  dark-rule: "#2C2539"
  dark-rule-2: "#3D3450"
  dark-act: "#C3A9E6"
  dark-on-act: "#191021"
  dark-act-soft: "#2A2138"
  dark-gold: "#D9B84A"
  dark-gold-ink: "#EBD48A"
  dark-gold-soft: "#2A2316"
  chrome: "#17121F"
typography:
  display:
    fontFamily: Pretendard Variable
    fontSize: 38px
    fontWeight: "700"
    lineHeight: 1.24
    letterSpacing: -1.22px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 19px
    fontWeight: "600"
    lineHeight: 1.52
    letterSpacing: -0.42px
  heading:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "650"
    lineHeight: 1.35
    letterSpacing: -0.14px
  body:
    fontFamily: Pretendard Variable
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 1.76
    letterSpacing: 0
  quote:
    fontFamily: Maru Buri
    fontSize: 12.5px
    fontWeight: "400"
    lineHeight: 1.72
    letterSpacing: 0
  label:
    fontFamily: Pretendard Variable
    fontSize: 11px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: 1.1px
  stat:
    fontFamily: IBM Plex Mono
    fontSize: 20px
    fontWeight: "500"
    lineHeight: 1.2
    letterSpacing: -0.4px
  meta:
    fontFamily: IBM Plex Mono
    fontSize: 10px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0
spacing:
  unit: 4px
  scale: [2, 6, 8, 11, 13, 16, 20, 26, 30, 34, 40, 46, 60]
rounded:
  all: 4px
  pill: 999px
elevation:
  flat: none
  raised: 0 1px 2px rgba(36,26,56,0.05)
  lifted: 0 2px 6px rgba(36,26,56,0.06), 0 8px 22px rgba(36,26,56,0.07)
  floating: 0 4px 10px rgba(36,26,56,0.08), 0 20px 48px rgba(36,26,56,0.11)
---

# 채광 (The Light Well)

## Overview

**명제: 답이 아니라 근거가 주인공이다. 화면은 문서에 빛을 들이는 장치다.**

이 주제의 세계에 실제로 있는 것은 규정집, 판차, 승인일, 쪽수, 조항, 그리고 인용이다.
인사말이 아니다. 그래서 첫 화면은 "무엇을 도와드릴까요"가 아니라 **무엇을 근거로 답하는지**를
보여준다.

### 설계안 (코드보다 먼저 쓴 것)

- 색 5: 백지 `#FCFBFD` · 잉크 `#241A38` · 정색 `#523A82` · 금선 `#C9A227` · 그늘 `#EDE9F2`
- 활자 3역: 본문 Pretendard · 인용 원문만 마루부리 · 메타 IBM Plex Mono
- 시그니처: 채광창. 엠블럼의 원반과 광선을 실선 호로만 그린 도형.
  그 아래 승인 문서를 폭으로 부호화한 띠. 폭 = 그 문서를 보는 창구 수.

```
┌──────────────────────────────────────────────────────┐
│  ◉ 블레싱                              읽는 법  ○     │
├──────────────────────────────────────────────────────┤
│      ╲  ╲  │  ╱  ╱      승인된 문서 14종이            │
│         ((◉))            답의 근거입니다               │
│      ╱  ╱  │  ╲  ╲      14  14  2026.07.30           │
│                          ┌──────────────────┐         │
│                          │ 무엇이 궁금하신가요 →│        │
│                          └──────────────────┘         │
├──────────────────────────────────────────────────────┤
│  지금 답할 수 있는 것                                  │
│  ██████ █████ ███ ███ ██ ██ █ █ █ █ █ █ █             │
├──────────────────────────────────────────────────────┤
│  창구 14곳  (다섯 갈래 조밀 목록)                       │
└──────────────────────────────────────────────────────┘
```

### 자기비평 (설계안을 브리프에 대조한 것)

1. **가운데 빛나는 원은 2026년 AI 제품의 전형이다.** 그래서 채우지 않고 선으로만 그렸고,
   가운데 정렬도 하지 않았다. 도형은 왼쪽 40%, 문장과 입력은 오른쪽이다.
2. **직전 라운드의 C(총람)는 문서 이름으로 시작해서 처음 오신 분이 출발할 수 없었다.**
   그래서 입력창을 문서 띠보다 위에 둔다. 문서는 약속의 증거이지 출발점이 아니다.
3. **보라를 빛으로 쓰면 AI 표식이 된다.** 광선은 잉크로 긋고 정색은 채광창의 한 겹과
   지금 켜진 근거에만 쓴다.

Dials 대응값: 변화 8 / 모션 6 / 밀도 4.

## Colors

세 안 중 바탕이 가장 밝고(`#FCFBFD`) 잉크가 가장 차다. 각진 형태와 함께 기관의 인상을 만든다.

금색은 두 곳에만 쓴다. 채광창의 호 하나(현행 판을 가리키는 눈금)와 본문의 인용 표식,
그리고 인용문 안의 밑선이다. **본문의 인용 표식이 금선인 것이 A·B 와 다른 점이다.**
알약을 넣으면 문장이 끊기기 때문에 밑선 하나와 작은 번호만 남겼다.

## Typography

본문이 세 안 중 가장 크다(16px / 1.76). 밀도가 낮은 대신 읽기가 편해야 하기 때문이다.
규정집 인용문만 마루부리. `word-break: keep-all` 전역, 본문 자간 0.

## Layout

| 화면 | 골격 |
|---|---|
| 로그인 | 좌 채광창 + 우 문장과 SSO 버튼 |
| 홈 | 채광창(좌 0.62 : 우 1) → 문서 띠 → 창구 다섯 갈래 조밀 목록 |
| 대화 | **좌 방주 212px + 본문 단.** 899px 미만에서 방주가 본문 아래 카드로 |
| 창구 상세 | 규칙선으로만 나눈 조밀 목록 |

**왼쪽 방주가 이 안의 실루엣이다.** A는 오른쪽에 자료를 두고 B는 왼쪽에 내비게이션을 두는데,
이 안은 왼쪽에 근거를 둔다. 회색조로 바꿔도 셋이 구분되는 이유다.

## Elevation

거의 쓰지 않는다. 이 안은 그림자가 아니라 **규칙선**으로 위계를 만든다.
띄우는 것은 프로토타입 크롬과 열린 방주뿐이다.

## Shapes

**반경은 4px 하나뿐이다.** 알약만 예외다. 각진 것이 이 안의 성격이다.

## Components

**채광창.** 원 4개 + 광선 12개 + 금색 호 1개 + 엠블럼. 전부 실선이고 채우지 않는다.
로드할 때 `stroke-dasharray` 로 한 번 그려지고 반복하지 않는다.

**문서 띠.** `flex: <창구 수>` 로 폭을 나눈다. 창구가 보는 문서 목록에서 역산한 실제 값이다.
칸을 누르면 그 문서를 보는 창구가 아래에 나온다.
**문서가 30종을 넘으면 칸이 손가락보다 좁아져 스크롤로 바꿔야 한다.**

**왼쪽 방주.** 본문의 금선 표식을 누르면 왼쪽 방주가 켜지고 인용문이 펼쳐진다.
방주를 눌러도 본문 구간이 켜진다. 방향이 양쪽이다.
`max-height` 전이를 쓰므로 요소가 반드시 `display: block` 이어야 한다(span 이면 먹지 않는다).

**유형 라벨 / 검색 영수증 / 상시 도움 자리** 는 세 안이 공유한다. A안 문서를 참조.

## Motion

이 안의 안무는 **빛이 든다**이다. 위에서 아래로 차례로 밝아진다.

| 대상 | 하는 일 |
|---|---|
| 채광창 | 호가 한 번 그려진다. 로드 때만이고 반복하지 않는다 |
| 문서 띠 | 칸이 아래에서 자라 오른다. 35ms 간격 |
| 답변 | 100ms 간격으로 밝아진다 |
| 방주 | 본문이 끝난 뒤 들어온다 |

`prefers-reduced-motion` 과 수동 토글 모두 존중. 끌 때 duration 을 0 으로 만든다.

## Do's and Don'ts

**Do**

- 채광창은 선으로만 그린다. 채우면 AI 오브가 된다
- 도형은 왼쪽으로 밀고 가운데 정렬하지 않는다
- 표제의 숫자도 데이터에서 뽑는다. 손으로 적으면 규모를 바꿀 때 어긋난다
- 반경은 4px 하나만 쓴다

**Don't**

- 보라 그라디언트, 글로, 히어로 오브, AI 응답 뒤 틴트
- 문서 이름으로 시작하는 첫 화면(처음 오신 분이 출발할 수 없다)
- 인라인 요소에 `max-height` 전이(먹지 않는다)
- `cite_count` 노출, 구현어 노출, 1인칭 화법

## 이 안의 한계

**데스크톱에 강하고 모바일에 약하다.** 899px 미만에서 방주가 사라지고 본문 아래 카드로
내려오므로 시그니처가 절반만 남는다. 모바일이 주 사용처라면 이 안을 고를 근거가 약해진다.

**문서 띠는 봇과 문서의 연결을 알아야 성립한다.** 그 값이 API 에 없으므로 지금은 예시다.
세 안 중 이 안이 선행 과제 1번에 가장 크게 걸려 있다.
