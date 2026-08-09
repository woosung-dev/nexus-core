---
version: alpha
name: 말문 (The Opening)
description: >
  블레싱 멀티봇 클라이언트의 의도 진입 변형. 명제는 하나다. 홈은 목록이 아니라 말을 여는
  자리다. 운영 원칙이 규정한 두 진입점(알아보기 / 나누기)과 컴포저를 홈의 본문으로 올리고,
  창구는 배정 결과로만 등장한다. 시그니처는 답변 조립 안무다. 결론에서 근거, 절차, 다음으로
  순서대로 자리를 잡고, 각주를 누르면 본문 구간과 우측 자료 카드가 하나의 밑선으로 이어진다.
  재질은 종이 겹이다. 그림자는 검정이 아니라 잉크 보라를 탄다. 보라는 납작한 잉크로만 쓰고
  AI 응답 뒤에 틴트로 깔지 않는다.
colors:
  paper: "#F6F3F8"
  surface: "#FFFFFF"
  surface-2: "#EFE9F4"
  surface-3: "#E6DEEE"
  ink: "#2E1D4D"
  ink-2: "#584A72"
  ink-3: "#6F6285"
  rule: "#E2DAEC"
  rule-2: "#CDC0DC"
  act: "#523A82"
  primary: "#523A82"
  on-act: "#FFFFFF"
  act-soft: "#EDE6F7"
  act-line: "#B9A4D6"
  gold: "#C9A227"
  gold-ink: "#6B5000"
  gold-soft: "#FAF2DA"
  danger: "#A3231B"
  danger-soft: "#FBEDEB"
  ok: "#256B4B"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-paper: "#150F1E"
  dark-surface: "#1D1628"
  dark-surface-2: "#251D33"
  dark-surface-3: "#2E2440"
  dark-ink: "#EDE7F5"
  dark-ink-2: "#BCAFCE"
  dark-ink-3: "#978AAA"
  dark-rule: "#332843"
  dark-rule-2: "#43355A"
  dark-act: "#C3A9E6"
  dark-on-act: "#1B1226"
  dark-act-soft: "#2B2140"
  dark-gold: "#D9B84A"
  dark-gold-ink: "#EBD48A"
  dark-gold-soft: "#2C2416"
  chrome: "#161022"
typography:
  display:
    fontFamily: Pretendard Variable
    fontSize: 40px
    fontWeight: "700"
    lineHeight: 1.22
    letterSpacing: -1.28px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 17px
    fontWeight: "550"
    lineHeight: 1.6
    letterSpacing: -0.26px
  heading:
    fontFamily: Pretendard Variable
    fontSize: 16px
    fontWeight: "650"
    lineHeight: 1.35
    letterSpacing: -0.24px
  body:
    fontFamily: Pretendard Variable
    fontSize: 15.5px
    fontWeight: "400"
    lineHeight: 1.72
    letterSpacing: 0
  quote:
    fontFamily: Maru Buri
    fontSize: 13.5px
    fontWeight: "400"
    lineHeight: 1.78
    letterSpacing: 0
  label:
    fontFamily: Pretendard Variable
    fontSize: 11px
    fontWeight: "600"
    lineHeight: 1.4
    letterSpacing: 1.1px
  cite:
    fontFamily: Pretendard Variable
    fontSize: 11.5px
    fontWeight: "550"
    lineHeight: 1.6
    letterSpacing: 0
  meta:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0
spacing:
  unit: 4px
  scale: [2, 4, 6, 9, 12, 14, 18, 22, 26, 30, 40, 44, 72]
rounded:
  card: 14px
  field: 12px
  small: 8px
  pill: 999px
elevation:
  flat: none
  raised: 0 1px 2px rgba(46,29,77,0.06), 0 1px 1px rgba(46,29,77,0.04)
  lifted: 0 2px 6px rgba(46,29,77,0.07), 0 6px 16px rgba(46,29,77,0.06)
  floating: 0 4px 10px rgba(46,29,77,0.08), 0 14px 34px rgba(46,29,77,0.10)
  bevel: inset 0 1px 0 rgba(255,255,255,0.7)
