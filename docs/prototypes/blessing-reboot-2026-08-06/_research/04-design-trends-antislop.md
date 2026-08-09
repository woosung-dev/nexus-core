# 2025~26 AI 제품 디자인 트렌드 & AI-slop 회피 리서치

조사일 2026-08-06. Mobbin/Godly/Landingfolio/Awwwards/siteinspire/Dribbble/Pinterest + 디자인 트렌드 아티클을 WebSearch·WebFetch·`insane-search`(Pinterest 우회)로 조사했다.

**접근 실패 기록**: Godly는 `godly.website`가 `recent.design`으로 301 리다이렉트되어 있어 원 갤러리 접근 실패(대체: Awwwards SaaS/AI 카테고리, Landingfolio로 보완). Saaspo(`saaspo.com`)는 403으로 차단(대체: Landingfolio·Lapa Ninja로 보완). Pinterest는 로그아웃 상태에서 첫 검색어("AI chat UI design 2025")는 결과가 전혀 로드되지 않았고("You are signed out" 벽), 두 번째 검색어("AI landing page editorial minimalist design")만 핀 8개가 텍스트로 로드됨 — 핀 설명 대부분이 저품질(제목만 있고 출처 도메인 불명)이라 참고용으로만 인용. Dribbble의 특정 컬렉션(`7521345-AI-inspo`)은 실제로는 챗봇/스마트홈 목업 위주로 최신 에디토리얼 트렌드와는 결이 달라 인용을 최소화했다.

---

## 1. 2025~26 랜딩 트렌드

**레이아웃 — 미니멀은 끝나지 않았고 "베ントー화" 되었다.** Apple의 기능 소개 그리드 이후 베ントー 그리드가 SaaS/AI 제품 표준이 됐고, 2026 방향은 정적 타일에서 한발 더 나아가 호버 시 타일이 슬라이드로 열리거나 비디오를 재생하는 "동적 베ントー"로 진화 중이다. 동시에 에디토리얼/스토리텔링 레이아웃(잡지 편집 구조, 커스텀 사진 크롭, 인용구 조판)이 순수 미니멀리즘의 대안으로 부상 — "표현적 단순함(expressive simplicity)": 미학을 위한 미니멀이 아니라 개성을 가진 명료함.

**모션 수위.** 2026 웹은 뷰포트 스케일 타이포(`vw` 단위로 스크롤에 따라 글자가 압축·확장·굵기 전환되는 kinetic typography)가 히어로 이미지를 대체하는 핵심 아키텍처 요소로 부상. 다만 과용 시 접근성 리스크(스크롤 하이재킹, 모션 민감성)가 지적된다. 재질 쪽에서는 WebGL 대신 가벼운 CSS 노이즈/필름 그레인 오버레이로 "디지털 완벽함"을 깨는 아날로그 텍스처가 늘고 있다 — 2025년의 무균질한 매끈함에 대한 반작용.

**컬러 경향.** 순백보다 **크림/오프화이트 + 클래식 세리프** 조합이 "에디토리얼하고 격상된" 느낌을 주는 전략으로 다수 보고됨. 다크 모드는 여전히 강세이나 Linear의 2025 리디자인처럼 "칼라를 줄이고 흑백 대비 위주로" 가는 절제형과, 여전히 네온 글로/보라 그라디언트를 쓰는 구형 SaaS 톤이 갈린다 — 후자는 정확히 AI-slop 신호로 지목된다(§2 참조).

