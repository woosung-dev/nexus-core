---
version: alpha
name: 색인 (The Register)
description: >
  블레싱 네비게이션 클라이언트의 색인 변형. 메인이 봇 고르는 화면이 아니라 참고서의
  색인이다. 표제어 24개가 헤어라인으로 흐르고 오른쪽에 그 대목의 발췌가 붙는다.
  색은 브랜드 바이올렛 하나가 행동을 맡고, 골드는 검증된 근거가 있다는 표시로만
  선에 쓴다. 카드와 그림자를 쓰지 않고 위계는 활자와 규칙선으로만 만든다.
colors:
  paper: "#F8F5FA"
  surface: "#FFFFFF"
  surface-2: "#F1ECF6"
  ink: "#3B2560"
  ink-2: "#5B4B78"
  ink-3: "#6F6285"
  rule: "#E3DCEC"
  rule-2: "#CCC1DC"
  act: "#523A82"
  primary: "#523A82"
  on-act: "#FFFFFF"
  act-soft: "#EDE6F7"
  gold: "#C9A227"
  gold-ink: "#6B5000"
  gold-soft: "#FBF3DC"
  mark: "#F4E7BE"
  danger: "#A3231B"
  danger-soft: "#FBEDEB"
  ok: "#256B4B"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-paper: "#15121B"
  dark-surface: "#1E1926"
  dark-surface-2: "#272031"
  dark-ink: "#EDEAF2"
  dark-ink-2: "#A79FB4"
  dark-ink-3: "#9C93AB"
  dark-rule: "#332C3E"
  dark-rule-2: "#473F55"
  dark-act: "#C0AAE8"
  dark-on-act: "#1A0F28"
  dark-act-soft: "#241C33"
  dark-gold: "#D9B368"
  dark-gold-ink: "#E4C688"
  dark-mark: "#4C3D12"
  chrome: "#100C18"
typography:
  masthead:
    fontFamily: Paperlogy
    fontSize: 34px
    fontWeight: "900"
    lineHeight: 1.16
    letterSpacing: -1.2px
  heading:
    fontFamily: Paperlogy
    fontSize: 19px
    fontWeight: "700"
    lineHeight: 1.3
    letterSpacing: -0.4px
  section:
    fontFamily: Paperlogy
    fontSize: 14.5px
    fontWeight: "700"
    lineHeight: 1.3
    letterSpacing: -0.3px
  term:
    fontFamily: Pretendard Variable
    fontSize: 14.5px
    fontWeight: "600"
    lineHeight: 1.45
    letterSpacing: -0.17px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 16.5px
    fontWeight: "400"
    lineHeight: 1.75
    letterSpacing: -0.2px
  body:
    fontFamily: Pretendard Variable
    fontSize: 14.5px
    fontWeight: "400"
    lineHeight: 1.85
    letterSpacing: 0
  gloss:
    fontFamily: Pretendard Variable
    fontSize: 12.5px
    fontWeight: "400"
    lineHeight: 1.55
    letterSpacing: 0
  locator:
    fontFamily: Geist Mono
    fontSize: 10.5px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0
spacing:
  unit: 4px
  scale: [2, 4, 6, 8, 11, 14, 18, 22, 26, 30, 38, 44, 56]
rounded:
  row: 0px
  control: 8px
  pill: 999px
elevation:
  flat: none
  frame: 0 24px 70px -28px rgba(0,0,0,0.65)
---

# 색인 (The Register)

## Overview

이 안의 명제는 하나다. **제품의 첫 화면은 고르는 화면이 아니라 찾는 화면이다.**

기준본의 메인은 `[큰 제목] → [2칸 진입점] → [봇 5행]` 이었다. 그 골격에는 세 가지 문제가 있었다.
봇 목록이 화면의 절반을 차지하는데 봇이 1개면 메인 자체를 건너뛰고, 큰 활자가 "무엇을 하러 오셨나요"라는
정보량 0의 문구를 쓰고, 질문을 누르면 대화 시작 화면으로 한 번 더 이동해야 했다.

색인은 그 셋을 한 번에 없앤다. 표제어 24개가 본문이 되고, 봇 5개는 하단의 "담당 색인 5권" 각주로
내려간다. 가장 큰 활자에는 무엇이 현행이고 언제 갱신됐는지를 넣는다. 표제어를 고르면 오른쪽에 그
대목의 발췌가 그 자리에서 뜨고, 「이대로 묻기」가 질문을 입력창에 채운다.

표제어는 두 절로 나뉜다. **규정에 기준이 있는 표제어**는 문서 이름과 쪽수를 갖고 왼쪽에 금색
세로선이 붙는다. **규정으로 답을 내지 않는 표제어**는 근거 자리에 "근거 없이 듣습니다"라고 적고
세로선이 없다. 운영 원칙 §2의 "고민 중심 답변은 규정을 실제로 설명할 때만 근거를 붙인다"를
색인 층위에서 먼저 지키는 장치다.

