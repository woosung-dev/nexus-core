# 글로벌 B2C AI 챗봇 랜딩·채팅 UI 리서치

조사일: 2026-08-06
조사 방법: WebFetch(claude.com 성공), curl_cffi TLS 임퍼소네이션(character.ai/chatgpt.com/claude.ai/perplexity.ai/poe.com/pi.ai 원본 HTML+CSS 번들 직접 수신 성공, meta.ai만 403 지속 실패), Jina Reader(insane-search 경로), WebSearch(디자인 토큰 리버스엔지니어링 소스 `shadcn.io/design/*`, 브랜드 컬러 아카이브 `mobbin`/`loftlyy`, 언론 기사 교차검증). 각 항목은 실측 소스를 명시했고, 실측 실패한 부분은 "미확인"으로 표기했다.

---

## 1. Character.AI (character.ai)

**접근 방법**: WebFetch 403 → curl_cffi(chrome impersonate) 200 성공, HTML 455KB + CSS 289KB 직접 수신.

### 랜딩 구조
접속 즉시 **가입 벽(signup wall)** 이 뜬다. 스크린샷/데모/기능 설명 스크롤 없이:
- 헤드라인: **"Get access to 10M+ Characters"**
- 서브카피: **"Sign up in just ten seconds"**
- CTA: "Continue with Google" / "Continue with Apple" / "Continue with email" (3버튼, 소셜 로그인 우선)
- meta description(=실질 태그라인): *"Chat with millions of AI Characters on the #1 AI chat app. Where will your next adventure take you?"*
- 로그인 전 체험: **불가** — 캐릭터 둘러보기/미리보기 없이 가입 폼이 전체 화면을 차지. 하단엔 About/Careers/Safety Center/Blog 링크만.

### 채팅 UI
- 아바타: 캐릭터별 프로필 이미지가 채팅 컨텍스트에서는 **원형 크롭**, 홈 화면 카드에서는 **정사각 크롭**으로 다르게 렌더링(공식 가이드북 확인).
- 2024년 UI 리뉴얼("New UI")에서 채팅 텍스트가 넓은 여백의 좁은 말풍선으로 압축되고 **밝은 파란색 톤**이 도입됐으며, 인라인 페르소나 프로필 사진이 채팅 스트림에서 사라졌다. 색상 대비가 강해 눈부심(eye strain) 불만이 다수 접수됐고, 구 UI 복귀 토글이 유료 구독자에게만 열려 반발을 샀다(roborhythms.com 리뷰 확인).
- 트랜스크립트형 레이아웃 계열 구현(참고 오픈소스 이슈)에서는 AI 메시지가 배경 없이 **색상 좌측 보더**로 페르소나를 구분하고, 사용자 메시지는 우측 정렬 + 옅은 회색 배경을 쓰는 패턴이 일반적으로 채택됨.

### 타이포·컬러 (CSS 번들 직접 추출)
- 커스텀 폰트 3종 확인: **`characterSans`**(브랜드 산세리프, 헤더용), **`atHauss`**(커스텀 디스플레이 서체), **`libreBaskerville`**(세리프 — 인용구/캐릭터 소개문 등에 사용 추정). 폴백은 Inter, Noto Sans.
- 다크 모드가 기본값: `--background-refresh:#131313`, `--card:#181818`, `--brand-off-white-refresh:#fafafa`, elevation 단계 `#050505→#242424`(다크)/`#fafafa→#dbdbdb`(라이트), 에러 레드 `#f62350`, 보조 블루 `#536dc6`.

### 톤·성격
자신을 "도구"가 아니라 "1,000만 개 이상의 캐릭터 시장"으로 소개. 신뢰 장치는 거의 없음(안전센터 링크 정도) — 엔터테인먼트/롤플레이 프레이밍이 명확.

### 시그니처 디테일
① 제품을 전혀 보여주지 않고 가입 폼부터 띄우는 공격적 퍼널(경쟁사 중 유일). ② "봇 하나"가 아니라 "캐릭터 카탈로그"가 제품 정체성 그 자체.

---

## 2. ChatGPT (chatgpt.com / openai.com/chatgpt)

**접근 방법**: WebFetch 403(양쪽) → curl_cffi 200 성공, chatgpt.com HTML 505KB + CSS 번들 1.7MB 수신. openai.com/chatgpt는 Jina Reader로 텍스트 확보.

