# 블레싱 네비게이션 클라이언트 시안 3종 (후속)

`docs/prototypes/blessing-nav-2026-08-05/` 의 후속입니다. 명제 3개와 브랜드 보라, 8화면 구성,
답변 4유형은 그대로 두고 **메인 화면의 정보 구조만 다시 짰습니다.**

`compare.html` 을 열면 세 시안을 같은 상태로 나란히 볼 수 있습니다. 빌드 도구는 필요 없습니다.

## 왜 메인만 바꿨나

기준본의 메인 셋은 표현만 색인 / 카드 / 노선도로 달랐고 골격은 같았습니다.

```
[큰 제목] → [2칸 진입점] → [봇 5개 목록]
```

여기에 네 가지 문제가 있었습니다.

1. 봇 목록이 화면의 절반을 차지하는데, 세 안 모두 상태 갤러리에 `bots.length === 1` 이면
   메인을 건너뛴다고 적어 두었습니다. 실사용에서 거의 안 나오는 것에 자리를 가장 많이 줬습니다.
2. 메인에 입력창이 없어 질문을 누르면 대화 시작 화면으로 한 번 더 이동해야 했습니다.
3. 화면에서 가장 큰 활자가 "무엇을 하러 오셨나요"였습니다. 정보량이 0입니다.
4. 재방문 상태가 B안에만 있어 A와 C의 메인은 매번 처음처럼 보였습니다.

## 세 안이 메인에서 하는 일

| | 메인의 본문 | 회색조 실루엣 |
|---|---|---|
| **A 색인** | 표제어 24개 색인 + 우측 발췌. 봇은 하단 각주로 | 좌 긴 목록 + 우 발췌 |
| **B 시스템** | 상태 줄 + 진행 중 대화 / 문서 변경 / 담당 범위 전폭 행 + 하단 고정 컴포저 | 좌 사이드바 + 전폭 행 + 하단 입력 |
| **C 경로** | 노선도 하나. 선=문서, 역=질문, 금색=환승, 파선=노선 없음 | 여백 큰 전면 다이어그램 |

가장 큰 활자에는 셋 다 사실을 넣었습니다. 무엇이 현행인지, 언제 갱신됐는지, 지금 무엇이 진행 중인지.

## 파일

```
a-register.html  + a-register.DESIGN.md   taste-skill
b-system.html    + b-system.DESIGN.md     ui-ux-pro-max
c-route.html     + c-route.DESIGN.md      frontend-design
compare.html                              세 창 동시 조종
assets/emblem.svg                         두 색 벡터 (--em-field / --em-mark 로 재채색)
_diag.html  _audit.html                   390px 렌더 · 가로 스크롤 검사
```

`*.DESIGN.md` 는 google-labs `design.md` 규격입니다.
`npx @google/design.md lint` 로 검증하고 `export --format css-tailwind` 로 Tailwind v4 `@theme` 을 뽑을 수 있습니다.

## 해시 라우팅

`a-register.html#thread/admin/dark/mobile` 형태이고 **순서는 상관없습니다.**
각 토막을 알려진 어휘(화면 8 / 답변 4 / light·dark·auto / desktop·mobile)에 대조해 배정합니다.
`#dark/mobile/thread/admin` 도 같은 상태입니다.

헤드리스 브라우저는 `prefers-color-scheme: dark` 를 보고하므로 라이트 화면을 찍으려면
해시에 `/light` 를 명시해야 합니다.

## 기술 메모

- 자립형 정적 HTML. 외부 의존은 폰트 CDN 뿐입니다. 엠블럼은 `assets/emblem.svg` 를
  각 파일에 `<symbol>` 로 인라인해 뒀습니다. 인라인해야 `--em-field` / `--em-mark` 로
  재채색되기 때문입니다. `assets/emblem.svg` 는 원본으로 남겨 둡니다.
- 반응형은 미디어 쿼리가 아니라 컨테이너 쿼리입니다. `.app` 이 `container-type: inline-size` 이고
  내부는 `@container app (min-width: …)` 로 반응합니다.
- 프로토타입 크롬은 1100px 미만에서 폭을 돌려주므로 390px 문서에서 앱이 진짜 390px 로 렌더됩니다.
- 노치 폰 목업을 쓰지 않습니다. 좁은 폭에서는 화면 전체를 앱이 씁니다.
- 그라디언트가 한 곳도 없습니다. 스켈레톤은 단색 펄스, 파선은 `border-style: dashed` 입니다.
  `grep -c gradient` 가 세 파일 모두 0 을 반환합니다.
- 모션은 `--motion` 단일 변수로 통제합니다. `animation: none !important` 를 쓰면 OS 에서
  동작 줄이기를 켠 사용자에게 수동 토글이 영구히 먹지 않습니다.
- 스트리밍 타이핑은 `Intl.Segmenter('ko', {granularity:'grapheme'})` 로 분절하고
  화면 전환 시 `AbortController` 로 중단합니다.

## 코드에 옮기기 전에 필요한 것

세 시안이 그렸지만 지금 코드로는 값을 채울 수 없는 것이 둘 있습니다.

1. **인용 대기 상태.** `ChatProvider.tsx` 의 백필 폴링(2초 × 15회, 실측 약 15초)에
   진행 상태가 노출되지 않습니다. 컨텍스트가 내보내는 값에 폴링 여부가 없어 바인딩할 변수가 없습니다.
2. **검색되었지만 인용되지 않은 문서 목록.** `Citation[]` 에는 인용된 것만 옵니다.
   인용 0건과 검색 실패를 화면에서 구분하려면 백엔드가 검색 결과 목록을 함께 보내야 합니다.

그 밖에 `frontend-client/src/app/globals.css` 의 `--primary` 가 아직 앰버이고
`layout.tsx` 가 Geist 만 로드해 한글이 시스템 폴백으로 떨어집니다. `.dark` 블록은 라이트 값을
복사하고 있습니다. 어느 안을 고르든 이 셋은 먼저 정리해야 합니다.

## 화면의 데이터

봇 이름, 문서명, 규정 내용, 인용문, 계정 정보는 전부 UI 검토용 예시입니다.
실제 규정이나 승인 문서가 아닙니다.
