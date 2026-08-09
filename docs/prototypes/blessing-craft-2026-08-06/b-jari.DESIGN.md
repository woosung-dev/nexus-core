---
version: alpha
name: 자리 (The Desk)
description: >
  블레싱 멀티봇 클라이언트의 작업대 변형. 명제는 하나다. 홈은 목록이 아니라 내 진행 상황이다.
  이어가는 대화, 지난번 이후 바뀐 문서, 그리고 태그로 묶인 창구 서가가 첫 화면의 본문이다.
  서가는 가로 스냅이라 창구가 40곳이 되어도 세로 길이가 늘지 않는다. 시그니처는 겹이다.
  고도 0에서 4까지 다섯 계단을 토큰으로 정하고 그 계단으로만 위계를 만든다. 그림자는
  검정이 아니라 잉크 보라를 탄다. 인용은 문장 바로 아래에서 열리는 끼움 카드다.
colors:
  bg: "#EFEFF3"
  surface: "#FFFFFF"
  surface-2: "#F6F6F9"
  surface-3: "#EAEAF0"
  ink: "#221B2E"
  ink-2: "#57506A"
  ink-3: "#7B7490"
  rule: "#E1E0E8"
  rule-2: "#CBC9D6"
  act: "#523A82"
  primary: "#523A82"
  on-act: "#FFFFFF"
  act-soft: "#EDE7F6"
  act-line: "#B7A4D4"
  gold: "#C9A227"
  gold-ink: "#6B5000"
  gold-soft: "#FAF2DA"
  danger: "#A3231B"
  danger-soft: "#FBEDEB"
  ok: "#256B4B"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-bg: "#0E0C13"
  dark-surface: "#191521"
  dark-surface-2: "#211C2C"
  dark-surface-3: "#2A2437"
  dark-ink: "#EDEAF3"
  dark-ink-2: "#B6AFC6"
  dark-ink-3: "#8E869F"
  dark-rule: "#2C2637"
  dark-rule-2: "#3C3450"
  dark-act: "#C3A9E6"
  dark-on-act: "#191021"
  dark-act-soft: "#2A2138"
  dark-gold: "#D9B84A"
  dark-gold-ink: "#EBD48A"
  dark-gold-soft: "#2A2316"
  chrome: "#131019"
typography:
  heading:
    fontFamily: Pretendard Variable
    fontSize: 23px
    fontWeight: "700"
    lineHeight: 1.3
    letterSpacing: -0.64px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 16.5px
    fontWeight: "550"
    lineHeight: 1.6
    letterSpacing: -0.2px
  section:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "650"
    lineHeight: 1.35
    letterSpacing: -0.14px
  body:
    fontFamily: Pretendard Variable
    fontSize: 15.5px
    fontWeight: "400"
    lineHeight: 1.72
    letterSpacing: 0
  card:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: -0.14px
  quote:
    fontFamily: Maru Buri
    fontSize: 13.5px
    fontWeight: "400"
    lineHeight: 1.78
    letterSpacing: 0
  label:
    fontFamily: Pretendard Variable
    fontSize: 10.5px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: 1.05px
  meta:
    fontFamily: IBM Plex Mono
    fontSize: 10.5px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0
spacing:
  unit: 4px
  scale: [1, 4, 6, 9, 11, 14, 18, 22, 26, 30, 34, 44, 60]
rounded:
  shell: 18px
  card: 12px
  field: 10px
  small: 7px
  pill: 999px
elevation:
  e0: none
  e1: 0 1px 2px rgba(34,27,46,0.05)
  e2: 0 1px 2px rgba(34,27,46,0.05), 0 3px 8px rgba(34,27,46,0.06)
  e3: 0 2px 4px rgba(34,27,46,0.06), 0 8px 20px rgba(34,27,46,0.08)
  e4: 0 4px 8px rgba(34,27,46,0.07), 0 18px 44px rgba(34,27,46,0.12)
  bevel: inset 0 1px 0 rgba(255,255,255,0.85)
---

# 자리 (The Desk)

## Overview

**명제: 홈은 목록이 아니라 내 진행 상황이다.**

A안이 "말을 여는 자리"라면 이 안은 "돌아오는 자리"다. 첫 화면의 본문은 이어가는 대화,
지난번 이후 바뀐 문서, 그리고 태그 서가다. 창구는 고르는 대상이 아니라 내가 이미 쓰고 있는
도구로 놓인다.

ui-ux-pro-max Step 2 를 실행했고 그 결과를 이렇게 처리했다.

```
python3 …/scripts/search.py "document knowledge assistant workspace multibot
  trust-first institutional" --design-system -f markdown
→ Pattern: FAQ/Documentation Landing · Style: Exaggerated Minimalism
  Colors: #2563EB accent · Typography: Atkinson Hyperlegible
```

**팔레트와 서체는 채택하지 않았다.** 브랜드 보라 `#603B94` 가 고정값이고, Atkinson Hyperlegible
은 라틴 전용이라 한글 본문에 적용되지 않는다. **채택한 것**은 검색을 화면 위쪽에 두는 것,
해결되지 않은 질문의 에스컬레이션 경로, 카테고리 아이콘을 브랜드색으로 두는 것,
그리고 프리딜리버리 체크리스트 전부다.