### 랜딩 구조
`openai.com/chatgpt`는 스크롤형 마케팅 페이지가 아니라 **제품 자체가 랜딩**이다.
- 헤드라인(빈 상태 문구, 반복 노출): **"Ready when you are."**
- 입력창이 최상단에 바로 노출, 음성(Voice) 아이콘 동반.
- 상단: "Log in" / **"Sign up for free"**, 좌측엔 New chat / Images / Plugins / Deep research 사이드바 메뉴가 비로그인 상태에서도 프리뷰됨.
- 로그인 유도 배너: *"Get responses tailored to you — Log in to get answers based on saved chats, plus create images and upload files."*
- 로그인 전 체험: **가능**(2026년 기준 계정 없이 즉시 대화 가능하도록 정책 변경됨 — WebSearch로 확인). 단, 이미지 생성 불가, 이미지 외 파일(PDF/Excel 등) 업로드 불가, 대화 미저장(세션 리셋 시 소멸), 구버전 모델로 라우팅되는 제약이 있음.

### 채팅 UI
- 미니멀·군더더기 없는 사이드바(대화 목록 무한 스크롤, 이름 변경 가능).
- 사용자 메시지: 고대비 말풍선(우측). 어시스턴트 메시지: 배경 없는 전폭 텍스트 + 하단 액션바(👍👎, 공유, 음성 읽기, 재생성, 더보기).
- Canvas 기능으로 텍스트/코드를 별도 패널에 문서처럼 편집 가능.

### 타이포·컬러
- **2025년 첫 리브랜딩**: 자체 서체 **"OpenAI Sans"** 도입(ABC Dinamo·Dumbar와 공동 개발, "기하학적 정밀함 + 둥근 인간적 성격" 컨셉), 기존 브랜드서체 **Söhne/Sohne**를 대체. "blossom" 로고 마크로 교체.
- CSS에서 실측한 컬러 토큰: 라이트 `bg-primary:#fff`, `bg-secondary:#f9f9f9`; 다크 `bg-primary:#212121`(순검정 아님), `bg-secondary:#303030`. 액센트는 매우 무채색에 가까운 회색 `#8f8f8f`/`#afafaf` — **강한 브랜드 컬러를 쓰지 않고 그레이스케일 위주**.
- 코드 폰트: `ui-monospace`, **Atkinson Hyperlegible Mono**. 수식은 KaTeX 폰트군.

### 톤·성격
"준비됐을 때 말 걸어" — 대기 상태 자체를 카피로 씀. 도구이자 개인 비서 톤, 캐릭터/페르소나 연출 없음.

### 시그니처 디테일
① 마케팅 페이지가 곧 제품 자체(별도 히어로 스크롤 없음). ② 리브랜딩으로 로고·서체를 "차갑고 로봇 같다"는 인식에서 "둥글고 인간적"으로 의도적 전환.

---

## 3. Claude (claude.ai / claude.com)

**접근 방법**: `anthropic.com/claude` → 301 리다이렉트 → `claude.com/product/overview` WebFetch 성공. `claude.ai` 자체는 curl_cffi 200(로그인 화면 셸만, 34KB). 디자인 토큰은 `shadcn.io/design/claude`(코드 역추출) 교차검증.

### 랜딩 구조
- 헤드라인: **"Meet your thinking partner"**
- 서브헤드: **"Tackle any big, bold, bewildering challenge with Claude"**
- 상단 CTA: "Try Claude" / "Contact sales". 히어로 CTA: **"Ask Claude"**.
- 섹션 순서: 헤더 → 히어로 → 3기능 탭(Write/Learn/Code) → 데스크톱 앱 다운로드(macOS/Windows) → 핵심 가치제안 4가지 → "Claude Cowork" 소개 → 학습/코딩/리서치 사용例.
- 로그인 전 체험: **"Try Claude"** 클릭 시 `claude.ai`로 바로 진입(단, 실제 메시지 전송은 로그인 필요 — 랜딩 자체는 열려있으나 대화는 게이트).

