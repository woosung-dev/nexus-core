---
version: alpha
name: 접수 (The Intake)
description: >
  블레싱 멀티봇 클라이언트의 접수 변형. 명제는 하나다. 고르는 화면을 없앤다.
  묻기 전에 한 줄만 적으면 그 한 줄이 담당을 정한다. 화면에 있는 것은 입력 한 줄과
  그 아래 결과뿐이고 나머지는 여백이다. 사이드바를 한 곳도 쓰지 않는다.
  A안보다 활자를 한 단계 키우고 밀도를 절반으로 낮췄다.
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
  ask:
    fontFamily: Paperlogy
    fontSize: 30px
    fontWeight: "700"
    lineHeight: 1.35
    letterSpacing: -0.9px
  display:
    fontFamily: Paperlogy
    fontSize: 31px
    fontWeight: "900"
    lineHeight: 1.2
    letterSpacing: -1px
  desk:
    fontFamily: Paperlogy
    fontSize: 16.5px
    fontWeight: "700"
    lineHeight: 1.4
    letterSpacing: -0.4px
  section:
    fontFamily: Paperlogy
    fontSize: 15px
    fontWeight: "700"
    lineHeight: 1.3
    letterSpacing: -0.3px
  lead:
    fontFamily: Pretendard Variable
    fontSize: 17px
    fontWeight: "400"
    lineHeight: 1.85
    letterSpacing: -0.2px
  body:
    fontFamily: Pretendard Variable
    fontSize: 15.5px
    fontWeight: "400"
    lineHeight: 1.9
    letterSpacing: 0
  hit:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 1.7
    letterSpacing: 0
  gloss:
    fontFamily: Pretendard Variable
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 1.7
    letterSpacing: 0
  fact:
    fontFamily: Geist Mono
    fontSize: 11.5px
    fontWeight: "400"
    lineHeight: 1.4
    letterSpacing: 0.02em
spacing:
  unit: 4px
  scale: [3, 6, 9, 12, 16, 20, 26, 32, 38, 46, 56, 72]
rounded:
  row: 0px
  control: 8px
  pill: 999px
elevation:
  flat: none
  frame: 0 24px 70px -28px rgba(0,0,0,0.65)
---

# 접수 (The Intake)

## Overview

**명제: 고르는 화면을 없앤다. 묻기 전에 한 줄만 적으면 그 한 줄이 담당을 정한다.**

봇을 가르는 축은 **질문**이다. 사용자는 창구 목록을 보지 않는다. 한 줄을 적으면
그 낱말이 어느 문서에 있는지 찾고, 그 문서를 보는 창구를 순서대로 보여 준다.
창구를 고르는 것은 그다음이고, 고르지 않아도 된다.

이 안의 화면은 거의 비어 있다. 입력 한 줄과 그 아래 결과가 전부다.
A안이 밀도 6의 2단 색인이라면 이 안은 밀도 2의 1단 접수 서식이다.
회색조로 바꿔도 두 안이 구분되어야 한다.

## ui-ux-pro-max Step 2 에서 무엇을 취하고 무엇을 버렸나

```
search.py "search first navigation intake form" --design-system
search.py "progressive disclosure routing to the right agent" --design-system
search.py "empty state permission gate" --design-system
```

**채택 2건**

1. Marketplace / Directory 패턴의 **"Search bar is the CTA. Reduce friction to search."**
   이 안의 명제와 정확히 같다. 입력이 화면의 주인공이고 목록은 결과다.
2. accessibility-critical 활자 무드(Atkinson Hyperlegible 행). 대상에 부모 세대 실무자가
   있다. 폰트는 브랜드 락이라 바꾸지 않고 **기준 활자 크기를 A안보다 한 단계 올렸다.**
   본문 15.5px, 리드 17px, 입력 30px, 행간 1.9. 이 안은 저밀도라 감당된다.

**기각**