**Serif 부활 — 그리고 그 자체가 새로운 밈이 되고 있다는 반론.** Perplexity(PP Editorial New, Studio Freight 제작), Anthropic/Claude, Runway, Manus가 나란히 세리프를 인터페이스에 들였다. Perplexity 커뮤니케이션 총괄 Jesse Dwyer는 Wired에 "우리는 사람을 위해 디자인한다(designs for humans)"고 명시적으로 밝혔다 — 인쇄물의 신뢰·권위 연상을 세리프로 빌려오는 전략. 디자이너 Keya Vadgama는 이를 "AI에 대한 대중의 불신에 대응해 온기와 인간 저작감을 투사하려는 시도"로 분석. 그러나 비판도 명확하다 — "무리 짓기(herd mentality)"에 불과하고, 세리프가 시스템이 실제로 갖지 않은 행위주체성을 암시해 "AI가 무엇인지에 대한 정확한 정신 모델에 오히려 역행한다"는 지적, 그리고 이 흐름 자체를 "tasteslop"이라 부르는 비평까지 나왔다. → **세리프 자체도 무비판적으로 쓰면 2026년의 새 그라디언트-보라가 될 수 있다.** (출처: aichatdaily.com 분석, Medium "5 free alternative serif fonts to Editorial New seen on Perplexity", Fonts In Use "Comet")

**Perplexity Comet 사례 상세.** Studio Freight가 제작한 Comet 브라우저 랜딩은 PP Editorial New(세리프)를 가변 폭으로 호버 시 확장·재구성시켜 "우주의 팽창"과 반응성을 은유. 타이포가 정적 자산이 아니라 살아있는 재료로 다뤄지는 사례.

**Linear 2025 리디자인 상세.** Inter Variable 단일 사용이지만 `cv01`/`ss03` OpenType 피처를 전역 활성화해 더 기하학적으로 보정. 300(라이트 본문)~590(세미볼드) 사이 폭넓은 웨이트를 쓰되 특히 510(레귤러와 미디엄 사이) 커스텀 웨이트가 시그니처. 72px/64px/48px 디스플레이 사이즈에 -1.584px~-1.056px의 공격적 네거티브 자간을 줘 "설계된 듯한" 압축 헤드라인을 만든다. 배경은 `#0f1011`/`#08090a` 니어블랙, 텍스트 `#f7f8f8`, 액센트는 `#5e6ad2`/`#8b5cf6`(보라 계열이지만 인터랙션 상태에만 절제 사용).