## Colors

바탕 `#F8F5FA` 기준 실측 대비: 잉크 12.0:1, 보조 7.1:1, 메타 5.2:1, 액션 8.5:1,
흰 글씨 on 액션 9.2:1. 다크 `#15121B` 기준: 잉크 15.6:1, 보조 7.3:1, 메타 6.3:1, 액션 9.0:1.
형광펜은 라이트 10.5:1, 다크 8.9:1.

**액센트는 바이올렛 하나뿐이다.** 페이지 전체에서 행동을 뜻하는 색은 `act` 하나이고,
초록 `ok` 는 연동 상태 같은 실제 시맨틱 상태에만 나온다.

**골드는 색이 아니라 뜻이다.** `#C9A227` 은 바탕 대비 2.2:1 이라 글자에 쓸 수 없다.
표제어 왼쪽 2px 세로선, 발췌 왼쪽 2px 세로선, 근거 카드 왼쪽 2px 세로선. 이 셋에만 쓴다.
글자로 골드가 필요한 자리(읽는 법 번호 등)에는 `#6B5000` (7.0:1) 을 쓴다.

엠블럼은 실제 로고색 `#F8C800` / `#003D84` 를 라이트와 다크 양쪽에서 그대로 유지한다.
로고에는 보라가 없다. 보라는 이 서비스의 UI 색이고 로고색과 별개다.

## Typography

Paperlogy 가 표시용, Pretendard Variable 이 본문, Geist Mono 가 위치 표기다. 세 역할이 분명하다.

- **매스트헤드** Paperlogy 900. 화면당 한 번. 여기에는 반드시 사실이 들어간다.
- **표제어** Pretendard 600. 색인의 주인공이고 14.5px 로 조밀하게 세운다.
- **주석(gloss)** Pretendard 400 12.5px `ink-3`. 표제어 아래 한 줄.
- **위치(locator)** Geist Mono 10.5px. `규정집 · 38` 처럼 문서와 쪽수만 적는다.
  모노를 쓰는 이유는 장식이 아니라 숫자 자리가 세로로 맞아야 훑을 수 있기 때문이다.
- 절차 번호는 `counter(s, decimal-leading-zero)` 로 `01 02 03` 이 된다. 색인의 항목 번호 관습이다.

이탤릭을 쓰지 않는다. 강조는 같은 패밀리의 굵기로만 만든다.

## Layout

**메인(색인)** `@container app (min-width:900px)` 에서 `1.65fr / minmax(316px,1fr)` 2단.
좌우가 각각 독립 스크롤이다. 900px 미만에서는 1단이 되고 발췌는 선택한 행 **바로 아래**로
펼쳐진다. 별도 화면이나 모달로 보내지 않는다. 색인에서 항목을 짚으면 그 자리에서 읽는 것이
책의 동작이기 때문이다.

**대화** `@container app (min-width:940px)` 에서 `minmax(0,1fr) / 320px`. 무거운 열이 **오른쪽**이다.
세션 목록은 앱바의 「지난 대화」 오버레이로 보냈다. 이 배치는 의도적으로 B안(왼쪽이 무거운 사이드바)의
거울상이다. 회색조로 바꿔도 두 안이 구분되어야 한다.

**프로토타입 크롬** 은 좌측 188px 세로 색인 탭이다. 1100px 미만에서는 사라지고 우하단 플로팅
버튼으로 열린다. 크롬이 사라질 때 폭을 온전히 돌려주므로 390px 문서에서 앱이 진짜 390px 로 렌더된다.

카드와 그림자를 쓰지 않는다. 그룹은 `border-top: 1px solid var(--ink)` 로 절을 열고
`border-bottom: 1px solid var(--rule)` 로 행을 나눈다. 한 행에 위아래 선을 함께 두지 않는다.

## Elevation

**평면이다.** 앱 프레임 바깥의 창 그림자 하나를 빼면 그림자가 없다.
깊이는 표면색(`paper` / `surface` / `surface-2`)과 규칙선으로만 표현한다.
선택 상태는 그림자가 아니라 `act-soft` 배경으로 나타낸다.

## Shapes

라운드는 규칙이 있는 혼합이다.

- **0px** 색인 행, 규칙선, 절 구분, 발췌 본문. 색인은 각져야 색인으로 읽힌다.
- **8px** 버튼, 입력, 칩이 아닌 컨테이너, 데모 상자.
- **999px** 칩(후속질문, 피드백 사유)과 스위치.

이 셋 밖의 값은 쓰지 않는다.

## Components