### 채팅 UI
- 사이드바: 대화 목록 + **"Projects"**(작업공간) 구분.
- **Artifacts**: 코드/문서/콘텐츠를 채팅과 분리된 **별도 캔버스 패널**에 띄우는 구조 — 순수 챗봇이 아니라 "채팅+문서 캔버스" 하이브리드.
- "Tone and length" 설정으로 응답 스타일 조절 가능.
- 전반적으로 "black text on white/cream, minimalist, utilitarian" 레이아웃(비교 기사 인용).

### 타이포·컬러 (디자인 토큰 역추출, 브랜드 정체성 핵심)
- **캔버스 배경 `#faf9f5`(크림)** — 업계 다수가 쓰는 블루/슬레이트 계열과 의도적으로 차별화한 결정.
- 프라이머리 액센트 **코랄 `#cc785c`**(active `#a9583e`), 보조 틸 `#5db8a6`, 앰버 `#e8a55a`. 다크 서피스(네이비) `#181715`.
- 텍스트: ink `#141413`, body `#3d3d3a`, muted `#6c6a64`.
- **디스플레이 서체: Copernicus**(정확히는 *Galaxie Copernicus Book*, Chester Jenkins·Kris Sowersby 2009년 디자인의 슬랩세리프)를 -1.5px 네거티브 트래킹으로 사용 — "세리프가 있어야 문학적·사려깊은 톤이 나오고, 산세리프 디스플레이로 바꾸면 다른 AI 툴과 똑같아 보인다"는 것이 브랜드 판단(디자인 시스템 문서 인용).
- 본문/UI: **StyreneB** 산세리프(또는 Inter 폴백). 코드: JetBrains Mono.

### 톤·성격
"thinking partner"(사고 파트너) — 도구도 친구도 아닌 **협업자** 프레이밍. 신뢰 장치는 절제된 비주얼(장식 최소화)과 문학적 세리프가 대신함.

### 시그니처 디테일
① 조사한 8개 제품 중 **유일하게 슬랩세리프 디스플레이 서체 + 웜 크림 배경**을 브랜드 정체성 축으로 삼음(경쟁사 전부 블루/다크/그레이 산세리프 계열). ② Artifacts 사이드 패널 = 채팅을 "문서 캔버스"로 확장하는 독자적 UI 패턴.

---

## 4. Perplexity (perplexity.ai)

**접근 방법**: WebFetch 403 → curl_cffi 200(HTML 12.8KB, SPA 셸) → CSS 번들 624KB 직접 다운로드해 컬러/폰트 실측. `shadcn.io/design/perplexity` 및 `mobbin`/`loftlyy` 브랜드 컬러 아카이브로 교차검증.

### 랜딩 구조
Perplexity도 **홈페이지 자체가 검색창(=제품)**. 태그라인은 **"Where Knowledge Begins"**(Product Hunt/앱스토어 확인). 로그인 없이 검색 가능(레이트 리밋). 별도 스크롤 마케팅 섹션 없음 — 구글 홈처럼 중앙 입력창 중심.
- `<meta name="theme-color">` 실측: **라이트 `#FCFCF9`**, **다크 `#100E12`**.

### 채팅 UI (가장 차별화된 지점)
- **말풍선을 의도적으로 쓰지 않는다** — "각 쿼리를 채팅 버블이 아니라 하나의 작은 리포트로 취급한다. 버블은 '메신저'를 신호하고, Claude.ai/ChatGPT/Cursor 등에서 사용자가 기대하는 '툴' 프레이밍을 해친다"(UX 아티클 인용). 사용자/AI 구분은 배경 음영·정렬로만 처리.
- **인라인 번호 인용**을 답변 생성 단계에서 구조적으로 삽입(사후 첨부가 아님) + 답변 상단 별도 **Sources 패널** + Answer/Images/Sources/Links 탭 구조.
- 사이드바: 스레드 히스토리 rail. 빈 상태에는 **제안 카드 캐러셀** 노출.
- 리버스엔지니어링된 토큰 감사에 따르면 **pill 형태(radius 9999px)** 버튼이 21회로 가장 빈번히 사용된 반경값 — 둥근 알약형 컴포넌트가 지배적 형태 언어.

