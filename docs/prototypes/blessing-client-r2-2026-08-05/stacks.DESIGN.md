---
version: alpha
name: 서고 (The Reading Room)
description: >
  블레싱 네비게이션 클라이언트의 열람실 변형. 코퍼스가 제품이고 챗봇은 그 색인이다.
  답변은 말풍선이 아니라 조판된 지면으로 온다. 질문은 판면 바깥 여백에 방주로 붙고,
  본문의 위첨자는 지면 하단의 실제 각주단으로 이어진다. 명조는 원문의 목소리, 고딕은
  시스템의 목소리이며 둘은 한 화면에서 절대 섞이지 않는다. 모서리 반경은 어디에도 없다.
colors:
  paper: "#ECEFF1"
  sheet: "#FAFBFC"
  sheet-sunk: "#E1E6EA"
  ink: "#12181D"
  ink-2: "#3D474F"
  ink-3: "#5E6A73"
  rule: "#D3D9DE"
  rule-strong: "#AEB8C0"
  brand: "#1F3A5F"
  brand-quiet: "#E4EAF1"
  on-brand: "#FFFFFF"
  gold: "#A8862B"
  gold-ink: "#6E5410"
  gold-wash: "#F4EFDF"
  danger: "#8E1E17"
  emblem-field: "#F8C800"
  emblem-mark: "#003D84"
  dark-paper: "#101418"
  dark-sheet: "#171C21"
  dark-sheet-sunk: "#1D242A"
  dark-ink: "#E8ECEF"
  dark-ink-2: "#B4BDC4"
  dark-ink-3: "#8B959C"
  dark-rule: "#262E35"
  dark-brand: "#9FBBDC"
  dark-gold: "#D8B45C"
  dark-gold-wash: "#2A2313"
typography:
  source-display:
    fontFamily: MaruBuri
    fontSize: 30px
    fontWeight: "700"
    lineHeight: 1.5
    letterSpacing: -0.2px
  source-title:
    fontFamily: MaruBuri
    fontSize: 20px
    fontWeight: "600"
    lineHeight: 1.55
    letterSpacing: 0
  source-body:
    fontFamily: MaruBuri
    fontSize: 17px
    fontWeight: "400"
    lineHeight: 1.95
    letterSpacing: 0
  source-note:
    fontFamily: MaruBuri
    fontSize: 14.5px
    fontWeight: "400"
    lineHeight: 1.8
    letterSpacing: 0
  system-lead:
    fontFamily: Pretendard Variable
    fontSize: 21px
    fontWeight: "600"
    lineHeight: 1.7
    letterSpacing: -0.2px
  system-body:
    fontFamily: Pretendard Variable
    fontSize: 17px
    fontWeight: "400"
    lineHeight: 1.85
    letterSpacing: 0
  system-label:
    fontFamily: Pretendard Variable
    fontSize: 12.5px
    fontWeight: "600"
    lineHeight: 1.5
    letterSpacing: 0
  marginal:
    fontFamily: Pretendard Variable
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 1.7
    letterSpacing: 0
  folio:
    fontFamily: Pretendard Variable
    fontSize: 12px
    fontWeight: "400"
    lineHeight: 1.5
    letterSpacing: 0
    fontFeature: "tnum"
rounded:
  none: 0
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 28px
  xl: 44px
  xxl: 72px
  measure: 34rem
components:
  sheet:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.system-body}"
    rounded: "{rounded.none}"
    padding: "{spacing.xl}"
  marginal-note:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-3}"
    typography: "{typography.marginal}"
    rounded: "{rounded.none}"
  footnote-entry:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink-2}"
    typography: "{typography.source-note}"
    rounded: "{rounded.none}"
    padding: "{spacing.sm}"
  footnote-entry-focused:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.ink}"
  shelf-entry:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.source-title}"
    rounded: "{rounded.none}"
    padding: "{spacing.md}"
  catalog-input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.system-lead}"
    rounded: "{rounded.none}"
    padding: "{spacing.sm}"
  catalog-input-focused:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
    typography: "{typography.system-label}"
    rounded: "{rounded.none}"
    padding: "{spacing.md}"
    height: 52px
  button-primary-pressed:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.on-brand}"
  button-quiet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    typography: "{typography.system-label}"
    rounded: "{rounded.none}"
    height: 52px