- Funnel 3단계 색(1 빨강 문제 / 2 주황 과정 / 3 초록 해결). 팔레트 락 위반이고,
  규정 안내에 색으로 감정을 붙이면 안 된다.
- Parallax Storytelling. 성능 Poor, 접근성 Poor 로 검색 결과 자체가 명시하고 있다.
  모션 다이얼 2 와도 충돌한다.
- 3D & Hyperrealism. 같은 이유.
- Inter, `#2563EB`, `#F97316`. 브랜드 락.
- 진행 표시기(progress indicator). 이 안의 접수는 단계가 아니라 한 줄이다. 단계를 만들면
  명제가 죽는다.

## Colors

A안과 같은 토큰을 쓴다. 세 안은 한 제품이므로 팔레트가 흔들리면 안 된다.
바탕 `#F8F5FA` 기준 실측 대비: 잉크 12.0:1, 보조 7.1:1, 메타 5.2:1, 액션 8.5:1.

이 안에서 색이 하는 일은 셋뿐이다.

- **바이올렛** 은 행동이다. 접수 순위 표시와 좁히는 질문의 세로선.
- **골드** 는 검증된 근거다. 형광펜(`mark`)과 `strict` 능력 표기의 세로선, 절차 번호.
  선과 배경으로만 쓰고 글자에는 `gold-ink` 를 쓴다.
- **잉크 3단계** 가 나머지 전부를 한다.

접수 결과에 색으로 등급을 매기지 않는다. 순위는 모노 숫자와 골드 세로선 하나로만 표시한다.

## Typography

이 안의 활자는 A안보다 크다. 그것이 밀도 2의 실제 내용이다.

- **접수 입력(ask)** Paperlogy 700 clamp(21px, 3.4cqw, 30px). 화면에서 가장 큰 활자다.
  밑줄 2px 만 있고 박스가 없다. A안의 박스형 검색 입력과 대비된다.
- **사실 줄(fact)** Geist Mono 11.5px. 입력 바로 위. `문서 13종 · 창구 14곳 · 갱신 2026.07.30`.
  **가장 큰 활자가 placeholder 이므로 그 placeholder 를 안내문이 아니라 실제 표제어에서 온
  문장으로 쓰고, 그 위에 사실을 한 줄 얹는다.** 기준본이 지적한 "가장 큰 활자에 정보량 0"을
  피하는 방법이다.
- **창구 이름(desk)** Paperlogy 700 16.5px. 결과 행의 주인공.
- **적중(hit)** Pretendard 400 14px. `『축복 행정 규정집 2026』 38쪽 에서 서류 를 찾았습니다`.
  찾은 낱말에 형광펜이 붙는다.
- **본문** Pretendard 400 15.5px / 1.9.

## Layout

**모든 화면이 1단이다.** `.mid` 가 `max-width: 684px; margin: 0 auto`. 사이드바가 한 곳도 없다.

**메인(접수)** 상단 여백 `clamp(34px, 7cqh, 72px)`. 입력, 사실 줄, 안내 한 문단, 그리고
비어 있음. 적기 시작하면 아래가 자란다.

**결과 행(desk)** 600px 이상에서 `minmax(0,1fr) auto` 2열. 이름/적중/능력이 1열,
문서 수가 2열 우측. 카드가 아니라 규칙선으로 나눈 행이다.

**대화** 1단. **근거가 답변 바로 아래 인라인으로 상주한다.** 640px 이상에서 인용 카드가
2열로 눕는다. A안(오른쪽 패널 상주)과 C안(각주를 눌러야 펼쳐짐)의 중간이 아니라 세 번째 방식이다.

**컴포저** 도 `.mid` 안에 들어간다. 전폭으로 늘어나지 않는다.

## Elevation

**평면이다.** 앱 프레임 그림자 하나뿐. 접수 입력에도 그림자가 없다. 밑줄 2px 이 전부다.

## Shapes

- **0px** 접수 입력의 밑줄, 결과 행, 규칙선.
- **8px** 버튼, 컴포저, 빈 상태 상자, 데모 상자.
- **999px** 칩, 좁히는 질문의 선택지, 접힌 창구 목록의 알약, 스위치.