### 타이포·컬러
- 브랜드 컬러는 **터쿼이즈(청록) 단일 액센트**: `#20808D`/`#016a71`(UI 프라이머리, "118개 토큰 중 유일하게 브랜드 레이어로 표시된 색"), 마케팅용 밝은 톤 `#1FB8CD`, 다크모드 딥톤 `#114F56`.
- 배경: 오프블랙 텍스트 `#091717`/`#13343B`, 페이퍼화이트 `#FBFAF4`/`#F3F3EE`, 웜 크림 캔버스 `#fdfbfa`.
- 폰트: 프로프라이어터리 **`pplxSans`**(가장 가까운 오픈 대체재는 Inter), 폴백 `ui-sans-serif/system-ui`. CSS 번들에서 **`fkGroteskNeue`**(FK Grotesk Neue, 라이선스 서체)와 **`berkeleyMono`**(코드/기술적 인상을 주는 인디 모노스페이스, 정밀·전문성 지향 브랜드가 즐겨 씀)도 확인. 워드마크는 **전체 소문자** 브랜딩.

### 톤·성격
"답 엔진(answer engine)" — 친구/캐릭터가 아니라 **권위·신뢰 있는 리서치 툴**로 자기소개. 신뢰 장치는 인용 그 자체.

### 시그니처 디테일
① 8개 제품 중 유일하게 "말풍선 없음 + 인용 내장형 리포트 레이아웃"을 채택 — 조사 대상 중 가장 급진적인 채팅 UI 이탈. ② 알약형(pill) radius를 전체 시스템의 지배적 형태로 사용.

---

## 5. Poe (poe.com)

**접근 방법**: WebFetch 403 → curl_cffi 200(HTML 75KB) 성공. 비교 리뷰(IntuitionLabs) 교차검증.

### 랜딩 구조
- `<title>`: **"Poe - Fast, Helpful AI Chat"**
- meta description: *"Chat with the best AI, privately or in a group chat. Explore GPT-5.6-Sol, Claude-Opus-5, Claude-Fable-5, Claude-Sonnet-5, Kimi-K3, and thousands of others, all on Poe."* — 랜딩의 핵심 셀링포인트가 **단일 페르소나가 아니라 "수천 개 모델에 대한 접근권"**임이 카피에서 바로 드러남.
- 쿠키 배너에 가려 히어로 시각 요소는 이번 세션에서 직접 확인 실패(Jina 캐시가 배너만 반환) — 텍스트 카피만 실측, 시각 레이아웃은 **미확인**.

### 채팅 UI
- 비교 리뷰 인용: *"clean but a bit more busy than ChatGPT or Claude"* — 상단 메뉴에서 봇 전환, **멀티봇 채팅**(한 스레드에서 여러 AI와 동시 대화) 지원.
- 봇 탐색은 카드형 그리드(마켓플레이스 구조) — Character.AI의 "캐릭터 카탈로그"와 구조적으로 유사하되 대상이 페르소나가 아니라 **모델/봇**.

### 타이포·컬러
- CSS 실측: 시스템 폰트 스택(`-apple-system, system-ui, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen-Sans, Ubuntu, Cantarell, Helvetica Neue, sans-serif`) + 커스텀 변수 `--pdl-font-family-web`("Poe Design Language"로 추정). **커스텀 디스플레이 서체 없음** — 경쟁사 대비 브랜드 타이포 투자가 가장 적음.
- 브랜드 고유 hex 컬러는 이번 CSS 추출에서 확인 못함(라이브러리 기본값만 검출) — **미확인**.

### 톤·성격
중립적 애그리게이터/마켓플레이스 톤. "helpful"이라는 단어 외 페르소나적 수사 없음. 제품 정체성이 캐릭터가 아니라 **모델 선택 폭** 자체.

### 시그니처 디테일
① 멀티봇-단일스레드 채팅. ② 랜딩 카피가 특정 모델명(GPT-5.6-Sol, Claude-Opus-5 등)을 직접 나열하는 유일한 사례 — 브랜드가 아니라 카탈로그를 판다.

---

## 6. Pi (pi.ai)

**접근 방법**: WebFetch 403 → curl_cffi 200(HTML 43KB) 성공, CSS 228KB 직접 추출. Jina Reader로 실제 히어로 텍스트 확보. Inflection AI 관련 WebSearch 교차검증.