---

# 말문 (The Opening)

## Overview

**명제: 홈은 목록이 아니라 말을 여는 자리다.**

`docs/guides/축복챗봇_운영원칙_v1.md:12-17` 은 첫 화면에 두 진입점(축복 정보 알아보기 /
고민 나누기)을 두고 "두 진입점은 별도 봇이 아니다"라고 못박는다. 직전 네 라운드의 메인은
전부 카탈로그였고 이 원칙을 구현하지 않았다. 이 안은 컴포저와 두 진입면을 홈의 본문으로
올리고, 창구는 다섯 갈래로 묶어 그 아래에 둔다.

Design Read: 문서 근거 멀티봇 RAG 챗봇 클라이언트의 redesign-overhaul.
2세 청년 당사자와 부모 세대 실무자가 같은 첫 화면을 쓴다. 따뜻한 기관 언어.

Dials: DESIGN_VARIANCE 7 / MOTION_INTENSITY 6 / VISUAL_DENSITY 5.
직전 라운드는 6/3/6 이었다. 사용자가 만듦새 부족을 지적하고 모션과 재질을 직접 골랐으므로
overhaul 규칙(+2/+2/유지)을 적용했고, 밀도만 6에서 5로 낮췄다. 처음 오는 청년이 첫 화면에서
출발할 수 있어야 하기 때문이다.

## Colors

브랜드 보라 한 갈래만 행동을 맡는다. `act #523A82` 는 흰 글씨 대비 9.2:1 이다.

금색은 **등급이 아니라 위치 표시**다. 인용문 안에서 "실제로 이 대목이 답에 쓰였다"를
가리키는 밑선으로만 쓰고 글자색으로 쓰지 않는다(`gold #C9A227` 은 본문 대비 2.2:1 이라
글자에 쓸 수 없다. 글자급이 필요하면 `gold-ink #6B5000`, 7.0:1).

**보라를 AI 표식으로 쓰지 않는다.** 그라디언트, 글로, 히어로 오브, 그리고 AI 응답 뒤에 깔리는
틴트가 전부 없다. 인용을 켤 때도 배경을 칠하지 않고 `inset 0 -1.5px 0 var(--act)` 밑선 하나로
본문 구간과 자료 카드를 잇는다.

## Typography

본문 Pretendard, 규정집 인용문만 마루부리, 메타는 IBM Plex Mono.
인용문에 명조를 쓰는 것은 규정집 문장이 UI 문자열이 아니라 문서로 읽히게 하는 장치다.
리디북스(Pretendard + RIDIBatang)와 크랙(Pretendard + 명조 4종)이 실제로 쓰는 조합이다.

`word-break: keep-all` + `overflow-wrap: break-word` 를 전역으로 넣는다. 없으면 한글이
낱말 중간에서 끊긴다. 본문 자간은 0 이고 큰 표제만 음수로 조인다.

Paperlogy 와 Freesentation 은 쓰지 않는다. 전자는 장식체(제목용)이고 후자는 웹폰트 임베딩이
조건부 허용이라 별도 서면 허락이 필요하다.

## Layout

| 화면 | 골격 |
|---|---|
| 로그인 | 좌 브랜드 면(큰 엠블럼) + 우 SSO 버튼 하나. 입력란이 없으므로 면적을 브랜드에 쓴다 |
| 홈 | 표제 → 컴포저 → 두 진입면(1.32 : 1 비대칭) → 이어가던 이야기 → 창구 다섯 갈래 |
| 대화 | 본문 단 + 우측 자료 레일 316px. 1060px 미만에서 레일이 본문 아래로 |
| 창구 상세 | 마크 + 이름 + 능력 표기 → 보는 문서 → **이 창구가 답하지 않는 것** |

두 진입면은 균등 카드 두 장이 아니다. 폭이 다르고 재질도 다르다. 규정 쪽은 흰 표면에
그림자를 얹고, 마음 쪽은 그림자 없이 종이 톤으로 눕는다.