## Components

### 접수 입력 (ask)
`label` 은 스크린리더용으로 숨기고 시각적으로는 사실 줄이 그 자리를 대신한다.
placeholder 는 안내문이 아니라 실제 표제어에서 온 문장이다(`축복후보자 서류는 무엇이 필요한가요`).
`Enter` 또는 오른쪽 화살표 버튼으로 접수한다. 입력하는 동안 결과가 실시간으로 자란다.

### 접수 결과 (desks)
`담당하는 곳 · N곳 중 M곳` 헤더 + **왜 그 창구인지 한 문단** + 결과 행.

> 적으신 낱말 **서류**가 실린 문서를 보는 곳입니다.
> 이 순서는 문서에 그 낱말이 있는지로만 정했습니다.

**이 문장이 이 안에서 가장 중요하다.** 지금 실제로 그릴 수 있는 배정 근거는 낱말 대조뿐이고,
그것은 근거가 아니다. 그 사실을 숨기지 않고 화면에 적는다. 진짜 판단 근거는 API 에 없다
(README 선행 과제 2).

후보가 4곳을 넘으면 **좁히는 질문을 하나** 드린다. 운영 원칙 §3-B 의 "한 번에 하나만"을
따른다. 나머지는 접이식으로 내린다.

### 능력 표기 (capability)
**규칙: 사용자의 기대와 어긋나는 쪽만 적는다. 기대대로면 아무것도 안 적는다.**
A안과 동일한 문구를 쓴다. 세 안이 같은 약속을 해야 한다.

| 실제 설정 | 화면 문구 |
|---|---|
| `history_window: 0` | 앞 대화를 이어서 기억하지 않습니다. 질문 하나에 답 하나씩 드립니다. |
| `evidence_policy_mode: strict` | 문서에서 근거를 찾지 못하면 답하지 않습니다. |
| `use_rag: false` | 문서를 근거로 답하지 않습니다. 결론을 대신 내리지 않고 함께 정리하는 쪽입니다. |
| `is_active: false` | 지금은 답하지 않습니다. 같은 내용을 『…』가 이어받았습니다. |
| `plan_required: PRO` | 카드에는 적지 않는다. 부딪히는 자리에서만 설명한다. |

결과 행에서는 짧은 형태(`근거를 못 찾으면 답하지 않습니다`), 창구 상세에서는 긴 형태를 쓴다.
RAG, strict, legacy, history_window 는 화면에 한 글자도 나오지 않는다(운영 원칙 §6).

### 창구 상세 (bot detail)
대조 블록이 세로 3절이다. `이 창구만 보는 문서` / `다른 창구와 함께 보는 문서` /
`이 창구가 보지 않는 문서`. A안이 3칸 가로 그리드인 것과 대비된다.
1단 안이므로 세로로 흐르는 편이 맞다.

### 답변 4유형
A안과 동일하다. 운영 원칙 §3·§5 를 그대로 렌더한다. 어른 연결 순서 고정,
안전 우선에서는 피드백 액션 바를 그리지 않는다.

### 이관 (handoff)
**답변 5번째 유형이 아니다.** 「근거 없음」의 하위 갈래 D2 다.

이 안에서 이관은 **접수를 한 번 더 하는 것**이다. 메인에서 보던 결과 행을 대화 안에
그대로 되민다. 사용자가 이미 아는 모양이라 무엇을 고르는지가 분명하다.

```
이 창구는 그 문서를 보지 않습니다. 지어내는 대신 접수를 한 번 더 하겠습니다.
성물 관리는 『가정 생활 규정』 v2.0 15쪽에 실려 있습니다.

이 한 줄로 다시 접수했습니다
  1  가정 정책 길잡이       『가정 생활 규정 v2.0』 15쪽 에서 성물 을 찾았습니다
  2  봉헌식·의례 안내       ...
  [여기서 계속하기]

고르시면 적으신 한 줄이 그대로 넘어갑니다. 지금까지의 대화와 근거는 넘어가지 않습니다.
```