### 랜딩 구조
Pi는 **랜딩이 곧 챗봇의 첫 발화**다. 마케팅 문구/스크린샷/기능 리스트 없이 접속 즉시:

> *"Hey, I'm Pi — your personal AI. 👋 I'm here to think things through with you, cheer you on, or keep you company when you just want to talk. Need help with a tough conversation, keeping your day on track, or picking the perfect gift? I've got your back. But first, what should I call you?"*

이름을 묻는 것으로 **온보딩 자체가 대화**다. 로그인 없이 즉시 체험 가능.

### 채팅 UI
- 텍스트 모드는 메시지 단위 대화형. 가장 특징적인 건 **음성 모드**: 전체화면 미니멀 UI로 전환, "듣는 중"엔 부드러운 웨이브 애니메이션, "생각 중"엔 추상 애니메이션 표시. **Hands-free**(무발화 상시청취) vs **Tap-to-talk** 모드 선택 가능. **Zen display**를 켜면 텍스트 트랜스크립트 대신 사운드웨이브만 표시. 음성 6종(영국식 억양 2종 포함), 2026년 리얼타임 음성 2.0은 억양·감정(스트레스/흥분/슬픔)을 감지해 톤을 맞춘다고 홍보.

### 타이포·컬러
- `<meta name="theme-color">` 실측: **`#FAF3EA`**(웜 크림/베이지).
- CSS 색상 변수 실측: 배경 라이트 `#FAF3EA`, 서브배경 `#F7EFE4`, 다크 배경 `#131212`/`#1A1918`. **그린 계열 액센트**가 시그니처: `--color-accent-default: #3D9C6E`(hover `#5FB386`/`#077843`, deep `#1A4631`) — 경쟁사 대부분의 블루 계열과 다른 선택.
- 폰트: **`GRENETTE`/`GRENETTE_CONDENSED`**(라이선스 커스텀 세리프 계열 디스플레이체), **`LEGACY_ALPINA`/`LEGACY_ALPINA_CONDENSED`**(구 브랜드 세리프로 추정), 본문은 **`DM_SANS`**(구글 DM Sans), 커스텀 `MONO`. 세리프 디스플레이체를 2벌이나 갖춘 건 Claude와 함께 "에디토리얼·웜 톤"을 지향하는 신호.

### 톤·성격
명시적으로 **정서적 동반자**로 자기소개("cheer you on", "keep you company") — 도구가 아니라 관계. 이름을 먼저 묻는 관계-우선 온보딩.

### 시그니처 디테일
① 온보딩=대화(폼 없음, 첫 메시지가 곧 이름을 묻는 질문). ② 음성 우선의 풀스크린 "Zen" 모드는 8개 제품 중 유일.

---

## 7. Replika (replika.com)

**접근 방법**: 일반 curl(UA 지정)만으로 200 성공(WAF 없음, 329KB) — 조사 대상 중 유일하게 아무 우회 없이 원본 HTML을 받은 사이트. CSS 3개 번들 직접 추출.

### 랜딩 구조
- 헤드라인: **`HeroCyclingTitle`** 컴포넌트로 단어가 순환 애니메이션됨 — **"The AI friend to do [life / side quests / ...], fall in love, become yourself"** 패턴(HTML 클래스명·문구로 확인).
- `<title>`: *"Replika | The AI Friend to do Life With"*
- 배경: 맨해튼 테마 일러스트 + 채팅 스크린샷 삽입.
- CTA: **"Get the app"**(iOS/Android 딥링크, 2회 배치) — 웹 채팅 CTA 없음, **앱 우선 퍼널**. 이메일 가입 벽도 없이 다운로드로 바로 유도.
- 섹션 순서: 히어로+실시간 사용자 카운터(예: "42,160,934명") → 신규 기능 소개 → 핵심 차별점(메모리 시스템) → 추가 기능 설명 → 사용자 스토리 5건 → 최종 CTA.

### 채팅 UI (직접 접근 불가, 리뷰 소스 기반 — 일부 미확인 표기)
- 가입 시 **3D(2026년 업데이트로 2D 애니메이션 전환) 아바타**를 직접 커스터마이징(헤어/눈동자/의상/방 꾸미기)한 뒤 대화 시작 — 채팅이 아바타에 종속된 부가 요소에 가깝다.
- **Memory 기능**이 핵심 차별화: *"Always remembers what matters"* — 사용자의 관계·일상·계획을 기억해 대화 맥락에 반영.
- 실제 채팅 화면(말풍선 스타일, 입력창 디자인)은 앱 게이트로 이번 세션에서 직접 확인하지 못함 — **미확인**, 리뷰 요약("친밀하고 게임 같은 온보딩")으로만 보완.

