블레싱 네비게이션 클라이언트를 단일 봇 화면에서 **멀티봇 플랫폼 화면으로** 확장한다.
인터뷰로 진행해도 좋다. "왜" "어떻게"를 물어봐도 된다.

## 먼저 읽을 것 (실제로 열어라)
docs/prototypes/blessing-nav-r2-2026-08-05/  a-register.html · README.md   ← 기준본
docs/prototypes/_compare4.html                                            ← 1회차 3안과 기준본 대조판
frontend-client/src/components/landing/BotCard.tsx, BotGrid.tsx           ← 지금의 멀티봇 UI
backend/app/models/bot.py
docs/guides/축복챗봇_운영원칙_v1.md

## 재정의
블레싱은 목표가 아니라 첫 번째 봇이다. 이 제품은 RAG 챗봇을 필요에 따라 여러 개 만들어
제공하는 시스템이다. 기존 시안 셋은 단일 봇으로는 좋지만 멀티봇을 의도적으로 미뤘다
(셋 다 `bots.length === 1` 이면 메인을 건너뛴다고 적어 놨다). 이번엔 그걸 정면으로 다룬다.

디자인 언어는 이어간다. 보라 #603B94 계열, 골드는 검증된 근거 의미색(선 전용),
답변 4유형, 어른 연결 순서, 데이터 계약(cite_count 비노출, approximate 전체 적용).

## 재조사하지 말고 그대로 쓸 사실
`Bot` 모델: name, description, image_url, tags[], is_verified, is_new,
plan_required(FREE|PRO), system_prompt, llm_model, use_rag, is_active, created_at, updated_at,
evidence_policy_mode("strict"|"legacy"), history_window(int)

사용자 경험을 바꾸는데 화면에 없는 것:
  use_rag:false → 인용이 영영 안 나옴 · strict → 인용 없는 답을 차단 ·
  history_window:0 → 앞 대화를 기억 못 함 · plan_required:PRO → 부딪힐 게이트 ·
  updated_at 은 모델엔 있고 BotResponse 엔 없음

API에 아예 없는 것 (화면은 그리되 README에 백엔드 선행 과제로 남겨라):
  봇↔문서(코퍼스) 연결 — 봇을 구별하는 가장 중요한 축인데 클라이언트가 알 수 없다
  봇 그룹/카테고리 · "이 질문은 어느 봇 담당인가"의 판단 근거

현재 멀티봇 UI는 `BotGrid.tsx` 의 균일 카드 4열 격자다. 이것이 바꿀 대상이다.

## 시작할 때 3개만 물어라
1) 봇이 지금 몇 개이고 1년 뒤 몇 개일 것 같은가. 평평한 목록인가, 무엇으로 묶이는가
2) 한 사용자가 보는 봇이 전부인가, 소속에 따라 다른가
3) 봇마다 다른 동작(기억 안 함 / strict 차단 / RAG 없음)을 사용자에게 알릴 것인가 숨길 것인가
   운영 원칙 §6은 내부 분류·RAG 동작 노출을 금지한다. 그런데 "이 봇은 기억하지 않습니다"는
   구현이 아니라 사용자와의 약속이다. 그 선을 어디에 그을지 답을 받아라.
답이 모호하면 가장 그럴듯한 해석을 택하고 한 줄로 밝힌 뒤 진행해라.

## 그릴 것
기존 8화면 유지. 멀티봇 때문에 바뀌는 것:
- 봇 고르기(현 메인) — 봇이 3개·12개·40개일 때 각각 성립해야 한다. 무엇으로 봇을 구별할지
  먼저 정하고 그 축으로 세워라
- 봇 상세 — "이 봇이 무엇인가"가 아니라 **옆 봇과 무엇이 다른가**에 답한다
- 대화 — 어느 봇과 이야기 중인지 항상 보인다. 봇을 바꾸면 무엇이 유지되고 무엇이 끊기나

새로 그릴 것:
- **이관**: "이건 제 담당이 아닙니다. 『가정 정책 길잡이』가 그 문서를 봅니다."
  시안 셋이 규칙으로만 적고 아무도 안 그렸다. 답변 5번째 유형으로 볼지 판단해라
- 봇 능력 표기 (인터뷰 3번 답을 따라라)
- 빈 상태: 볼 봇이 0개, PRO에 막힘, 비활성 봇 링크

예시 봇은 **12개 이상**. 5개로는 문제가 안 드러난다. RAG 없음·strict·history 0·PRO·
비활성·일본어·2세 대상을 섞어라.

## 만들 것
docs/prototypes/<새 폴더>/ 에 a/b/c 세 벌 + 각 DESIGN.md + compare.html + README.md.
`blessing-nav-r2-2026-08-05/` 에서 assets/emblem.svg, _diag.html, _audit.html 복사.
DESIGN.md는 google-labs design.md 규격 (스키마 키는 colors/typography/spacing/rounded/components).

## 스킬 — 하나씩 순차로. 동시에 로드하면 규칙이 충돌한다
1. taste-skill      기준본 a의 redesign(§11)으로 진입. 다이얼 선언 + §14 프리플라이트
2. ui-ux-pro-max    Step 2 필수. `python3 /Users/woosung/.claude/plugins/cache/ui-ux-pro-max-skill/ui-ux-pro-max/2.5.0/src/ui-ux-pro-max/scripts/search.py "<쿼리>" --design-system -f markdown`
3. frontend-design  설계안 먼저 쓰고 자기비평한 뒤 구현
세 안이 서로 다른 **멀티봇 명제**를 내야 한다. 같은 격자에 스킨만 다르면 실패다.

## 지킬 것
그라디언트 0, em-dash 0, 노치 목업 0, `cite_count` 숫자 노출 0.
봇을 구별할 때는 이름·담당 문서·능력 표기로 한다 (색·별점·대화 수·인기순 말고).
없는 데이터는 지어내지 말고 README에 선행 과제로 남긴다.
자체 완결 HTML, 빌드 없이 열려야 한다. 해시 라우팅은 순서 무관.

## 이 환경의 사실 (모르면 시간을 버린다)
- Chrome 151이라 `--headless=old` 는 제거됐다. `--headless=new` 를 쓰고,
  스크린샷 후에도 종료하지 않으니 백그라운드로 띄우고 파일이 생기면 죽여라.
- 헤드리스는 `prefers-color-scheme: dark` 를 보고한다. 라이트는 해시에 `/light` 를 명시해라.
- 390px 스크린샷은 헤드리스 최소 창 폭 때문에 잘린다. `_diag.html` iframe 래퍼로 찍어라.
- 정적 서버는 샌드박스 밖에서 띄워야 한다 (`dangerouslyDisableSandbox: true`).

## 작업 방식
요청한 범위를 그대로 해라. 판단이 필요한 건 스스로 정하고, 해석에 따라 결과가 크게
달라질 때만 물어라. 서브에이전트는 넓은 다중 파일 조사처럼 정말 독립적이고 큰 작업에만
쓰고, 몇 번의 도구 호출로 끝낼 일에는 쓰지 마라. 응답은 간결하게.