반응형은 미디어 쿼리가 아니라 컨테이너 쿼리다. `.app` 이 `container-type: inline-size` 이다.

## Elevation

다섯 계단이고 그 사이 값을 쓰지 않는다. **그림자는 검정이 아니라 잉크 보라 `rgba(46,29,77,…)`
를 탄다.** 이 한 줄이 화면을 종이처럼 눕힌다. 흰 표면에 순수 검정 그림자를 쓰면 회색 때가 낀다.

## Shapes

카드 14px, 입력 12px, 작은 것 8px, 알약 999px. 이 넷 말고 다른 값을 쓰지 않는다.

## Components

**인용 알약.** 위첨자 숫자가 아니라 문서 이름 알약이다. 앞에 `&nbsp;` 를 넣어 홀로 줄바꿈되지
않게 하고, 카드가 열려 있는 동안 알약은 켜진 채로 있다. 폭이 넘치면 카드가 아니라 알약 안에서
줄인다.

**유형 라벨.** `규정집 · 안내 · 지침 · FAQ` 는 전부 같은 색이다. 등급이 아니라 종류다.
표시가 붙는 것은 `개정 이전 판본` `문서 단위로만 확인` 같은 부정적인 경우뿐이고,
표시가 없다는 것은 "검증됨"이 아니라 "적을 것이 없음"이다.

**검색 영수증.** 검색 단계를 흘리다가 `근거 2건 · 검색 2.1초` 한 줄로 접힌다.
이 화면이 있어야 인용 0건과 검색 실패가 구분된다.

**상시 도움 자리.** 컴포저 위에 분류기와 무관하게 늘 눌러서 도움을 청할 수 있는 자리를 둔다.
안전 카드는 서비스의 목소리이므로 어시스턴트의 말과 시각적으로 분리한다.

## Motion

모든 애니메이션은 위계·서사·피드백·상태전환 중 하나를 한 문장으로 설명할 수 있어야 한다.
장식으로 도는 무한 루프는 없다.

| 대상 | 하는 일 |
|---|---|
| 화면 진입 | 본문이 한 번 올라온다. 어디로 왔는지 알리는 상태 전환 |
| **답변 조립** | 결론에서 근거, 절차, 다음으로 순서대로 자리를 잡는다. 읽는 순서를 몸이 먼저 안다 |
| 절차 항목 | 70ms 간격 스태거. 차례가 있다는 것을 보여준다 |
| 자료 레일 | 본문이 끝난 뒤 옆에서 들어온다. 본문이 먼저라는 위계 |
| 확인 중 점 | 아직 끝나지 않았다는 상태 표시. 유일한 반복 애니메이션 |

`prefers-reduced-motion` 과 수동 토글을 모두 존중한다. 끌 때 `animation: none` 대신
duration 을 0 으로 만든다. `none` 을 쓰면 `both` 가 풀려 시작 상태에 머무는 요소가 생긴다.

## Do's and Don'ts

**Do**

- 답변은 전폭 문서로 놓는다. 말풍선은 사용자 발화에만 쓴다
- 창구 정체성은 헤더에 한 번만 둔다. 응답마다 아바타를 붙이지 않는다
- 능력 표기는 사용자의 기대와 어긋나는 쪽만 적는다
- 창구 상세에 "이 창구가 답하지 않는 것"을 적는다
- 안전 번호는 109 와 마들랜 둘을 적는다

**Don't**

- 보라 그라디언트, 글로, 히어로 오브, AI 응답 뒤 틴트
- 위첨자 맨 숫자 각주, 신호등 색 배지, 숫자 신뢰도
- `cite_count` 노출, RAG·strict·history_window 등 구현어 노출
- 1인칭 화법("제가 찾아봤는데요"). 문서를 주어로 쓴다
- `.thread` 같은 다른 클래스에서 `display` 선언. 화면 표시는 `[data-on]` 하나가 정한다