### 색인 행 (entry)
`[골드 세로선] 표제어 / 주석 / 위치` 3요소. 620px 이상에서 위치가 우측 정렬로 빠진다.
`aria-current="true"` 가 선택 상태이고 배경만 `act-soft` 로 바뀐다.
골드 세로선은 `::before` 2×13px 이며 `data-grounded` 가 있을 때만 칠해진다.

### 발췌 (excerpt)
표제어 / 출처 / 본문 / 각주. 본문은 왼쪽 2px 골드 세로선을 갖고, 근거가 없는 표제어면
세로선이 `rule-2` 로 바뀌고 위에 "이 표제어에는 근거 문서를 붙이지 않습니다"가 붙는다.
하단에 「함께 보는 표제어」와 「이대로 묻기」.

### 답변 4유형
운영 원칙 §3·§5 를 그대로 렌더한다.

| 유형 | 렌더 | 인용 |
|---|---|---|
| 행정 확답 | 결론(lead) → `근거` → `절차`(01 02 03) → `다음` 순서 고정 | 있음 |
| 맥락 확인 | 공감 → 확인 질문 **정확히 한 개** → 부담 낮은 칩 | 인용 UI 자체가 없음 |
| 근거 없음 | 고정 거절 문장 → 부모님께 여쭐 질문 3개 → 짧은 정서 지지 | 없음 |
| 안전 우선 | 규정 안내 중단 → 안전 확인 → 어른 4단계 → 상담전화 109 | 없음 |

어른 연결 순서는 고정이다. 부모님 → 가정부장님 → 공직자·목회자·사모님 → 신뢰하는 가까운 어른.
안전 우선에서는 피드백 액션 바를 그리지 않는다.

### 근거 색인 (evidence)
`확인 중` → `참고한 자료 N건` 두 상태를 갖는다. 대기 중에는 스켈레톤이 자리를 잡아
늦게 온 카드가 레이아웃을 밀지 않는다. 백필 실측이 약 15초, 폴링이 2초 × 15회라
이 대기는 없는 상태가 아니라 그려야 하는 상태다.

`approximate` 가 하나라도 있으면 `MessageCitations.tsx` 와 같은 규칙으로 목록 **전체**를
근사로 본다. 라벨이 `참고 가능한 자료 N건` 이 되고, 각주 번호와 형광펜을 어느 카드에도 붙이지
않으며, 고지 문단이 목록 맨 위에 한 번만 놓인다.

`검색되었지만 인용되지 않은 자료` 는 접이식으로 따로 둔다. 인용 0건과 검색 실패는 다른 상태다.

### 피드백
긍정 `정확함 · 도움 됨 · 친절함 · 명확함 · 기타`,
부정 `부정확함 · 도움 안 됨 · 근거 부족 · 너무 김 · 부적절 · 기타`.
`types/api.ts` 의 실제 라벨이다. 임의로 늘리거나 줄이지 않는다.

## Do's and Don'ts

**Do**
- 가장 큰 활자에 사실을 넣는다. 무엇이 현행이고 언제 갱신됐는지.
- 문서를 주어로 쓴다. "『축복 행정 규정집』 12쪽에 따르면".
- 후속질문은 입력창에 채우기만 한다. 자동으로 보내지 않는다. 최대 3개.
- 상태는 근거 있음 / 근거 불충분 / 문서에 없음 셋으로만 말한다.
- 골드는 선으로만 쓴다.
- 모션은 `--motion` 단일 변수로 통제한다. `animation: none !important` 를 쓰면
  OS 에서 동작 줄이기를 켠 사용자에게 수동 토글이 영구히 먹지 않는다.

**Don't**
- 그라디언트를 쓰지 않는다. 배경, 버튼, 스켈레톤 시머, 점선 전부. 스켈레톤은 단색 펄스다.
- `cite_count` 를 숫자로 노출하지 않는다. 문서 랭킹 점수일 뿐이다.
- 숫자 신뢰도(`신뢰도 62%`)를 만들지 않는다.
- 1인칭을 쓰지 않는다. "제가 찾아봤는데요"가 아니라 문서가 주어다.
- 시스템 프롬프트, 내부 분류, RAG 동작 방식을 노출하지 않는다(운영 원칙 §6).
- 근거가 없을 때 문서명이나 쪽수를 만들어 내지 않는다.
- 노치 폰 목업을 쓰지 않는다. 반응형 실물로 렌더하고 뷰포트만 바꾼다.
- em-dash(`—`, `–`)를 쓰지 않는다. 일반 하이픈만 쓴다.
- `window.addEventListener('scroll')` 을 쓰지 않는다.
- 라이트 모드에서 `#855BC6` 이상 밝기의 보라를 fill 로 쓰지 않는다.
- 이모지, placeholder-as-label, 균일 16px radius, 컬러 좌측 보더 스트립을 쓰지 않는다.