보강 검색 `--domain ux "elevation shadow depth layering navigation sidebar"` 에서
고정 내비게이션이 본문을 가리지 않게 패딩으로 보정할 것과, 3단계 이상 깊이에서만 breadcrumb
을 쓸 것을 가져왔다. `--domain style "layered depth material elevation tactile"` 에서
Skeuomorphism 은 기각했고(성능 Poor, 텍스처가 가독성을 깎는다) Tactile Digital 의
누름 반응(scale .95 + 스프링)만 채택했다.

Dials 대응값: 변화 6 / 모션 6 / 밀도 7.

## Colors

바탕이 `#EFEFF3` 로 흰색이 아니다. 카드가 그 위에 떠야 겹이 보이기 때문이다.
A안보다 회색을 중립 쪽으로 밀어 표면이 차다. 같은 보라를 쓰되 온도가 다르다.

금색은 인용문 안의 위치 표시로만 쓴다. 보라는 납작한 잉크와 면으로만 쓰고
그라디언트, 글로, AI 응답 뒤 틴트는 없다.

## Typography

본문 Pretendard, 규정집 인용문만 마루부리, 메타는 IBM Plex Mono.
`word-break: keep-all` + `overflow-wrap: break-word` 전역. 본문 자간 0.

## Layout

| 화면 | 골격 |
|---|---|
| 로그인 | 가운데 카드 한 장. 뒤에 두 장이 겹쳐 있다. 이 안의 첫인상이 곧 겹이다 |
| 홈 | 좌 레일 232px + 검색 → 이어가는 대화 → 바뀐 문서 → 태그 서가(가로 스냅) |
| 대화 | 좌 레일 + 중앙 단 760px. 우측 레일이 없다 |
| 창구 상세 | 좌 레일 + 마크 + 능력 표기 → 보는 문서 → 이 창구가 답하지 않는 것 |

**좌 레일이 모든 화면에 있다.** 이것이 "자리"의 골격이고 A·C 와 실루엣이 갈리는 지점이다.
899px 미만에서 레일이 사라진다.

서가는 `grid-auto-flow: column` + `scroll-snap-type: x mandatory` 다.
창구가 40곳이 되어도 **세로 길이가 늘지 않는 것**이 이 안의 강점이다.

## Elevation

**이 안의 시그니처다.** 0에서 4까지 다섯 계단이고 그 사이 값을 쓰지 않는다.

| 계단 | 쓰는 곳 |
|---|---|
| e1 | 서가 카드, 문서 변경 목록, 칩 |
| e2 | 이어가는 대화 카드, 컴포저 |
| e3 | 열린 인용 카드, hover 상태 |
| e4 | 안전 카드, 로그인 패널, 모바일 셸 |

고도가 곧 "지금 무엇이 위에 있는가"이므로 임의로 그림자를 더하면 위계가 깨진다.
그림자는 검정이 아니라 잉크 보라 `rgba(34,27,46,…)` 를 탄다.

## Shapes

셸 18px, 카드 12px, 입력 10px, 작은 것 7px, 알약 999px. 이 다섯 말고 쓰지 않는다.

## Components

**인용 끼움 카드.** A안의 우측 레일과 다르다. 알약을 누르면 그 문단 바로 아래에서
`grid-template-rows: 0fr → 1fr` 로 카드가 열린다. 호버가 없는 모바일에서도 그대로 동작한다.

**태그 서가.** `bot.tags` 와 `GET /bots/categories` 가 실제로 있으므로 지금 API 로 채울 수 있다.
다섯 갈래 이름은 표시용이고 조직이 축을 정하면 갈아 끼운다.

**shared element 전환.** 창구 카드의 마크가 대화 헤더의 마크로 이어진다.
View Transitions API 를 쓰고 미지원 브라우저에서는 즉시 전환된다.

**유형 라벨 / 검색 영수증 / 상시 도움 자리** 는 세 안이 공유한다. A안 문서를 참조.

## Motion

| 대상 | 하는 일 |
|---|---|
| 화면 진입 | 카드가 바닥에서 고도를 얻으며 올라온다. 겹이 생기는 것을 보여준다 |
| 레일 항목 | 왼쪽에서 30ms 간격으로 들어온다 |
| 서가 카드 | 45ms 간격 스태거 |
| 답변 | 90ms 간격으로 자리를 잡는다 |
| 창구 → 대화 | 마크가 이어지는 shared element 전환 |
| 누름 | `scale(.97)` + 스프링. 물리적으로 눌린다는 피드백 |

`prefers-reduced-motion` 과 수동 토글 모두 존중. 끌 때 duration 을 0 으로 만든다.

## Do's and Don'ts

**Do**

- 고도는 다섯 계단만 쓴다. 사이 값을 만들면 위계가 무너진다
- 그림자에 잉크 보라를 태운다. 순수 검정은 흰 표면에 때를 남긴다
- 서가는 가로로 눕힌다. 세로로 쌓으면 40곳에서 무너진다
- 고정 상단 바는 본문 패딩으로 보정한다

**Don't**

- 보라 그라디언트, 글로, AI 응답 뒤 틴트
- 텍스처와 복잡한 그라디언트로 재질을 흉내내는 것(Skeuomorphism 기각 이유)
- 크롬 띠 높이를 상수로 박는 것. 줄바꿈되면 컴포저가 화면 밖으로 밀린다
- `cite_count` 노출, 구현어 노출, 1인칭 화법