---

# 서고 (The Reading Room)

## Overview

**참조물: 대학 출판부의 신학 단행본과 1970년대 한국 찬송가.** 종이 결이 살아 있는 낱장, 명조로 짠 표제, 작고 정확한 각주, 넓은 바깥 여백, 잉크 한 색.

이 화면의 전제는 하나다. **코퍼스가 제품이고, 챗봇은 그 색인이다.** 사용자가 궁금해하는 것은 챗봇의 의견이 아니라 규정집에 뭐라고 적혀 있는가이다. 그래서 이 화면에서 주인공은 문서이고, 대화는 문서에 이르는 길일 뿐이다.

그 전제가 화면을 결정한다. 홈은 봇 목록이 아니라 **서가**이고, 답변은 말풍선이 아니라 **조판된 지면**이다. 사용자의 질문은 판면 안으로 들어오지 않고 바깥 여백에 **방주**로 붙는다. 본문의 위첨자는 장식이 아니라 지면 하단의 **실제 각주단**으로 이어지고, 거기에 원문 발췌가 조판되어 있다.

**Key Characteristics**

- 모서리 반경이 어디에도 없다. 낱장은 각지다.
- 카드가 없다. 상자로 묶지 않고 여백과 괘선으로 묶는다.
- 그림자가 없다. 깊이는 종이 색의 차이로만 만든다.
- 명조는 원문의 목소리, 고딕은 시스템의 목소리다. 한 문단 안에서 섞이지 않는다.
- 아이콘이 한 개도 없다. 책에는 아이콘이 없다.

## Colors

서고(書庫)는 차가운 방이다. **채도를 거의 전부 걷어내고 금박 하나만 남겼다.**

따뜻한 크림빛 종이에 놋쇠 금색을 얹는 조합은 쓰지 않았다. 지금 어느 사이트에나 있어서 브랜드가 보이지 않게 되고, 무엇보다 이 방의 온도가 아니다. 이 서고의 종이는 푸른 기가 도는 `#ECEFF1`이고, 낱장은 `#FAFBFC`다.

- **Ink `#12181D`** — 본문과 표제. 종이 위에서 15.5:1, 낱장 위에서 17.3:1. 순검정이 아니라 푸른 기가 도는 먹이다.
- **Ink-2 `#3D474F`** (8.2:1) — 각주와 보조 문장. **Ink-3 `#5E6A73`** (4.8:1) — 쪽수, 판본, 방주.
- **Brand `#1F3A5F`** — 깊은 청회색. 링크와 활성 상태에만 쓴다. 주요 버튼은 브랜드색이 아니라 **잉크색**이다. 인쇄물에서 강조는 색이 아니라 농도로 한다.
- **Gold `#A8862B`** — 액센트가 아니라 **의미색**이다. 오류의 빨강이 액센트가 아닌 것과 같다. "이 대목이 실제로 근거가 되었다"는 표시에만 쓴다. 채식 필사본에서 금박이 가장 귀한 구절에만 얹히던 규칙 그대로다. 종이 위 3.0:1이라 글자에는 쓰지 않고, 글자급이 필요하면 **Gold-ink `#6E5410`** (6.2:1)을 쓴다.
- **엠블럼만 채도를 갖는다.** 화면에서 유일하게 원색인 것이 로고이고, 그래서 로고가 눈에 든다.
- 다크 모드는 불 꺼진 서고다. 배경 `#101418`, 낱장 `#171C21`, 잉크 `#E8ECEF`(15.6:1). 페이지 전체가 한 모드로 잠기고 구역별로 뒤집히지 않는다.

### 종이결

바탕에 SVG 난류(`feTurbulence`)를 데이터 URI로 구워 `.055` 불투명도로 얹는다. 이미지 파일이 아니라서 요청이 늘지 않고, **고정 레이어에만 올려서** 스크롤 중 GPU 재도색이 생기지 않는다. 라이트에서는 `multiply`, 다크에서는 `screen`으로 섞는다. 눈에 띄면 실패다. 없으면 화면이 유리처럼 느껴지고, 있으면 종이처럼 느껴지는 정도가 맞다.

