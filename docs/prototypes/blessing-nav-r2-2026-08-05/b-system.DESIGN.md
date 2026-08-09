---
version: alpha
name: 시스템 (The Console)
description: >
  블레싱 네비게이션 클라이언트의 콘솔 변형. 메인이 소개 화면이 아니라 재방문자의 상태판이다.
  상단에 코퍼스 상태 줄, 본문에 전폭 행 스택, 하단에 고정 컴포저. 히어로도 가로 스크롤
  레일도 카드 격자도 쓰지 않는다. 토큰과 상태 레이어와 elevation 스케일을 전부 실어
  Tailwind v4 @theme 으로 바로 옮길 수 있는 형태로 둔다.
colors:
  bg: "#F4F4F8"
  surface: "#FFFFFF"
  surface-2: "#EDEDF3"
  surface-3: "#ECE7F6"
  fg: "#3B2560"
  fg-2: "#5B4B78"
  fg-3: "#6F6285"
  border: "#E2E2EC"
  border-2: "#C9C9D8"
  primary: "#523A82"
  on-primary: "#FFFFFF"
  primary-soft: "#ECE7F6"
  ring: "#523A82"
  gold: "#C9A227"
  gold-ink: "#6B5000"
  gold-soft: "#FBF3DC"
  mark: "#F4E7BE"
  destructive: "#A3231B"
  destructive-soft: "#FBEDEB"
  ok: "#256B4B"
  ok-soft: "#E6F2EC"
  warn: "#7A5410"
  warn-soft: "#FBF1DC"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-bg: "#15121B"
  dark-surface: "#1E1926"
  dark-surface-2: "#272031"
  dark-fg: "#EDEAF2"
  dark-fg-2: "#A79FB4"
  dark-fg-3: "#9C93AB"
  dark-border: "#332C3E"
  dark-border-2: "#473F55"
  dark-primary: "#C0AAE8"
  dark-on-primary: "#1A0F28"
  dark-primary-soft: "#241C33"
  dark-gold: "#D9B368"
  dark-mark: "#4C3D12"
  chrome: "#100C18"
typography:
  h1:
    fontFamily: Pretendard Variable
    fontSize: 27px
    fontWeight: "800"
    lineHeight: 1.3
    letterSpacing: -0.8px
  h2:
    fontFamily: Pretendard Variable
    fontSize: 16px
    fontWeight: "700"
    lineHeight: 1.35
    letterSpacing: -0.32px
  h3:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "700"
    lineHeight: 1.4
    letterSpacing: -0.21px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 16px
    fontWeight: "500"
    lineHeight: 1.75
    letterSpacing: -0.16px
  body:
    fontFamily: Pretendard Variable
    fontSize: 14.5px
    fontWeight: "400"
    lineHeight: 1.8
    letterSpacing: 0
  row-title:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: -0.17px
  caption:
    fontFamily: Pretendard Variable
    fontSize: 12.5px
    fontWeight: "400"
    lineHeight: 1.5
    letterSpacing: 0
  numeric:
    fontFamily: Plus Jakarta Sans
    fontSize: 13.5px
    fontWeight: "700"
    lineHeight: 1.4
    letterSpacing: 0
  mono:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0
spacing:
  unit: 4px
  scale: [4, 8, 12, 16, 20, 24, 32, 40, 48]
rounded:
  surface: 10px
  control: 8px
  pill: 999px
elevation:
  e1: 0 1px 2px rgba(36,24,58,0.06)
  e2: 0 1px 3px rgba(36,24,58,0.07), 0 6px 16px -8px rgba(36,24,58,0.16)
  e3: 0 2px 6px rgba(36,24,58,0.08), 0 18px 40px -18px rgba(36,24,58,0.26)
---

# 시스템 (The Console)

## Overview

`ui-ux-pro-max --design-system` 이 반환한 것은 **Enterprise Gateway** 패턴,
**Micro-interactions** 스타일, Plus Jakarta Sans, 네이비 `#1E293B` + 블루 `#2563EB` 였다.

**채택**: 토큰 이름 체계(primary / on-primary / surface / border / destructive / ring),
Micro-interactions 의 상태 레이어와 50-100ms 호버, 일관 elevation 스케일,
Plus Jakarta Sans, 사전 배송 체크리스트.

**이탈 3건**

1. **팔레트를 브랜드 보라로 오버라이드했다.** 이 제품에는 이미 브랜드색이 있다.
   스킬이 준 것은 색이 아니라 색을 다루는 구조다.
2. **패턴이 지시하는 "1. Hero (Video/Mission)" 를 넣지 않았다.** Enterprise Gateway 는
   처음 온 잠재 고객을 위한 영업 게이트웨이다. 이 화면은 어제도 쓴 사람이 오늘 다시 여는
   콘솔이다. 히어로와 가로 스크롤 레일을 걷어내는 것이 이번 작업의 목적이다.