Sources: [Medium — Web Design Trends 2026: Bento Grids](https://medium.com/@aksamark/web-design-trends-2026-why-minimalism-is-evolving-into-bento-grids-16839fd31fb7), [Fireart Studio — 2026 Web Design Trends](https://fireart.studio/blog/the-best-web-design-trends/), [Digital Silk — Kinetic Typography 2026](https://www.digitalsilk.com/web-design/web-trends/kinetic-typography/), [925studios — Linear Design Breakdown](https://www.925studios.co/blog/linear-design-breakdown), [DesignMD — Linear Design Tokens](https://designmd.cc/benchmarks/linear), [The Brand Identity — Studio Freight × Perplexity Comet](https://the-brandidentity.com/project/how-studio-freight-launched-perplexitys-browser-before-it-existed), [Fonts In Use — Comet](https://fontsinuse.com/uses/72596/comet), [AI Chat Daily — AI companies pivot to serif fonts](https://www.aichatdaily.com/ai-analysis/ai-companies-pivot-serif-fonts-look-more-human)

---

## 2. "AI가 만든 티" 패턴 블랙리스트 (근거 포함)

여러 아티클(Developers Digest의 16패턴, 925studios, Superdesign, SmoothUI)이 공통으로 수렴하는 목록이다. **핵심 원리**: 이 모든 패턴이 슬롭으로 읽히는 이유는 못생겨서가 아니라 **"의도적 선택의 부재"를 드러내기 때문** — LLM은 학습 데이터의 통계적 평균을 반환하고, 2019년 이후 웹의 평균은 Tailwind 기본값이었다.

1. **보라→인디고 그라디언트("VibeCode Purple", `#6366F1→#A855F7`)** — 2026년 "가장 시끄러운 AI 신호"로 지목됨. Tailwind가 2019년 `indigo-500`을 기본색으로 출하한 이후 학습 데이터를 장악해 모델이 통계적으로 가장 흔한 선택을 반사적으로 고른 것.
2. **글래스모피즘(간유리 카드) 남용** — 2022년 한때 유행했던 프로스티드 글래스 처리가 이후 LLM의 고정 기본값이 됨. shadcn/ui 미가공 디폴트와 함께 "지문(fingerprint)" 취급됨.
3. **정중앙 히어로 + 3열 균일 기능 카드** — "1만 개의 다른 제품 아무 데나 붙여도 되는" 구조. Tailwind 튜토리얼의 3-column 그리드가 기본 기능 섹션 구조로 학습됨.
4. **아이콘-토핑 카드(둥근 사각 안 아이콘 + 제목 + 두 줄 설명) 반복** — "동일한 카드 처리 6개 나열"이 슬롭의 시각적 서명.
5. **H1 위 배지("New" 알약 등)** — 위치 자체가 하나의 시그니처 패턴이 됨.
6. **카드 상단/좌측 컬러 보더** — "em-dash만큼이나 AI 생성의 신뢰할 수 있는 신호"로 지목.
7. **채도 높은 컬러 글로/박스섀도우** — 큰 사이즈의 네온 글로 효과.
8. **영구 다크모드 + 중간회색 본문 + 올캡 섹션 라벨** — "생성된 다크 테마는 WCAG AA 대비를 상시 실패한다"는 지적까지 동반.
9. **Inter/Roboto 무비판적 기본 선택** — "가장 안전한 답"이라 아무 방향성 없이 선택됐다는 신호. (역설: Inter 자체가 나쁜 게 아니라 "고른 이유가 없는 Inter"가 문제.)
10. **가중치 없는 카피 + 가는 선 아이콘("Build faster. Ship smarter." 류)** — 문법적으로는 맞지만 "그 제품에 대해 아무것도 말하지 않는" 텍스트.
11. **이모지 아이콘 내비게이션/기능 불릿** — 사이드바나 기능 리스트에 이모지를 아이콘 대용으로 씀.
12. **번호 매긴 3단계 시퀀스("1·2·3" 스텝)와 가로 통계 배너 스트립** — 데이터/온보딩을 기계적으로 나열.
13. **스파클(✨) 장식** — 사용자 조사에서 직접 다뤄지진 않았으나 위 패턴군과 동일 계열: "AI 기능입니다"를 시각 장식으로 과잉 표시하는 관습. Shape of AI 등 UX 연구는 AI임을 알리는 것과 "AI스러움을 시각적으로 치장하는 것"을 구분해야 한다고 강조.
14. **가짜/전형적 후기 카드(별점 5개 + 스톡 아바타 + 일반화된 문구)** — "믿을 만한 얼굴"을 스톡으로 대체하려는 시도가 오히려 신뢰를 깎는다는 지적과 같은 계열(§5 종교/비영리 섹션 참조: "스톡 사진은 2초 안에 티가 난다").
15. **로봇 아바타·3D 아이소메트릭 일러스트로 AI를 의인화** — 본 리포지토리 내 선행 라운드(`blessing-craft-2026-08-06/README.md`)에서도 관리자 목업 감사 결과로 명시적으로 금지 처리된 패턴("라벤더 그라디언트 구름, 3D 일러스트, 로봇 아바타, 이모지").

Sources: [Developers Digest — 16 AI Design Slop Patterns](https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it), [925studios — AI Slop Fonts and Gradients](https://www.925studios.co/blog/ai-slop-design-tells), [Superdesign — Why AI Design Looks Generic](https://superdesign.dev/blog/why-ai-design-looks-generic), [SmoothUI — AI Design Slop](https://smoothui.dev/blog/ai-design-slop), [GitHub — avoid-ai-design skill](https://github.com/funboy322/avoid-ai-design)

---

## 3. 세련됨을 만드는 기법 화이트리스트 (실제 사례 포함)

1. **극단적 타이포 스케일 대비 + 네거티브 자간 튜닝** — Linear: 디스플레이 72px에서 -1.584px 자간, 300~590 사이 폭넓은 웨이트 스펙트럼, 특히 510이라는 "이름 없는 중간 웨이트"를 시그니처로 채택. 스케일 대비 자체보다 **자간을 사이즈별로 다르게 튜닝**하는 디테일이 "엔지니어링된 듯한" 느낌을 만든다.
2. **가변 폭 세리프의 호버 인터랙션** — Perplexity Comet(Studio Freight): PP Editorial New가 호버 시 폭이 늘어나는 가변축을 이용해 "정적 텍스트"가 아니라 "반응하는 재료"로 다뤄짐.
3. **크림/오프화이트 배경 + 클래식 세리프 페어링** — 순백을 버리고 인쇄물 질감의 크림 배경에 세리프를 얹어 "에디토리얼하고 격상된" 톤을 만드는 전략. (단, §1의 세리프 남용 경고와 함께 판단할 것.)
4. **동적 베ントー 그리드** — 정적 타일이 아니라 호버 시 슬라이드/비디오 재생으로 콘텐츠 레이어가 열리는 구조. Apple의 기능 그리드에서 출발해 SaaS 표준이 된 뒤, 2026형은 "인터랙션 깊이"로 차별화.
5. **CSS 노이즈/필름 그레인 오버레이** — WebGL 없이 가벼운 SVG 노이즈로 평면에 촉각적 질감을 부여, "디지털 완벽함"을 깨는 아날로그 신호를 준다.
6. **뷰포트 스케일(kinetic) 타이포그래피** — 스크롤에 따라 대형 글자가 압축·확장·굵기 전환. 히어로 이미지 대신 타이포 자체가 브랜드 내러티브를 짊어짐. (단, 모션 민감성 접근성 리스크를 항상 병기해야 한다는 게 같은 아티클의 경고.)
7. **역할별 밀도 차등화(피봇: 누가 보느냐)** — 핀테크 UX 원칙: "핵심 행동을 한 사용자 역할에 명확히 하고, 경쟁사가 숨기는 숫자(수수료·한도·요율)를 보여주고, 역할에 따라 밀도를 다르게 한다 — 재무팀에는 고밀도(Ramp/Brex), 창업자에게는 최소(Mercury)". 이는 순수 "미니멀 vs 정보량" 이분법이 아니라 **독자를 특정하는 것 자체가 세련됨의 원천**이라는 원칙.
8. **투명성으로 신뢰를 쌓는 카피 전략** — Mercury: 자금 보관 방식·보안 기준·파트너 은행 관계를 숨기지 않고 자연스럽게 본문에 통합. "규제 맥락을 감추지 않는다"는 원칙 자체가 디자인 결정.
9. **모노크롬 우선 + 액센트 컬러의 절제된 국소 사용** — Linear의 2025 리디자인은 컬러를 줄이고 흑백 대비 위주로 전환, 보라·인디고 계열 액센트는 인터랙션 상태(호버·포커스)에만 국한. "AI스러움을 만드는 보라"와 "절제된 보라"의 차이는 **면적과 용도**에 있다.
10. **레이아웃 그리드의 비대칭·타이트 정렬** — 2026 트렌드 아티클들이 공통으로 언급하는 "broken grids"(깨진 그리드)와 "invisible architecture"(보이지 않는 격자) — 완벽한 대칭 3열 대신 의도적 비대칭 배치로 "손이 갔다"는 인상을 만든다.
11. **에디토리얼 스토리텔링 구성(잡지식 편집)** — 커스텀 형태의 사진 크롭, 인용구를 독립 조판 요소로 배치, 섹션 간 내러티브 흐름 — 정보 나열이 아니라 "읽는 순서"를 설계.
12. **마이크로 인터랙션에 의미 부여(장식이 아니라 상태 설명)** — 본 리포지토리 선행 라운드가 채택한 원칙: "모든 애니메이션은 위계·서사·피드백·상태전환 중 하나를 설명할 수 있어야 함"(모션 강도 3→6로 올리되 전부 목적 태깅). 이는 "바운스가 모든 호버의 기본값"인 슬롭 패턴(§2 목록에 준하는 SmoothUI 지적)의 정반대.
13. **실제 인물/실제 현장 사진(스톡 금지)** — 신뢰 도메인(교회·비영리) 리서치에서 반복 확인: "방문자는 스톡 사진을 2초 안에 알아본다. 실제 회중·실제 건물·실제 예배 사진이 진짜 신뢰를 만든다."

Sources: [925studios — Linear Design Breakdown](https://www.925studios.co/blog/linear-design-breakdown), [The Brand Identity — Perplexity Comet](https://the-brandidentity.com/project/how-studio-freight-launched-perplexitys-browser-before-it-existed), [Utsubo — Fintech Website Trust Design Patterns](https://www.utsubo.com/blog/fintech-website-trust-design-patterns), [The Masterly — Fintech Design Trends 2026](https://www.themasterly.com/blog/fintech-design-guide), [Fireart Studio — 2026 Web Design Trends](https://fireart.studio/blog/the-best-web-design-trends/), [Envato Elements — Web design trends for 2026](https://elements.envato.com/learn/web-design-trends)

---

## 4. 채팅/대화형 UI 좋은 레퍼런스

갤러리(Mobbin) 자체는 로그인 월 뒤에 있어 스크린샷 원본을 직접 확인하지 못했으나, 목록화된 패턴 요약과 개별 제품 리서치로 아래 5개 사례를 확보했다.

1. **Perplexity (채팅 + 인용)** — 답변을 말풍선이 아니라 전폭 문서 형태로 배치하고, 각주 숫자 대신 발행처명 알약(pill)으로 출처를 표시. **배울 점**: 사용자 발화만 말풍선/우측 정렬로 구분하고 AI 응답은 "문서"로 취급하면 신뢰도 높은 정보 제품처럼 읽힌다. (본 리포지토리 `blessing-craft-2026-08-06/README.md`가 실 CSS 검증까지 마친 원칙: "진지한 정보 제품은 예외 없이 사용자 발화만 말풍선에 넣고 AI 응답은 전폭 문서로 놓는다".)
2. **Glean (엔터프라이즈 검색)** — 검색 계획 카드를 "제목 + N개 완료"로 접어서 보여줌. 출처 카드에 제목과 아이콘을 강제. **배울 점**: 검색 중간 과정을 전부 노출하지 않고 "요약된 영수증" 한 줄로 접으면 장황함 없이 신뢰 신호를 줄 수 있다.
3. **Onyx (오픈소스 Glean 대안)** — 모든 주장을 실제 문서의 특정 문장까지 추적 가능한 인라인 인용으로 연결(permission-aware retrieval + citations). **배울 점**: "인용이 있다"가 아니라 "인용이 원문 몇 번째 문장인지"까지 파고드는 것이 근거 표시의 다음 단계.
4. **Notion AI Enterprise Search** — 워크스페이스·연결앱(Slack/Drive/Jira) 통합 검색 답변에 항상 출처를 인용하는 것을 기본값으로 강제. **배울 점**: "인용을 켤지 끌지"가 아니라 애초에 인용 없는 답변 자체를 허용하지 않는 제품 결정.
5. **일반 챗봇 UI 공통 4원칙(Mobbin 패턴 요약)** — 구조화된 응답 포맷팅(긴 답을 읽기 쉬운 덩어리로 분절), 타이핑 인디케이터, 모호한 질의를 좁히는 퀵리플라이 버튼, 우아한 폴백(제너릭 "이해 못했습니다" 대신 액션 가능한 리커버리 루프 — 소스 인용으로 재확인시키거나 사람 연결). 접근성 기준으로는 고대비 말풍선, 넉넉한 탭 타깃, 키보드 완전 대응, 스크린리더 대응이 반복 강조됨.

Sources: [Mobbin — Chatbot UI Design Examples](https://mobbin.com/explore/web/screens/chat-bot), [blessing-craft-2026-08-06/README.md](file:///Users/woosung/project/agy-project/nexus-core/docs/prototypes/blessing-craft-2026-08-06/README.md)(리포지토리 내부 선행 조사, Perplexity/Glean/Onyx 실 CSS 검증 포함)

---

## 5. 신뢰 도메인(금융·의료·공공·종교) 디자인 사례

1. **Mercury (핀테크/뱅킹)** — "미니멀한 게 우연이 아니라, 회사 운영에 집중해야 할 창업자에게는 그게 정답이기 때문에 미니멀하다"는 명시적 설계 철학. 자금 보관 방식·보안 기준·파트너 은행 관계 같은 규제 정보를 숨기지 않고 카피에 자연스럽게 통합해 "투명성 자체가 신뢰의 비주얼"이 되게 함.
2. **Ramp (핀테크/지출관리)** — 절제된 뉴트럴 컬러 + 넉넉한 여백 + 즉시 이해되는 절감액 숫자로 "규모·신뢰·현대적 효율성"을 첫 화면에서 동시에 전달. Mercury와 달리 재무팀 대상이라 정보 밀도를 의도적으로 높게 유지 — "역할별 밀도 차등화" 원칙의 실사례.
3. **의료 AI 제품 일반(다수 사례 종합)** — "전형적 헬스케어 SaaS보다 의도적으로 더 정교한" 컨피던트 세리프 헤드라인 + 에디토리얼급 타이포그래피, 팔레트는 딥 플럼·잉크·크림 같은 절제된 톤. AI 사용을 숨기지 않고 첫 화면에서 명확히 알리는 카피와 일관된 "AI 아이코노그래피"가 신뢰 형성의 전제 조건으로 지목됨(Stanford Persuasive Tech Lab 인용: 사용자의 75%가 웹사이트 디자인만으로 기업 신뢰도를 판단).
4. **교회/신앙 도메인(다수 사례 종합, 특정 제품명은 갤러리에서 확보 못함)** — 일부 교회 사이트는 고대비 흑백 + 세리프 헤드라인으로 설교 콘텐츠를 "잡지 스프레드"처럼 편집형 시리즈로 배치. 공통 원칙: 스톡 사진 대신 실제 회중/건물 사진(방문자는 스톡을 2초 안에 알아챈다는 지적), 암호화 결제·자동 백업 등 보안 신호를 명시적으로 언급해 신뢰를 쌓음. → 종교 도메인에서 "AI가 정보를 준다"는 사실 자체를 숨기지 않되, 장식적 AI 신호(로봇·스파클)는 완전히 배제하는 것이 의료/금융과 공유되는 패턴.

Sources: [The Masterly — Fintech Design Trends 2026 (Mercury)](https://www.themasterly.com/blog/fintech-design-guide), [Utsubo — Fintech Website Trust Design Patterns (Ramp)](https://www.utsubo.com/blog/fintech-website-trust-design-patterns), [Webstacks — 18 Best Healthcare Website Design Examples](https://www.webstacks.com/blog/healthcare-website-design), [TELUS Digital — Designing Trustworthy AI Products for Healthcare](https://www.telusdigital.com/insights/data-and-ai/article/how-to-design-trustworthy-ai-products-for-healthcare), [Epic Life Creative — Church Web Design Trends 2025](https://www.epiclifecreative.com/web-design-trends-for-churches-and-ministries-in-2025/)

---

## 종합: 이번 프로젝트에 추천하는 미학 방향 후보 3가지

프로젝트 성격(가정 신앙 공동체용 정보/상담 챗봇, 신뢰가 핵심, 브랜드 보라 `#603B94` 보유, `blessing-craft-2026-08-06` 라운드에서 이미 "그라디언트 0·보라 절제·모션은 목적 태깅"까지 규칙화됨)을 전제로, 리서치에서 확인된 화이트리스트 기법을 조합해 세 방향을 제안한다.

### 후보 1 — "차분한 에디토리얼(Calm Editorial)"
- **특징**: 크림/오프화이트 배경 + 절제된 세리프 헤드라인(단, 세리프는 인용문·표제 등 국소 사용에 한정해 §1의 "tasteslop" 경고를 피함) + 잡지식 섹션 구성(비대칭 배치, 인용구 독립 조판). 컬러는 모노크롬 우선, 브랜드 보라는 밑선·텍스트 컬러 정도의 납작한 국소 액센트로만.
- **참고 사례**: Perplexity의 PP Editorial New 세리프 채용 전략(단 "사람을 위한 디자인"이라는 명시적 근거를 함께 채택할 것), 크림 배경+세리프 조합이 보고된 다수의 AI 스타트업 랜딩 사례, 의료 도메인의 "딥 플럼·잉크·크림" 팔레트.
- **적합한 이유**: 신앙/가정 공동체라는 도메인에 세리프의 "인쇄물=권위" 연상이 자연스럽게 맞고, 그라디언트·글로 없이도 격상된 느낌을 낼 수 있어 기존 규칙(그라디언트 0)과 충돌하지 않는다.

### 후보 2 — "절제된 시스템(Restrained System, Linear 계열)"
- **특징**: 모노크롬 다크/라이트 베이스 + 극단적 웨이트·자간 튜닝(사이즈별 네거티브 자간 스케일)으로 위계를 만들고, 액센트 컬러(브랜드 보라)는 인터랙션 상태에만 국한. 세리프 없이 산세리프 단독으로도 "엔지니어링된 정교함"을 낸다.
- **참고 사례**: Linear 2025 리디자인(Inter Variable, 510 커스텀 웨이트, -1.584px 자간, `#0f1011` 니어블랙 + `#5e6ad2`/`#8b5cf6` 국소 액센트).
- **적합한 이유**: 관리자/실무자용 화면처럼 "정보 밀도가 높고 반복 사용되는" 면에 적합 — 신뢰는 장식이 아니라 정확한 정렬과 절제에서 나온다는 원칙을 가장 순수하게 구현.

### 후보 3 — "투명한 근거(Transparent Grounding)"
- **특징**: 시각 스타일보다 **정보 구조**가 미학이 되는 방향. Perplexity/Glean/Onyx식 인용 알약, 검색 과정을 "근거 N건·검색 X초" 한 줄로 접는 영수증 UI, "이 창구가 답하지 않는 것"을 명시하는 섹션, AI라는 사실을 숨기지 않되 장식하지도 않는 절제된 라벨링(C2PA 2.0의 "신호등처럼 색으로 등급 매기지 말라" 권고 준수).
- **참고 사례**: Perplexity(발행처명 알약), Glean("제목+N개 완료" 접힘 카드), Onyx(문장 단위 추적 인용), Mercury(규제 정보를 숨기지 않는 카피 전략).
- **적합한 이유**: 금융/의료/종교처럼 "신뢰가 상품 그 자체"인 도메인에서는 비주얼 트렌드보다 근거의 투명성이 더 강한 세련됨의 신호라는 것이 §5 리서치의 공통 결론. 이미 본 리포지토리가 이 방향으로 실 CSS 검증까지 마친 선례(`blessing-craft-2026-08-06`)가 있어 확장 리스크가 가장 낮다.

**추천 우선순위**: 후보 3(정보 구조)을 뼈대로 삼고, 화면 성격에 따라 첫 진입/설득 화면은 후보 1(에디토리얼)을, 반복 사용되는 실무 화면은 후보 2(절제된 시스템)를 국소 적용하는 하이브리드가 리서치 근거상 가장 안전하다 — 셋 모두 §2 블랙리스트(그라디언트·글래스모피즘·이모지·3카드·가짜 후기)를 원천적으로 배제하는 방향이기 때문에 서로 충돌하지 않는다.