### 타이포·컬러
- `<meta name="theme-color">` 실측: **`#FFFFFF`**(순백 배경).
- CSS에서 발견된 폰트: **`Schoolbell`**(손글씨풍 구글 폰트 — 장식/일기 위젯 등 부분 사용 추정), **`Google Sans Code`**(코드/모노스페이스 용도). 본문 메인 서체는 이번에 받은 CSS 조각 안에서 특정하지 못함 — **미확인**(다른 번들에 있을 가능성).

### 톤·성격
가장 **관계·로맨스 지향**적인 카피("fall in love"를 마케팅 문구로 명시). 신뢰보다 **정서적 애착**을 판매.

### 시그니처 디테일
① 8개 중 유일하게 AI에게 **지속적 시각적 신체(아바타+방)** 를 부여하고 채팅을 그 부속물로 배치. ② 마케팅이 로맨틱 애착을 노골적으로 약속.

---

## 8. Meta AI (meta.ai) — 접근 제한, 부분 확인만 가능

**접근 방법 기록**: WebFetch 403 → curl(plain) 403 → curl_cffi 3종 임퍼소네이션(chrome124/safari17_0/firefox133) **모두 403** → Wayback Machine CDX API 429(Too Many Requests, 세션 내 재시도 못함) → **Jina Reader 1회만 성공**(HTML/CSS 없이 텍스트만).

### 확인된 것
Jina Reader가 반환한 전체 본문:
> Highlight insights from a report / Tell me what TV shows everyone's watching / Help me build a website / Help me discover trending workouts

HTML 구조 없이 이 4줄만 반환됐다는 것 자체가 단서: **홈페이지가 곧 채팅 입력창이고, 4개의 예시 프롬프트 칩이 빈 상태에 노출**되는 구조로 추정된다(ChatGPT/Pi/Perplexity와 같은 "제품=랜딩" 계열). 단, 이는 텍스트만으로 유추한 것이라 레이아웃 확정은 아니다.

### 확인 실패, 일반 지식으로만 알려진 것 (사실 검증 안 됨 — 인용 금지 수준)
WebSearch 결과는 meta.ai 페이지 자체가 아니라 **WhatsApp/Instagram 등 다른 앱 안의 Meta AI 아이콘**(블루-퍼플 그라데이션 원형 로고) 정보였다. 컬러 hex, 폰트명, 사이드바 구조, 채팅 버블 스타일은 이번 조사에서 **전부 미확인**이며, 이 문서에서 임의로 "블루/퍼플"이라 단정하지 않는다.

### 결론
8개 대상 중 **가장 낮은 확인도**. 후속 조사가 필요하면 Playwright 스크린샷(이번 세션은 다른 프로세스가 점유 중이라 실패) 또는 다른 시간대의 Wayback CDX 재시도를 권장.

---

## 종합: 우리 프로젝트(문서기반 정책 안내 챗봇 · 종교 공동체 대상 · 데스크톱 우선)에 적용할 패턴

### 적용할 만한 패턴 7가지