3. **본문 서체는 Pretendard Variable 이다.** 한글이 본문이라 Plus Jakarta Sans 는
   숫자와 라틴에만 쓴다. 표 형태 숫자에는 IBM Plex Mono 를 쓴다.

메인이 답하는 질문은 "이 봇이 뭐야"가 아니라 **"내가 어디까지 했더라, 그리고 문서가 뭐가 바뀌었더라"** 다.
그래서 화면이 이 순서다.

```
[상태 줄]  현행 6종 · 2026 정본 · 갱신 07.14 · 폐기 0 · 근거 확인 중 1
[이어서]   진행 중 대화 4행. 근거가 늦게 도착한 답변은 여기서 상태가 먼저 바뀐다
[문서 변경] 최근 변경 4행. 무엇이 언제 왜 바뀌었는지
[담당 범위] 봇 5행. 인기순이 아니라 담당 문서 묶음순
[컴포저]   하단 고정. 메인에서 바로 묻는다
```

## Colors

바탕 `#F4F4F8` 기준 실측: fg 11.9:1, fg-2 7.0:1, fg-3 5.1:1, primary 8.4:1,
흰 글씨 on primary 9.2:1. 다크 `#15121B` 기준: fg 15.6:1, fg-2 7.3:1, fg-3 6.3:1, primary 9.0:1.

시맨틱 토큰만 쓰고 컴포넌트에 원시 hex 를 쓰지 않는다.
`ok` `warn` `destructive` 는 실제 상태에만 나오고 장식으로 쓰지 않는다.
행 배지의 색은 뜻이다. `2026 정본` 은 골드, `추가` 는 ok, `판본 대기` 는 warn,
`근거 확인 중` 은 primary. 색만으로 뜻을 전하지 않으므로 배지에는 항상 글자가 함께 있다.

골드 `#C9A227` 은 2.2:1 이라 글자에 쓸 수 없다. 배지의 밑선 2px, 각주 번호 칩의 밑선.
글자급 골드는 `#6B5000` (6.9:1).

## Typography

Pretendard Variable 이 한글 본문과 제목, Plus Jakarta Sans 가 숫자,
IBM Plex Mono 가 판본과 날짜다. 세 역할이 겹치지 않는다.

상태 줄의 숫자(`6종` `0` `1`)는 Plus Jakarta Sans 700 이고
`font-variant-numeric: tabular-nums` 라 값이 바뀌어도 자리가 흔들리지 않는다.
판본과 날짜는 IBM Plex Mono 이고 합자를 끈다.

## Layout

**메인(콘솔)** `.console { grid-template-rows: auto 1fr auto }`.
상태 줄과 컴포저가 고정이고 가운데만 스크롤한다. 1024px 이상에서 좌측 248px 사이드바가 붙는다.

행 스택은 640px 이상에서 `34px / 1fr / auto / auto` 4칸이고,
그 미만에서는 `34px / 1fr` 2칸으로 접혀 배지와 날짜가 아래로 쌓인다.
카드가 아니라 행이므로 격자 여백이 생기지 않고 스캔이 빠르다.

**대화** 좌측 사이드바 248px + 가운데 본문 최대 820px. **인용은 본문 아래 접이식**이고
우측 패널을 쓰지 않는다. A안(오른쪽이 무거운 2열)과 거울상이라 회색조로도 구분된다.

**하단 탭** 은 4개다. 5개를 넘기지 않고 아이콘과 라벨을 함께 쓴다.

**프로토타입 크롬** 은 하단 상태바다. 폭을 뺏지 않으므로 390px 문서에서
앱이 진짜 390px 로 렌더된다. 1100px 미만에서는 「컨트롤」 버튼으로 접힌다.

## Elevation

`e1` 은 버튼과 카드, `e2` 는 호버로 뜨는 것, `e3` 은 로그인 카드와 토스트.
그림자는 순수 검정이 아니라 배경 색조(`rgba(36,24,58,…)`)를 섞는다.
행 스택에는 그림자를 쓰지 않는다. 행은 뜨는 것이 아니라 목록이다.

## Shapes

- **10px** 표면(카드, 인용 상자, 알림, 컴포저 박스)
- **8px** 컨트롤(버튼, 입력, 아이콘 버튼, 각주 칩)
- **999px** 알약(칩, 스위치, 세그먼트, 절차 번호)

이 셋 밖의 값은 쓰지 않는다.

## Components

### 상태 줄 (statusbar)
`role="status"`. 다섯 개의 사실만 싣는다. 현행 문서 수 / 판본 / 마지막 갱신 /
폐기 수 / 근거 확인 중인 답변 수. 마지막 항목이 이 제품에서 가장 자주 오해받는 상태다.

