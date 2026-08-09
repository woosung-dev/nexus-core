# 상용 RAG(문서 기반 Q&A) 제품 랜딩 페이지 조사

조사일: 2026-08-06
방법: WebFetch(1차) → Jina Reader(r.jina.ai) → Playwright 실브라우저(로그인월/쿠키배너로 막힌 곳) 순으로 시도. 접속 실패한 곳은 실패 사유와 2차 자료를 명시.

---

## 히어로 헤드라인 원문 수집표

| 서비스 | 헤드라인 원문 | 무엇을 파는가 |
|---|---|---|
| **Gemini Notebook**(구 NotebookLM) | "Understand Anything" / 한국 로캘: "무엇이든 이해할 수 있습니다" | 신뢰 가능한 근거에 "그라운딩"된 사고 파트너 — 이해력 자체를 판다 |
| **Perplexity**(제품 홈, perplexity.ai) | "무엇을 알고 싶으신가요?"(What do you want to know?) | 마케팅 카피가 아니라 검색창 placeholder가 곧 헤드라인 — 제품=랜딩 |
| **Perplexity Hub**(마케팅, /hub) | "AI for the curious" | 브랜드 미션 — 정확성(인용)·멀티모델 오케스트레이션 |
| **ChatPDF** | "Best-in-class AI tools for students and researchers" | 학생·연구자용 PDF Q&A, 속도와 무료를 판다 |
| **Humata** | "AI meets your knowledge base" | 조직 지식베이스 전체를 대상으로 한 질의응답, 신뢰를 판다 |
| **Glean** | "Work AI that understands your company" | 기업 전체 업무 AI(시스템·컨텍스트 연결), 생산성 ROI를 판다 |
| **Chatbase** | "Conversational agents for customer experience" | 고객경험 자동화 에이전트, 매출 증대를 판다 |
| **CustomGPT.ai** | "Every AI answers questions. Create one you trust." | 경쟁사 대비 "신뢰(정확한 인용)"를 정면 차별점으로 판다 |
| **뤼튼**(wrtn.ai) | 없음 — 홈이 곧 로그인 전 제품 UI | 별도 마케팅 헤드라인 자체가 존재하지 않음 |
| **알리**(Allganize, allganize.ai) | "Enterprise AI · Coworker + Works" | 파일럿→프로덕션 전환, 문서 근거 인용을 판다 |
| **CLOVA X** | 확인 불가(도메인 소멸) | — |
| Onyx(보너스) | "Give your team superpowers." | 오픈소스 사내 AI 챗(문서+앱+사람 연결) |
| Dify(보너스) | "The Platform for Production-Ready Agentic Workflows." | RAG/에이전트 워크플로 빌더, 개발자 인프라를 판다 |
| SiteGPT(보너스) | "Make AI your expert customer service agent" | 웹사이트 콘텐츠 기반 고객지원 챗봇 |

---

## 서비스별 관찰

### 1. Gemini Notebook (구 NotebookLM) — notebooklm.google