## Typography

두 패밀리, 두 역할. 세 번째는 없다.

**MaruBuri** (마루 부리, 네이버) — 원문의 목소리. 인용된 규정 본문, 문서 제목, 각주단. 장문 한글 읽기를 위해 설계된 부리 계열이라 여기 쓰는 이유를 댈 수 있다.
**Pretendard** — 시스템의 목소리. 답변 문장, 라벨, 방주, 버튼.

| 역할 | 서체 | 크기 | 굵기 | 행간 |
|---|---|---|---|---|
| 원문 표제 | MaruBuri | 30px | 700 | 1.5 |
| 문서 제목 | MaruBuri | 20px | 600 | 1.55 |
| 원문 본문 | MaruBuri | 17px | 400 | **1.95** |
| 각주 | MaruBuri | 14.5px | 400 | 1.8 |
| 시스템 도입부 | Pretendard | 21px | 600 | 1.7 |
| 시스템 본문 | Pretendard | 17px | 400 | **1.85** |
| 방주 | Pretendard | 14px | 400 | 1.7 |
| 쪽수·판본 | Pretendard | 12px | 400 | 1.5 (tnum) |

**원칙**

- 판면 폭은 34rem에서 멈춘다. 한글은 한 행이 길면 되읽기가 생긴다.
- 원문 행간 1.95는 인용된 규정이 답변보다 느리게 읽히도록 의도한 것이다. 규정은 훑는 글이 아니다.
- 자간은 0이다. 큰 표제에만 `-0.2px`을 준다.
- `word-break: keep-all`. 규정 용어가 행 끝에서 쪼개지면 안 된다.
- 각주 번호는 위첨자이고, 각주단에서는 매달린 들여쓰기로 받는다.

## Layout

비대칭 편집 격자. 가운데 정렬하지 않는다.

```
바깥 여백        판면 (34rem)                    바깥 여백
┌──────────┬─────────────────────────────┬──────┐
│ 방주      │  결론                        │      │
│ 질문      │  축복후보자 등록에는 서류      │      │
│ 08.05    │  3종이 필요합니다.            │      │
│          │                             │      │
│          │  근거                        │      │
│          │  등록에 필요한 서류는…¹        │      │
│          ├─────────────────────────────┤      │
│          │  1 『축복후보자 등록 안내』 6쪽  │      │  ← 각주단
│          │    제7조(제출 서류) 축복후보자…  │     명조
└──────────┴─────────────────────────────┴──────┘
```

낱장은 화면 가운데가 아니라 **왼쪽 여백을 넓게 두고 오른쪽으로 밀려** 있다. 방주가 들어갈 자리를 실제로 비워 두기 때문이고, 그래서 이 비대칭에는 이유가 있다.

- 여백 단계 4·8·16·28·44·72.
- 1024px 미만에서 방주는 판면 위로 올라가고, 각주단은 그대로 지면 하단에 남는다.
- 각 화면은 서로 다른 짜임을 쓴다. 서가는 서지 목록, 답변은 판면과 각주단, 원문은 좌우 펼침면, 출입은 낱장과 장서 목록, 내정보는 항목 대조표.

## Elevation & Depth

| 단계 | 처리 |
|---|---|
| 0 | 종이 바탕 `paper` |
| 1 | 낱장 `sheet` (종이색 차이만) |
| 2 | 1px `rule` 괘선 |
| 3 | 1px `rule-strong` 또는 `sheet-sunk` |

**그림자는 하나도 없다.** 낱장이 떠 있는 것처럼 보이게 하지 않는다. 낱장은 놓여 있다.

## Shapes

**반경 0.** 버튼, 입력, 낱장, 발췌, 전부 각지다. 예외는 없다.

낱장에 둥근 모서리를 주는 순간 그것은 종이가 아니라 앱의 카드가 된다. 이 화면의 전체 논지가 거기서 무너진다.