D2 는 봇↔문서 연결이 있어야만 성립한다. 없으면 D1(부모님께 여쭐 질문)로 떨어뜨린다.

### 근거 (evidence)
답변 바로 아래 인라인 상주. `확인 중` / `참고한 자료 N건` / `참고 가능한 자료 N건` /
`인용된 자료 없음` 네 상태. `approximate` 가 하나라도 있으면 목록 전체를 근사로 보고
각주 번호와 형광펜을 어느 카드에도 붙이지 않는다.
`검색되었지만 인용되지 않은 자료` 는 접이식으로 따로 둔다.

## 규모: 3곳, 14곳, 40곳에서 무엇이 되고 무엇이 안 되나

해시로 직접 볼 수 있다. `#home/n0` `#home/n3` `#home/n14` `#home/n40`
접수 결과 상태는 `#home/asked` `#home/asked/n40` `#home/asked0`(담당 없음).

| 규모 | 성립 | 무너지는 곳 |
|---|---|---|
| **1곳** | **성립하지 않는다** | 접수 자체가 군더더기다. 적은 한 줄이 그대로 첫 질문이 되어 대화가 시작되어야 한다. 이 안의 명제가 무너지는 유일한 규모다 |
| **3곳** | 성립하지만 약하다 | 배정이 시시하다. 세 곳을 다 보여 주는 편이 빠르므로 접수 아래에 셋을 항상 펼쳐 두고, 적으면 순서만 바뀌게 했다 |
| **14곳** | 잘 맞는다 | 후보가 보통 1~3곳이라 좁히는 질문이 거의 안 나온다 |
| **40곳** | **가장 잘 맞는다** | 40곳을 고르는 것은 불가능하므로 접수가 유일한 진입로가 된다. 후보가 12곳까지 늘어나 좁히는 질문이 실제로 필요해진다 |

**이 안이 진짜로 잘하는 것**: 창구가 몇 개든 사용자의 첫 동작이 하나다.
**이 안이 진짜로 못하는 것**: 배정 근거가 낱말 대조뿐이라 지금은 정직하게 그것을 적는 수밖에
없다. 백엔드가 판단 근거를 주기 전까지 이 안은 절반만 진짜다.

## Do's and Don'ts

**Do**
- 가장 큰 활자에 사실을 넣는다. 입력이 가장 크므로 placeholder 를 실제 질문 문장으로 쓰고
  그 위에 문서 수와 갱신일을 얹는다.
- 왜 그 창구인지를 문서 이름으로 밝힌다. 순위만 보여 주지 않는다.
- 배정 근거가 약하면 약하다고 화면에 적는다.
- 후보가 넷을 넘으면 좁히는 질문을 한 번에 하나만 한다.
- 능력은 기대를 배신하는 쪽만 적는다.
- 골드는 선과 형광펜으로만 쓴다.

**Don't**
- 그라디언트를 쓰지 않는다.
- 사이드바를 쓰지 않는다. 이 안은 1단이다.
- 접수를 단계로 쪼개지 않는다. 한 줄이다.
- 결과에 색으로 등급을 매기지 않는다. 신뢰도 숫자를 만들지 않는다.
- `cite_count` 를 숫자로 노출하지 않는다.
- 봇을 색, 별점, 대화 수, 인기순으로 구별하지 않는다.
- 시스템 프롬프트, 내부 분류, RAG 동작 방식을 노출하지 않는다(운영 원칙 §6).
- 근거 없이 남의 창구를 지목하지 않는다.
- 노치 폰 목업을 쓰지 않는다.
- em-dash(`—`, `–`)를 쓰지 않는다.
- `window.addEventListener('scroll')` 을 쓰지 않는다.
- 이모지, placeholder-as-label(label 은 스크린리더용으로 반드시 둔다), 균일 16px radius를 쓰지 않는다.