### 행 스택 (stack)
`[마크] 제목 / 부제 [배지] [날짜]`. 전폭이고 호버는 상태 레이어 5%.
카드로 만들지 않는 이유는 이 목록이 훑는 대상이지 고르는 대상이 아니기 때문이다.

### 컴포저 (ask)
하단 고정. 위에 진입점 세그먼트 두 개가 붙어 플레이스홀더와 안내 문구를 바꾼다.
운영 원칙 §1 의 두 진입점은 서로 다른 봇이 아니라 **같은 봇이 답변 순서를 바꾸는 것**이라,
브라우징이 아니라 묻는 방식의 속성으로 두었다.

### 답변 4유형

| 유형 | 렌더 | 인용 |
|---|---|---|
| 행정 확답 | 결론 → `근거 문서와 핵심 기준` → `절차와 준비` → `바로 할 수 있는 다음 행동` | 있음 |
| 맥락 확인 | 공감 → 확인 질문 **정확히 한 개** → 부담 낮은 칩 | 인용 UI 자체가 없음 |
| 근거 없음 | 고정 거절 문장 → 부모님께 여쭐 질문 3개 → 짧은 정서 지지 | 없음 |
| 안전 우선 | 규정 안내 중단 → 안전 확인 → 어른 4단계 → 상담전화 109 | 없음 |

어른 연결 순서 고정: 부모님 → 가정부장님 → 공직자·목회자·사모님 → 신뢰하는 가까운 어른.
안전 우선에서는 피드백 액션 바를 그리지 않는다.

### 인용 (cites)
도착 전에 `근거를 확인하는 중입니다` 로 **자리를 먼저 잡는다.** 백필 실측 약 15초,
폴링 2초 × 15회. 자리를 미리 잡지 않으면 늦게 뜬 카드가 화면을 밀어 CLS 가 생긴다.

헤더에 `참고한 자료 N건` 과 `검색 N건` 을 나란히 둔다.
인용 0건과 검색 실패는 다른 상태이고, 접으면 `검색되었지만 인용되지 않은 자료` 목록이 나온다.

`approximate` 가 하나라도 있으면 `MessageCitations.tsx` 와 같은 규칙으로 목록 전체를
근사로 본다. 라벨이 `참고 가능한 자료 N건` 이 되고 각주 번호와 형광펜을 어느 카드에도
붙이지 않으며, 고지 문단이 맨 위에 한 번만 놓인다.

### 피드백
긍정 `정확함 · 도움 됨 · 친절함 · 명확함 · 기타`,
부정 `부정확함 · 도움 안 됨 · 근거 부족 · 너무 김 · 부적절 · 기타`. `types/api.ts` 의 실제 라벨이다.

## Do's and Don'ts

**Do**
- 상태 줄에는 사실만 싣는다. 숫자가 바뀌면 자리가 흔들리지 않게 tabular-nums 를 쓴다.
- 비동기로 오는 것에는 자리를 먼저 잡는다.
- 배지는 색과 글자를 함께 쓴다. 색만으로 뜻을 전하지 않는다.
- 모든 버튼과 탭 최소 44px. 호버 5%, 누름 10% 상태 레이어.
- 라벨은 입력 위에, 오류는 입력 아래에. 오류 문구에 무엇을 하면 되는지까지 적는다.
- 후속질문은 입력창에 채우기만 한다. 자동으로 보내지 않는다. 최대 3개.

**Don't**
- 히어로를 만들지 않는다. 가로 스크롤 레일도 쓰지 않는다.
- 그라디언트를 쓰지 않는다. 기준본의 `linear-gradient(135deg,#4E3079,#603B94,#855BC6)`
  히어로가 이 안이 지운 대표적인 것이다. 스켈레톤도 시머가 아니라 단색 펄스다.
- `cite_count` 를 숫자로 노출하지 않는다.
- 숫자 신뢰도를 만들지 않는다. 상태는 근거 있음 / 근거 불충분 / 문서에 없음 셋뿐이다.
- 1인칭을 쓰지 않는다. 문서가 주어다.
- 시스템 프롬프트, 내부 분류, RAG 동작 방식을 노출하지 않는다(운영 원칙 §6).
- 별점, 대화 수, 팔로워를 쓰지 않는다. 인기 수치는 "가장 많이 쓴 답이 맞는 답인가"라는
  잘못된 질문을 만든다.
- 노치 폰 목업을 쓰지 않는다.
- em-dash(`—`, `–`)를 쓰지 않는다.
- `window.addEventListener('scroll')` 을 쓰지 않는다.
- 라이트 모드에서 `#855BC6` 이상 밝기의 보라를 fill 로 쓰지 않는다.
- 이모지를 아이콘으로 쓰지 않는다. SVG 만 쓰고 스트로크는 1.7px 로 통일한다.