## Components

### Sheet

`sheet`는 이 시스템의 유일한 그릇이다. 카드가 없는 대신 낱장이 있고, 낱장 안에서 위계는 괘선과 여백이 만든다. 상하 여백 44px, 좌우 44px.

### Marginal Note

`marginal-note`는 판면 바깥 왼쪽에 놓인다. 사용자가 무엇을 물었는지, 언제 물었는지가 여기 있다. 판면 안으로 들어오지 않는 이유는, 질문은 문서의 일부가 아니기 때문이다.

### Footnote Apparatus

이 시스템의 시그니처다. 본문 위첨자를 누르면 지면 하단 각주단의 해당 항목이 `footnote-entry-focused`로 잠깐 물든다. 각 항목은 번호, 문서 제목, 판본, 쪽수를 머리에 달고 원문 발췌를 명조로 싣는다. 발췌 안에서 실제로 근거가 된 대목만 금빛 밑선을 받는다.

각주 번호는 `approximate` 인용에는 붙지 않는다. 재검색으로 찾은 문서는 답변 문장과 짝지을 수 없으므로 번호 없이 각주단 아래 별도 문단으로 낸다.

### Shelf Entry

`shelf-entry`는 매달린 들여쓰기의 서지 항목이다. 문서 제목은 명조, 판본과 발행처와 쪽수는 고딕. 상자가 아니라 괘선으로 나뉜다.

### Catalog Input

질문 입력은 상자가 아니라 **한 줄의 괘선**이다. 도서관 카드목록의 기입란과 같다. 라벨은 항상 위에 있고 placeholder를 라벨로 쓰지 않는다. 초점을 받으면 괘선이 잉크색으로 굵어진다.

## Do's and Don'ts

### Do

- 원문은 명조로, 시스템의 말은 고딕으로 조판한다.
- 각주는 진짜 각주로 만든다. 지면 하단에 원문 발췌를 싣는다.
- 문서의 판본과 시행일을 본문보다 먼저 낸다.
- 강조는 색이 아니라 농도와 크기로 한다.
- 근거가 없으면 어디까지 찾아봤는지를 먼저 적는다.

### Don't

- 모서리를 둥글리지 않는다. 반경 0이 이 시스템의 뼈대다.
- 따뜻한 크림빛 바탕에 놋쇠 금색을 올리지 않는다. 종이는 차갑다.
- 금색을 글자에 쓰지 않는다. 근거 표시 전용이다.
- 아이콘을 넣지 않는다.

## Motion

`MOTION_INTENSITY: 3`. 열람실은 움직이지 않는다.

움직이는 것은 두 가지뿐이고 둘 다 이유를 한 문장으로 댈 수 있다. 첫째, 각주 번호를 누르면 해당 각주가 잠깐 물든다. 어디로 갔는지 알려주는 피드백이다. 둘째, 근거를 대조하는 동안 괘선 한 줄이 천천히 차오른다. 답변은 이미 끝났고 대조가 남았다는 상태를 알린다.

나머지는 색 전환 160ms뿐이다. `prefers-reduced-motion`을 존중하고, 수동 토글이 그보다 우선한다.

## Responsive Behavior

| 폭 | 처리 |
|---|---|
| ≥1180px | 방주가 판면 왼쪽 바깥에, 낱장은 왼쪽 여백을 넓게 두고 배치 |
| 900–1179px | 방주가 판면 위로 이동, 낱장 가운데 정렬 |
| <900px | 단일 열, 각주단은 지면 하단 유지, 입력 괘선 고정 |

터치 목표는 44×44 아래로 내려가지 않는다. 반경 0이라도 눌리는 영역은 넉넉하다.

## Known Gaps

- 이 화면에는 사진이 없다. 이 제품에는 사진으로 보여줄 것이 없고, 문서 지면 자체가 시각 재료다. 가짜 사진이나 손으로 그린 장식 일러스트를 넣지 않았다.
- 「검색했으나 인용되지 않은 문서」 목록은 현재 API에 없다. 각주단 아래 그 자리를 그려 두었고 값은 채워야 한다.