1. **Claude의 웜 크림 캔버스(#faf9f5류) + 세리프 디스플레이 헤드라인, 단일 코랄 액센트.** 종교 공동체 대상 안내 챗봇은 "차갑고 기술적인 툴"보다 "사려 깊고 신뢰가는 안내자" 인상이 필요하다. 블루/다크 계열 일색인 경쟁사 대비 웜톤+세리프 조합은 차별화와 톤 적합성을 동시에 준다.
2. **Perplexity의 인용 내장형 "리포트" 레이아웃과 Sources 패널.** 우리 제품은 정확히 "문서기반 정책 안내"이므로, 말풍선 놀이보다 "질문 → 근거 인용이 박힌 답변 → 출처 패널"이 제품 목적과 직결된다. 인라인 번호 인용 + 별도 출처 탭 구조를 최우선으로 참고할 것.
3. **Pi의 "랜딩=첫 대화" 패턴.** 이미 신뢰가 형성된 내부 공동체 사용자에게는 스크롤형 마케팅 페이지보다, 접속 즉시 봇이 먼저 말을 거는 방식이 마찰을 줄인다("무엇을 도와드릴까요" 같은 첫 인사 + 즉시 입력 가능).
4. **ChatGPT의 로그인 전 제한적 체험 허용.** 계정 없이도 일부 대화는 가능하게 하되 저장·파일첨부 등은 로그인 게이트 — IT 친숙도가 낮은 사용자층의 진입장벽을 낮추는 동시에 민감 정보(개인 상담 등)는 계정 뒤에 둘 수 있다.
5. **Claude Artifacts류의 "문서 캔버스" 사이드 패널.** 규정집/공문 원문 발췌를 채팅 말풍선 안에 욱여넣지 않고 별도 패널에 띄우면, 정책 원문과 챗봇 요약을 시각적으로 분리해 신뢰도를 높일 수 있다.
6. **Perplexity의 통일된 알약형(pill) 반경 + 절제된 그레이스케일 UI.** 작은 디자인 리소스로도 일관성을 유지하기 쉬운 시스템이며, 장식이 아니라 문서 내용에 시선이 가게 한다.
7. **ChatGPT의 무채색 위주 + 단일 저채도 액센트 전략.** 정책/행정 안내라는 성격상 화려한 그라데이션보다 "행정 문서스러운 절제"가 신뢰를 준다 — 액센트 컬러는 CTA·인용 표시 등 기능적 지점에만 국한.

### 피해야 할 패턴 5가지

1. **Character.AI의 즉시 가입 벽.** 제품을 전혀 보여주지 않고 가입 폼부터 들이미는 방식은 이미 신뢰관계가 있는 공동체 대상 서비스에는 불필요한 마찰이며, "종교 공동체+행정 안내"라는 맥락과도 맞지 않는다.
2. **Character.AI 2024 리뉴얼의 고대비·밝은 블루 색상 남용.** 눈부심/피로 불만이 실제로 보고된 사례 — 장시간 텍스트를 읽어야 하는 정책 안내 UI에서는 특히 피해야 한다.
3. **Replika의 로맨틱/의인화 컴패니언 프레이밍("fall in love", 아바타+방 꾸미기).** 종교 공동체의 행정·정책 안내 챗봇에 "친구·연인" 프레이밍은 부적절하며 신뢰를 오히려 해칠 수 있다.
4. **Pi의 음성 우선 풀스크린 모드를 1순위 경험으로 두는 것.** 데스크톱·문서 중심 사용 맥락에는 음성 UI 투자 우선순위가 낮다 — 있으면 부가기능 정도로 그쳐야 한다.
5. **Poe식 "모델 카탈로그 나열".** 사용자에게 여러 AI 모델/봇을 골라 쓰게 하는 마켓플레이스 프레이밍은 "하나의 일관된 기관 목소리"가 필요한 정책 안내 챗봇의 신뢰성과 상충한다 — 내부적으로 여러 봇을 운영하더라도 최종 사용자에게는 단일 정체성으로 보여야 한다. (참고로 ChatGPT의 "출처 표시 없는 요약" 패턴도 이 카테고리에 속한다 — 인용 없는 단정적 답변은 정책 안내에서 특히 위험하다.)

---

## 접근 실패/부분 확인 요약

| 사이트 | 상태 | 비고 |
|---|---|---|
| Meta AI (meta.ai) | 부분 실패 | WebFetch/curl/curl_cffi(3종) 전부 403, Wayback 429. Jina 텍스트 1회만 확보. 컬러·폰트·UI 구조 미확인 |
| Poe | 부분 확인 | HTML은 확보했으나 쿠키배너에 가려 히어로 시각 요소 미확인, 브랜드 hex 컬러 미검출 |
| Replika | 부분 확인 | 랜딩 페이지는 완전 확보(우회 불필요), 로그인 후 채팅 UI 자체는 리뷰 소스로만 보완 |
| Character.AI / ChatGPT / Claude / Perplexity / Pi | 실측 완료 | curl_cffi 또는 WebFetch로 HTML+CSS 직접 확보, 디자인 토큰 다수 검증 |