**중요 발견**: 2026년 7월부로 NotebookLM이 **Gemini Notebook으로 리브랜딩**됨. FAQ에 "Yes. NotebookLM is now Gemini Notebook as of July 2026... all of your existing notebooks remain fully accessible"라고 명시. (출처: https://notebooklm.google, Playwright 스크린샷으로 실접속 확인 완료)

- **히어로**: "Understand Anything" 한 줄 + 서브카피 "Your research and thinking partner, grounded in the information you trust, built with the latest Gemini models." CTA는 "Try Gemini Notebook" 단일 블랙 버튼(보조로 "Get the app"). 히어로에 스크린샷 없음 — 대신 굵은 헤드라인 중 "무엇이든/Anything"만 파랑→초록 그라디언트로 강조, 나머지는 순수 검정. 배경은 순백, 여백이 매우 넓음. Google Sans 계열 산세리프.
- **인용 UI(직접 스크린샷 확인)**: 히어로 다음 3개 기능 카드 중 세 번째가 정확히 "See the source, not just the answer / 답변만이 아니라 소스도 확인하세요"다. 스크린샷은 **다크 UI 카드** 안에 원문 텍스트가 하이라이트되고, 인용 번호 칩 "①"이 인라인으로 붙어 있으며, 손글씨 스티커 말풍선 "CHECKING SOURCES"(보라색)가 그 위에 얹혀 있다. 다른 카드에도 "INSTANT STUDY GUIDE!"(핑크), "CREATE AUDIO STUDY GUIDES"(노랑) 같은 손글씨 스티커가 반복 등장 — **정적 스크린샷이 아니라 "지금 근거를 확인 중"이라는 동작감을 스티커로 연출**하는 게 특징.
- **신뢰 표현**: FAQ에서 "reduced hallucinations", "source-grounded", "Direct control over sources" 등 4개 항목으로 신뢰 근거를 논리적으로 나열(마케팅 카피가 아니라 FAQ 형식).
- **섹션 순서**: 히어로 → 기능 3분할(업로드/인사이트/인용, 각각 mp4 데모) → 사용 사례 3종(학습/발표/아이디어) → 언론·인플루언서 인용 캐러셀(HardFork, CNBC, WSJ, The Verge, Karpathy — **동일 인용문이 페이지 소스에 4~6회씩 중복** 등장, 캐러셀 루프 소스가 그대로 노출된 것으로 추정) → 프라이버시 섹션 → FAQ(아코디언, 매우 김) → 푸터.
- **비주얼**: 라이트 배경 + 다크 UI 목업 카드 대비, 네온 그라디언트(초록/보라/파랑) 글로우, 손글씨 스티커 주석 — Google 특유의 "쾌활한 주석" 스타일.

출처: https://notebooklm.google (Playwright 실접속 + 스크린샷, Jina Reader 텍스트 병용)

---

### 2. Perplexity — perplexity.ai / perplexity.ai/hub

perplexity.ai 루트 도메인은 **마케팅 페이지가 아니라 로그인 전 제품 UI 그 자체**임을 실접속으로 확인. WebFetch는 403(쿠키 배너/봇 차단)이라 Playwright로 우회.

- **제품 홈(perplexity.ai)**: 헤드라인이라 부를 게 없고 검색창 placeholder "무엇을 알고 싶으신가요?"가 사실상 헤드라인. 좌측 사이드바(신규/Computer/아티팩트/프로젝트/세션)에 검색창 하나. 페이지 진입 직후 "로그인하거나 무료로 가입하세요" 모달이 자동으로 뜸(Google/Apple/이메일/SSO). 배경은 순검정, 화이트 텍스트, 별도 스크린샷·기능소개·후기 섹션 전혀 없음.
- **마케팅 페이지(perplexity.ai/hub)**: 여기가 진짜 랜딩. 헤드라인 "AI for the curious", 서브카피 "답을 찾으세요. 아이디어를 만드세요. 세상을 바꾸세요." 히어로 배경은 **야간 정원 사진**(반딧불처럼 빛나는 흰 꽃, 인물 실루엣이 폰을 보는 시네마틱 컷) 위에 대형 세리프+산세리프 혼합 타이포("AI" 산세리프, "for" 이탤릭 세리프, "the curious" 산세리프) — 실스크린샷도 3D도 아닌 **연출된 인물 사진**을 쓰는 게 특이점. 검색창이 히어로에 바로 삽입되어 있고 하단에 "Perplexity · OpenAI · Gemini · Nvidia · Claude" 로고 티커와 "최고의 모델들, 함께라면 더욱 강력하게" 카피.
- **인용/신뢰 세일즈**: "우리가 하는 일" 4카드 중 첫 번째가 "정확한 AI — 인용으로 뒷받침되는 정확한 답변, 더 깊이 있는 심층 리서치, 더 적은 환각". FAQ에도 "모든 답변은 실시간 웹 출처에 기반하며 본문 내 인용이 포함되어 있어, 불투명하지 않고 검증할 수 있습니다"라고 직접 명시. 다만 인용 UI를 **스크린샷으로 보여주진 않음** — 문구로만 주장.
- **섹션 순서**: 히어로(검색창) → 모델 로고 티커 → 4가지 핵심가치 카드 → 4개 제품 카드(답변엔진/Computer/Comet브라우저/API) → "첫 질문에서 완성된 결과물까지" 워크플로 탭(리서치/분석/빌드/자동화, 실제 금융분석·마케팅 대시보드 예시 스크린샷 다수) → 개인/팀/개발자 3분할 CTA → FAQ 아코디언 → 푸터.
- **비주얼**: 다크 시네마틱 사진 + 세리프·산세리프 믹스 타이포가 브랜드 시그니처. 워크플로 섹션은 실제 데이터 대시보드 스크린샷(투자 논지, 승률 차트, 광고 채널 기여도 등)을 촘촘히 배치 — 기능이 아니라 "결과물"을 보여주는 방식.

출처: https://www.perplexity.ai , https://www.perplexity.ai/hub (둘 다 Playwright 실접속 + 스크린샷 확인. WebFetch는 403)

---

### 3. ChatPDF — chatpdf.com

- **히어로**: "Best-in-class AI tools for students and researchers" / 서브카피 "Your PDF AI - like ChatGPT but for PDFs. Summarize and answer questions for free." CTA "Sign up"(반복), 파일 업로드 드래그앤드롭 UI가 히어로에 바로 삽입(실스크린샷은 아니고 파일 포맷 아이콘 일러스트).
- **인용/신뢰**: "Cited Sources" 섹션에 "Built-in citations anchor responses to PDF references. No more page-by-page searching." 대학 로고(Harvard/Cambridge/Oxford/Stanford), "10M+ Researchers", "1,000,000+ Q's answered every day", a16z "Top 50 Gen AI apps of 2024" 배지, 4.9점 별점.
- **섹션 순서**: 히어로 → 툴 내비 → 업로드 재반복 → 신뢰요소(대학로고·통계·트위터 후기) → 사용사례 3종 → "Wall of Love" 후기 → 기능 4가지 → FAQ → 푸터.
- **비주얼**: 라이트 배경, 실스크린샷+벡터 일러스트 혼합, 모던 산세리프, 넉넉한 여백.

출처: https://www.chatpdf.com (WebFetch 성공)

---

### 4. Humata — humata.ai

- **히어로**: "Humata" + "AI meets your knowledge base" / 서브 "Ask questions across all of your files". CTA "Try for free" 1개(+로그인/가입). 히어로 스크린샷 4장 순차 삽입(home-slide-01~04, 상세 CSS는 확인 불가).
- **인용/신뢰**: "Get answers you can trust", 기능명 자체가 "Highlights citations — Build trust with cited links into your source files". "Trusted by top investors" + 실명 인용(Phil Fersht, HFS Research CEO).
- **섹션 순서**: 히어로 → 투자자 신뢰 로고 → 기능 4가지(무제한 파일/인용 하이라이트/무제한 질문/웹임베드) → 보안 → 가격 → FAQ → 후기 → 최종 CTA → 푸터.
- **비주얼**: 모바일/태블릿 목업 프레임 사용 확인, 구체적 컬러·폰트는 CSS 미포함으로 확인 불가.

출처: https://www.humata.ai (WebFetch 성공, 단 시각 디테일은 HTML만 반환되어 제한적)

---

### 5. Glean — glean.com

- **히어로**: "Work AI that understands your company" / 서브 "Glean connects knowledge, systems, and context so AI can actually work." CTA "Get a Demo" + "See how it works"(앵커). 히어로에 스크린샷·데모 없이 **추상 배경 그래픽**(Hero-Glean-Bg.webp)만.
- **인용/신뢰**: 여기가 조사 대상 중 유일하게 **인용 UI를 전혀 세일즈 포인트로 안 쓰는** 사례. 대신 정량 ROI("110 hours saved per user/year", "93% enterprise adoption in < 2 years", "12,442,032,540 average token savings YTD")와 컴플라이언스 배지 6종(ISO 42001/HIPAA/SOC2 Type II/GDPR 등), 22개 기업 로고, 고객 인용 4건으로 신뢰를 구축.
- **섹션 순서**: 히어로 → 통합가능 플랫폼 로고 → 고객사 로고 → 이벤트 프로모(GLEANGO2026) → 토큰절감 통계 → 가치제안 3가지 → 보안기능 → 컴플라이언스 배지 → 성과지표 → 고객 사례연구 5개 → 인용 캐러셀 → 플랫폼 기능 4가지 → Work AI Institute 자료 → 블로그.
- **비주얼**: 다크 톤(검정/차콜) + 흰 텍스트, 그라디언트 강조, 스크린샷 없이 추상 배경그래픽·기업로고 위주. 섹션 12개 이상으로 매우 긺 — 엔터프라이즈 세일즈 자료에 가까움.

출처: https://www.glean.com (WebFetch 성공)

---

### 6. Chatbase — chatbase.co

- **히어로**: "Conversational agents for customer experience" / 서브 "AI agents that meet customers at every stage of their journey, across chat, email, and voice, to resolve issues end to end and increase revenue." CTA 2개: "Start free trial" / "Get a demo". 히어로도 추상 배경(hero-bg.webp)뿐, 동작 스크린샷 없음.
- **인용/신뢰**: 인용 UI 언급 없음. 대신 "4.8" 별점, "Trusted by over 10,000 brands", G2 어워드 3종, OpenAI Head of Startups 등 실명 인용 다수, 유튜브 고객사례 영상.
- **섹션 순서**: 히어로 → 고객사 로고 → 에이전트 유형 3종 → OpenAI 임원 추천사 → 에이전트 라이프사이클(Build→Test→Deploy→Optimize) → 제품 스위트 → 고객인용 캐러셀 → 배포채널(Chat/Email/Voice) → 동영상 사례 3개 → G2 배지 → 보안(GDPR/SOC2/HIPAA) → 산업별 솔루션 → 최종CTA.
- **비주얼**: 다크(black/charcoal) + grain/noise 텍스처, 3D 지오메트릭 큐브 일러스트와 실스크린샷 혼합, 산세리프.

출처: https://www.chatbase.co (WebFetch 성공)

---

### 7. CustomGPT.ai — customgpt.ai

- **히어로**: 메인 "Every AI answers questions. Create one you trust." + 서브 "Create AI that gets it right" + 태그라인 "Go live in 15 minutes with custom AI that accurately cites your information." CTA 2개: "Try for free"(7일 트라이얼) / "Chat with our AI". 비디오 데모 임베드 확인.
- **인용/신뢰**: 조사 대상 중 신뢰 카피가 가장 공격적. "third-party verified #1 for anti-hallucination technology, beating out major players like OpenAI and Google", "handle 93% of support and research questions", "Trusted by 10,000+ organizations"(UN, Adobe, Dropbox 등 로고), SOC-2/GDPR, "Awarded Top 7 emerging leader"(GAI Insights).
- **섹션 순서**: 히어로 → 신뢰로고 → 3단계 론칭(연결→커스터마이징→배포) → 데이터연결(1,400+ 파일형식) → LLM 선택(OpenAI/Anthropic 등) → 배포위치 → 선택이유(신뢰/보안/정확성) → 어워드 → 보안 → 정확성 벤치마크 → 고객증언 3개 → 가격 3단 → FAQ 12개 → 최종CTA.
- **비주얼**: 비디오 4개, 로고 SVG 다수, 색상/폰트는 확인 불가.

출처: https://customgpt.ai (WebFetch 성공)

---

### 8. 뤼튼(wrtn.ai) — 마케팅 랜딩 부재

wrtn.ai에 접속하면 **마케팅 카피 없이 로그인 전 제품 UI가 그대로 나온다**. "로그인 후 파일 또는 사진을 첨부해 주세요"라는 안내문과 "요청 유형(기본/블로그/자기소개서)" 프리셋 카드, GPT-5 모델 표시, 상단 내비(홈/도구/혜택/저장됨), CTA는 "무료로 회원가입"/"로그인"뿐. 헤드라인·서브카피·후기·로고월·가격 섹션 등 통상적 랜딩 구성요소가 전혀 없음 — **제품과 랜딩을 분리하지 않은 사례**.

출처: https://wrtn.ai (WebFetch는 402 에러, Jina Reader로 재시도해 본문 확인)

---

### 9. 클로바X(CLOVA X) — 접속 실패, 도메인 자체가 소멸

`clova-x.naver.com`은 **DNS 조회 자체가 실패**(`NXDOMAIN`, `nslookup` 직접 확인, 2026-08-06 기준). Jina Reader도 "Domain 'clova-x.naver.com' could not be resolved" 오류. Wayback Machine의 최근 스냅샷(2025-08-06)을 시도했으나 아카이브 서버 접속이 이 환경에서 차단되어 있어 원문 재현에는 실패했고, 대체로 시도한 `id_` 원본 모드 응답도 이 네트워크 환경의 프록시가 삼킨 것으로 보이는 무관한 JSON을 반환해 신뢰할 수 없는 것으로 판단, 폐기함.

**2차 자료(WebSearch)**: CLOVA X는 2023년 출시된 네이버의 대화형 AI 서비스로 "한국형 ChatGPT"로 소개되었고, 출시 당시 베타·대기자 신청제였다는 설명이 검색 스니펫에서 확인됨(출처: https://namu.wiki/w/네이버 클로바 등, 직접 열람하지 않고 검색 스니펫만 인용).

별도로 `clova.ai`(HyperCLOVA X 기업용 B2B 페이지, 200 OK로 실접속 확인)는 CLOVA X와는 다른 제품 라인으로, 헤드라인 "HyperCLOVA X는 네이버가 자체 개발한 초거대 언어모델로 복잡한 비즈니스 문제를 해결합니다"에 "HyperCLOVA X 자세히보기"/"테크니컬 리포트 바로가기" CTA를 쓰는 것을 확인했으나, 이는 컨슈머 챗봇 CLOVA X의 대체 자료로 보기 어려워 표에서 "확인 불가"로 처리함.

출처: nslookup 직접 실행, https://r.jina.ai (에러 응답), https://clova.ai (WebFetch 성공, 참고용)

---

### 10. 알리(Allganize) — allganize.ai

- **히어로**: "Enterprise AI · Coworker + Works" / 서브 "Enterprise AI you can *actually trust* to do the work. Bridge the gap from pilot to production..." CTA 3개: "Request a Demo"(2회) + "See a 2-min demo". 실제 제품 스크린샷 2장(사용분석 대시보드+Coworker Concierge 챗, Proposal Studio+Video-to-Manual 앱).
- **인용/신뢰**: 조사 대상 중 인용 UI를 **가장 구체적으로** 문구화. "Grounded in the original layout — 원본 문서에서 인용 구간을 직접 강조", 정확한 위치 표기 예시 "p.4 § 2.3 · layout preserved", "every output traces back to the source document". "300+ Enterprises in production", "120M Documents handled".
- **섹션 순서**: 히어로 → 고객로고+인증배지(SOC2/HIPAA/ISO27001) → 고객 인용문 → "The Problem" → "Why Allganize" 4가지 차별점 → 제품군(Coworker/Works) → 템플릿 갤러리 → 기술스택 4레이어 → 배포옵션 → FAQ → 푸터.
- **비주얼**: 실제 제품 스크린샷 위주(일러스트 미사용), 넓은 여백.

출처: https://www.allganize.ai (WebFetch 성공)

---

### 11. 보너스 — Onyx / Dify / SiteGPT

**Onyx(onyx.app)**: 헤드라인 "Give your team superpowers." / 서브 "Onyx is the open-source AI chat connected to your docs, apps, and people." 신뢰 표현이 독특 — 경쟁제품 대비 **벤치마크 승률**을 직접 수치화("ChatGPT 대비 64%, Claude 대비 68.1%, Notion AI 대비 76%"), GitHub 스타 2만 개, "1,000+ 글로벌 상위 팀 신뢰". 섹션: 히어로 → Deep Research → 플랫폼 기능 → 벤치마크 → 커넥터 → 오픈소스 강점 → 개발자 기능 → 부서별 유스케이스 → 고객사례(Ramp, 30x ROI) → 엔터프라이즈. 출처: https://onyx.app (WebFetch 성공)

**Dify(dify.ai)**: 헤드라인 "The Platform for Production-Ready Agentic Workflows." 서브에 "RAG pipelines"라는 기술 용어를 그대로 노출. CTA "Get Started"/"Contact Sales". 신뢰는 고객로고(Maersk, Adobe, Google, PayPal 등)+인용 3건. RAG 관련 직접적 신뢰 UI는 없고 "Knowledge Pipeline" 섹션명만 확인. 3D 조각상 스타일 추상 렌더링이 특징적. 출처: https://dify.ai (WebFetch 성공)

**SiteGPT(sitegpt.ai)**: 헤드라인 "Make AI your expert customer service agent" / 서브 "It's like having ChatGPT specifically for your product." 신뢰는 로고 5개+실명 후기(CBS Bahamas)+SOC2/GDPR/HIPAA 배지. 인용 UI 언급 없음, "Before/After 비교" 섹션이 특이점. 출처: https://sitegpt.ai (WebFetch 성공)

---

## 크로스 서비스 관찰 — 인용/신뢰를 파는 3가지 층위

1. **문구만으로 주장**(Perplexity, ChatPDF, Humata, Chatbase, Dify, SiteGPT): "인용이 있다", "출처가 명시된다"는 카피는 쓰지만 실제 인용 UI 스크린샷은 히어로/신뢰 섹션에 노출하지 않음.
2. **UI를 실제로 보여줌**(Gemini Notebook 유일): 인용 번호 칩이 텍스트에 인라인으로 붙은 스크린샷을 "See the source, not just the answer" 섹션에 직접 배치, 손글씨 스티커로 "지금 검증 중"이라는 동작감까지 연출.
3. **위치 단위로 구체화**(Allganize 유일): "p.4 § 2.3" 같은 조항 단위 표기로 "출처 있음"을 넘어 "정확히 어디"까지 카피에 박음.
4. **인용을 아예 안 쓰고 ROI/컴플라이언스로 대체**(Glean): 엔터프라이즈 구매자에게는 "정확한 인용"보다 "몇 시간 절약했나/보안인증 있나"가 더 강한 신뢰 신호라고 판단한 것으로 보임.

---

## 문서기반 멀티봇 챗봇 랜딩에 훔쳐올 것 (7개, 근거 포함)

1. **인용을 "동작 중"으로 보여주기** — Gemini Notebook의 인라인 인용칩 + "CHECKING SOURCES" 스티커처럼, "근거 확인 중" 상태를 시각화하면 "정확합니다"라는 카피보다 훨씬 설득력 있다. 근거: notebooklm.google 히어로 3번째 카드가 페이지에서 가장 구체적인 신뢰 증거였음.
2. **헤드라인 동사에 "신뢰"를 직접 박기** — CustomGPT.ai "Create one you trust", Humata "AI meets your knowledge base"처럼 "정확성/신뢰"를 형용사가 아니라 헤드라인의 핵심 동사·명사로 삼는 카피 전략.
3. **인용을 위치 단위로 구체화** — Allganize의 "p.4 § 2.3 · layout preserved" 패턴은 규정집·행정문서 기반 챗봇(우리 도메인과 정확히 일치)에 그대로 적용 가능. "출처 있음"보다 "몇 페이지 몇 조항"이 신뢰를 만든다.
4. **히어로 직후 3~4카드로 "우리가 하는 일" 압축** — Perplexity Hub의 4-value-prop 그리드(정확한 AI/멀티모델/웹우선/API)처럼 스크롤 1~2번 안에 제품 이해가 끝나야 한다.
5. **정량 지표로 사회적 증거 굳히기** — ChatPDF "1,000,000+ Q's answered every day", Humata·CustomGPT의 "10,000+ orgs" 같은 숫자는 정성적 카피보다 훨씬 빠르게 신뢰를 형성한다.
6. **보안/컴플라이언스 배지 나열(Glean)** — 가정·개인정보를 다루는 문서기반 챗봇이라면 인용 신뢰 못지않게 "이 정보가 안전하게 다뤄지는가"가 중요한 세일즈 포인트다. SOC2/GDPR류가 없다면 우리 도메인에 맞는 대체 신뢰 신호(운영주체 명시, 데이터 미학습 정책 등)를 명시적으로 배치.
7. **경쟁·기존 대비 개선치를 벤치마크 카드로** — Onyx의 "ChatGPT 대비 64% 승률" 식 수치화는 "이전 방식보다 얼마나 나아졌나"를 궁금해하는 방문자에게 직접 답을 준다.

## 하지 말 것 (7개, 근거 포함)

1. **스크린샷 없는 추상 배경 히어로(Glean, Chatbase)** — 문서기반 Q&A는 "실제로 어떻게 답하는지"가 핵심 차별점인데, 이를 보여주지 않으면 신뢰 형성의 최대 기회를 스스로 버리는 것. 특히 처음 접하는 사용자층(가정/신앙 상담)에게는 추상 그래픽만으로는 "이게 뭐 하는 서비스인지" 전달이 안 됨.
2. **설명 없이 제품 UI를 그대로 노출(Perplexity 홈, 뤼튼)** — 로그인 모달·빈 검색창만 던지는 전략은 이미 브랜드 인지도가 높은 제품에서만 통한다. 신규 방문자가 대부분인 우리 서비스에는 부적합.
3. **RAG·파이프라인 같은 기술 용어를 그대로 노출(Dify)** — "Agentic Workflows", "RAG pipelines"는 개발자 대상 카피다. 최종 사용자(비개발자, 특히 부모 세대)에게는 거리감만 준다.
4. **동일 인용문/캐러셀 소스를 페이지에 그대로 중복 노출(Gemini Notebook)** — HardFork 인용이 소스 코드에 4~6번 반복되는 건 캐러셀 구현 실수가 그대로 드러난 사례. 콘텐츠 빈곤이나 구현 미숙으로 비칠 수 있어 QA에서 반드시 체크해야 할 항목.
5. **제품과 마케팅 랜딩을 분리하지 않기(뤼튼)** — 홈페이지가 곧 로그인 전 제품이면 신규 방문자에게 "무엇을 파는지"를 설명할 자리가 없다. 랜딩과 제품 진입점을 반드시 분리.
6. **자체 마케팅 자산의 생명주기 방치(CLOVA X)** — clova-x.naver.com이 DNS에서 완전히 소멸한 것은 브랜드 자산 관리 실패의 극단적 사례. 멀티봇 서비스가 확장/개편될 때도 기존 랜딩 URL·브랜드 자산을 폐기하지 않고 리다이렉트라도 남기는 최소한의 관리가 필요함을 반면교사로 삼을 것.
7. **검증되지 않은 공격적 비교 우위 주장(CustomGPT.ai "beating out OpenAI and Google")** — 출처가 불분명한 "3자 검증 1위" 문구는 신뢰가 생명인 종교/가정 상담 도메인에서는 과장 광고로 읽혀 역풍을 부를 위험이 크다. 차라리 구체적 수치(인용 정확도 %, 응답 시간)로 대체할 것.

---

## 접속 실패 로그

| 대상 | 1차 시도 | 결과 | 우회 | 최종 상태 |
|---|---|---|---|---|
| notebooklm.google | WebFetch | 제목만 반환(본문 누락) | Jina Reader → Playwright 재접속 | 성공 |
| perplexity.ai | WebFetch | 403 Forbidden | Playwright 실브라우저 | 성공(단, 마케팅 랜딩은 /hub) |
| wrtn.ai | WebFetch | 402 Payment Required | Jina Reader | 성공(단, 마케팅 헤드라인 자체가 없음을 확인) |
| clova-x.naver.com | WebFetch | fetch 불가 | Jina Reader → nslookup → Wayback Machine | 전부 실패, 도메인 NXDOMAIN 확인으로 최종 결론 |
