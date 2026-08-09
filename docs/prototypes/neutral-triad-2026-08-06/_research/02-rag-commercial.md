# 상용 RAG/문서기반 챗봇 제품의 판매·카피 전략 조사

- 조사일: 2026-08-06
- 목적: neutral-triad 라운드(중립 셸 + N-가변 봇 로스터, `_brief.md`)를 위한 판매 언어 벤치마킹.
  **카피 톤(B2C 친근형 vs B2B 신뢰형) · 네이밍 패턴 · 프라이싱 언어 · 멀티봇 로스터 표현** 4개 축에 집중했다.
- 방법: WebFetch(1차) → Jina Reader(r.jina.ai, 2차) → WebSearch(3차 보완, 특히 실시간 가격처럼 자주 바뀌는 정보) 순.
  1차 소스 접근에 실패한 항목은 본문에 "미확인" 또는 "서드파티 소스"로 명시하고 지어내지 않았다.
- **중복 금지 준수**: 히어로 헤드라인 원문 수집표는 `../blessing-unbound-2026-08-06/_research/02-rag-product-landings.md`,
  인용 UX 패턴표는 `../blessing-reboot-2026-08-06/_research/03-rag-citation-ux.md`에 이미 있다. 이 문서는 그 둘이
  다루지 않은 **가격·이름·로스터·톤** 언어만 다룬다(신규 제품 6종 추가: AskYourPDF, Upstage AI Space, Allganize Alli
  SaaS, 채널톡 ALF, 뤼튼 스튜디오, Dust).

---

## 1. 카피 톤 스펙트럼 — B2C 친근형 vs B2B 신뢰형

같은 "문서 근거 답변"을 팔아도 문장의 인칭·동사·수사가 극명히 갈린다. 아래는 실제 채집 문장이다.

### 1-1. B2C 친근형 — "너의 도구", 구어체, 즉시성

| 제품 | 원문 | 관찰 |
|---|---|---|
| ChatPDF | "Your PDF AI - like ChatGPT but for PDFs. Summarize and answer questions for free." | 이미 유명한 제품(ChatGPT)에 빗대 설명 비용을 0으로 만듦 |
| AskYourPDF | "Choose the plan that fits your needs and start engaging with your documents like never before" | "engage"라는 관계적 동사, "like never before"식 과장 수사 |
| 채널톡 ALF | "헷갈리는 내용이 있다면 ALF를 불러 물어보세요" / "`@ALF`를 불러 메시지 정리, 공감 표현, 정보 검색 등 간단한 요청을 맡기고 더 중요한 업무에 집중해 보세요" | 챗봇을 2인칭으로 "부르는" 대상으로 문장을 구성(아래 2장 참조) |
| 채널톡 ALF | "24시간 365일 지치지 않는 어시스턴트" / "신입 CS 매니저의 업무를 도와주는 멘토 역할" | 사람 역할(신입사원/멘토)에 직접 비유 — B2B 제품인데도 톤은 친근형에 가까움 |
| 뤼튼 | "매일 쓰는 AI, 뤼튼 고객센터 입니다" / "무엇을 도와드릴까요?" | 마케팅 카피가 아니라 자사 고객센터 봇의 인사말 — 제품 자체가 곧 발화자 |
| 뤼튼 스튜디오 | "코딩 없이 10분 만에 나만의 AI 챗봇 만들기" (서드파티 요약, 원문 접근 제한) | "나만의" 소유격 + 소요시간 명시로 진입장벽을 낮춤 |

출처: https://www.chatpdf.com (WebFetch, 2026-08-06) · https://www.askyourpdf.com/pricing (WebFetch) · https://channel.io/ko/blog/articles/ai-assistant-alf-1ba879b9 (WebFetch) · https://help.wrtn.ai/studio (WebFetch, 뤼튼 스튜디오 공식 명칭은 부분만 확인) · WebSearch 보완("코딩 없이 10분" 문구는 검색 스니펫 기반, 원문 랜딩 페이지 직접 확인 실패)

### 1-2. B2B 신뢰형 — "우리 회사", 명사화된 신뢰, ROI

| 제품 | 원문 | 관찰 |
|---|---|---|
| Glean | "Work AI that understands your company" / "Glean connects knowledge, systems, and context so AI can actually work." / "Built for enterprise from day one" | "actually work"라는 반어적 강조로 경쟁제품 대비 실전성을 암시 |
| Allganize | "Enterprise AI you can *actually trust* to do the work. Bridge the gap from pilot to production." | Glean과 동일하게 "actually"를 이탤릭 강조 — B2B AI 카피의 공통 수사로 보임(2개 제품 확인) |
| Allganize (Alli SaaS) | "인프라 없이 시작하고, IT 통제권은 그대로 유지합니다" | 구매 결정권자(IT 부서)의 우려(권한 상실)를 직접 겨냥한 문장 |
| Upstage AI Space | "Your trusted AI for document-based work" / "delivers answers you can trust—grounded in your files with citations and full traceability" | "trust"를 헤드라인과 서브카피 양쪽에 중복 배치, 근거는 "citations and full traceability"로 즉시 구체화 |
| CustomGPT.ai | "Every AI answers questions. Create one you trust." / "3x productivity. Cut costs in half" | 신뢰(정성) 다음 문장에 곧바로 수치(정량) ROI를 붙이는 2단 구성 |
| Dust | "Multiplayer AI for human-agent collaboration." / "Trusted among AI Operators at 3,000+ global organizations" | "Multiplayer"라는 게임 용어를 협업 신뢰 은유로 전용 — 조사 대상 중 가장 독특한 어휘 선택 |
| Onyx | "Unlock Generative AI and productivity for your team" | "Unlock"(잠금 해제)로 이미 존재하지만 못 쓰고 있는 가치라는 프레이밍 |

출처: https://www.glean.com (WebFetch) · https://www.allganize.ai/ko/products/alli-saas (WebFetch) · https://www.upstage.ai/products/ai-space (WebFetch) · https://customgpt.ai/pricing/ (WebFetch) · https://dust.tt (Jina Reader, WebFetch 실패 후 재시도) · https://www.onyx.app/pricing (WebFetch)

### 1-3. 스펙트럼 관찰

1. **"trust/actually" 계열 동사가 B2B 카피의 공용어다.** Glean·Allganize·Upstage·CustomGPT.ai 4곳 모두 "신뢰"를 형용사가 아니라 "실제로 작동한다(actually work)"는 반증 프레임으로 쓴다 — 구매자가 이미 여러 AI 파일럿에서 실패를 겪었다고 전제하는 카피.
2. **B2C는 챗봇을 "부르는 대상"으로, B2B는 "일하는 주체"로 문법화한다.** 채널톡 ALF는 `@ALF`로 호출하는 2인칭 대상이지만, Dust·Glean은 "agents"를 3인칭 복수(팀의 일원)로 서술한다.
3. **한국 B2B 제품(Allganize)도 정작 자사 제품(알리)에는 페르소나를 안 입힌다.** 반면 같은 한국 제품인 채널톡 ALF는 B2B 고객(CS팀)을 대상으로 하면서도 카피 톤은 B2C에 가깝다 — 톤은 업종(B2B/B2C)이 아니라 **일상 사용 빈도**(하루에도 여러 번 부르는 도구인가)로 갈리는 것으로 보인다.

---

## 2. 네이밍 패턴

### 2-1. 제품명 유형 3분류

| 유형 | 예 | 특징 |
|---|---|---|
| 기능형(무엇을 하는지 이름에 박음) | ChatPDF, AskYourPDF, Chatbase, CustomGPT.ai, Upstage **AI Space** | 이름만으로 카테고리 설명 완료. 신규 시장 진입 시 SEO·즉시 이해에 유리하나 브랜드 확장성은 낮음 |
| 사람이름/캐릭터형 | 채널톡 **ALF** | 조사 대상 중 유일하게 3글자 고유명사형 이름을 붙이고 `@ALF`처럼 호출 가능한 개체로 취급 |
| 추상형(동사/추상명사에서 파생) | **Glean**("이삭을 줍다"), **Dust**, Allganize **Alli**(Ally의 변형으로 추정, 1차 소스에 어원 설명 없음 — 미확인) | 브랜드 확장에는 유리하나 처음 접하는 사용자에게 기능 설명 부담이 이름 밖 카피로 전가됨 |

출처: 각 제품 공식 페이지(1-1·1-2 표와 동일 출처). Alli 어원은 1차 소스에서 확인되지 않아 추정으로 표기.

### 2-2. 봇/어시스턴트 "개체"를 부르는 말 — 조사 대상 전체 비교

| 제품 | 지칭 | 비고 |
|---|---|---|
| AskYourPDF | "AI Agent" / "AI Chatbot" / "AI assistants" | 한 페이지 안에서 세 용어를 혼용 — 통일된 제품 어휘가 없음 |
| Upstage | "AI Space"(제품명 자체를 개체명처럼 사용, "the AI"라는 지칭은 없음) | — |
| Glean | "AI agents" / "**Glean Agents**"(고유명사화) / "enterprise agents" / "reasoning-based agents" | 제품 라인명(Glean Agents)과 일반명사(agents)를 같이 씀 |
| Onyx | "**Custom Agents**"(공식 문서 현재 용어) | GitHub 이슈·구버전 자료에 "Persona"·"Assistant" 표현이 남아있어 **Persona → Assistant → Agent로 명칭이 바뀐 것으로 추정**되나, 정확한 변천 시점은 1차 소스로 확인 못해 미확인 |
| 채널톡 | "**ALF**"(고유명사) / "AI 어시스턴트" / "AI 에이전트" | 자사 블로그가 "AI 어시스턴트? AI 에이전트(ALF)랑 뭐가 달라요?"라는 제목으로 자사 용어 혼란을 스스로 해설할 만큼 다의적 |
| Allganize | "Coworker"(제품 라인명, "알리 코워커") / "Works"(제품 라인명, "알리 웍스") | 개체를 지칭하는 일반명사보다 제품 라인명이 곧 지칭어 — "동료(coworker)"라는 은유는 이름에만 있고 본문 카피는 객관적 톤(페르소나화 없음, 1-2 표 참조) |
| 뤼튼 스튜디오 | "AI 서포터"("서포터"가 사용자 대화 상대를 가리키는 주요 개체어로 확인) | help.wrtn.ai 문서에서 확인, 상세 정의는 미확인 |

**종합**: "Agent"가 2026년 상반기 기준 업계 공용어로 굳어지는 중이나(Glean·Onyx·AskYourPDF·Dust 전부 사용), 정작 **엔드유저 대면 카피에서는 여전히 "Assistant/어시스턴트"가 더 자주 쓰인다**(채널톡·AskYourPDF). "Agent"는 관리자·개발자용 문서에서, "Assistant"는 최종 사용자용 마케팅 카피에서 쓰이는 계층 분화가 관찰된다.

---

## 3. 프라이싱 페이지 언어

### 3-1. 플랜명·가격·제한 표현 — 제품별 원문

| 제품 | 플랜 구성 | 무료 경계를 부르는 말 | 제한 단위 표현 |
|---|---|---|---|
| **ChatPDF** | Free / **ChatPDF Plus** | 계정 가입 없이 "2 documents every day" — 로그인 자체가 아니라 **일일 문서 수**가 경계 | 정확한 Plus 가격은 1차 소스(`/pricing`)가 404로 접근 실패. 서드파티 소스마다 $5·$19.99로 상충 표기되어 있어 **금액은 미확인으로 남김**(WebSearch, 2026-08-06) |
| **Humata** | Free / Expert($9.99) / Team($49/user) / Enterprise(custom) | "Basic features for up to **60 free pages**" | 과금 단위 = **페이지**("월 무료 페이지" + 초과 시 페이지당 $0.02→$0.01로 플랜이 오를수록 단가 하락) |
| **AskYourPDF** | Free / Premium($11.99) / Pro($14.99, "가장 인기") / Enterprise | "50 questions per day", "3 conversations per day" | 페이지수·MB·문서수/일·질문수/일·대화수/일 **5중 쿼터**로 세분화, 플랜별 AI 모델 등급도 분리(무료=GPT-5 Mini만) |
| **Onyx** | 무료 플랜 없음("Start Free Trial"만) / Business($20/user/월, 연간청구) / Enterprise(문의) | 무료가 아니라 **"체험판(trial)"**으로 경계를 표현 — 카드 등록 요구 여부는 미확인 | 페이지 단위가 아니라 "커넥터 수(40개+)"·"에이전트 수" 등 **연결 대상 개수** 기준 |
| **Chatbase** | Free($0) / Hobby($32) / Standard($120, 인기) / Pro($400) / Enterprise | "**50 message credits**/month" | 과금 단위 = "message credits" + "AI Actions per agent". 무료 플랜은 "**14일 비활성 시 에이전트 자동 삭제**"라는 벌칙성 조항이 명시됨 — 조사 대상 중 유일하게 무료 플랜에 삭제 페널티를 공개 문구화 |
| **CustomGPT.ai** | 7일 무료체험(카드 필수) / Standard($99) / Premium($499, 인기) / Enterprise | "free"가 아니라 **"trial"**, 카드 등록 후 자동 결제 전환을 페이지에 명시 | "에이전트 수"+"쿼리 수/월"+"에이전트당 문서 수"+"단어 저장 용량(6000만~3억 단어)" |
| **NotebookLM(Gemini Notebook)** | 단독 구매 불가 — **Google One AI Premium($19.99/월)**에 Plus가 번들. Business/Enterprise는 Workspace/Cloud 경유 | Business 페이지는 "**무료 평가판 시작하기**"만 노출, 가격은 "요금제 비교하기"로 이탈시킴(외부 링크) | 조사 대상 중 유일하게 **자체 요금제가 없는** 제품 — 가격 언어 자체가 다른 구독의 부속물로 존재 |
| **Perplexity** | (서드파티 집계, 2026 기준) Free / Pro($20) / Max($200) / Education Pro($10, 학생인증) / Enterprise Pro($40/seat) / Enterprise Max(custom) | — | 1차 페이지(`/pricing`, `/enterprise`) 모두 403으로 접근 실패, **표 전체가 서드파티 집계 기반이라 공식 확인 못함**(WebSearch, 2026-08-06) — 참고용으로만 인용 |
| **Glean** | 전면 비공개 | 경계 표현 자체가 없음 — "Get a Demo"만 | 가격 페이지가 아예 존재하지 않는 것으로 확인(WebFetch, `/pricing` 접근 시 가격표 없이 데모 CTA만 반환) |
| **Allganize** | 전면 비공개 | "도입 상담 후 조직 설정까지 **일주일 이내**"로 속도를 대체 지표로 제시 | — |
| **채널톡 ALF** | 정액 플랜이 아니라 **종량제**(그로스/엔터프라이즈 등 채널톡 자체 등급에 부가) | "월 3만 원 상당 **기본 제공량**"(무료가 아니라 매월 리필되는 크레딧) | 과금 단위 = **AU**(1AU=1원 상당의 자체 화폐 단위). v1은 "해결당 500~900원", v2는 "**상담 참여당** 500AU + 태스크 실행당 200AU"로 2025-11-28 전면 개편 |

출처: https://www.humata.ai/pricing · https://www.askyourpdf.com/pricing · https://www.onyx.app/pricing · https://www.chatbase.co/pricing · https://customgpt.ai/pricing/ (모두 WebFetch, 2026-08-06) · https://workspace.google.com/products/notebooklm/ (WebFetch) · https://docs.channel.io/updates/ko/articles/중요-공지-채널톡-가격제-개편-안내251128 (WebFetch) · Perplexity·ChatPDF 가격은 WebSearch 서드파티 집계(공식 페이지 접근 실패, 아래 접속 실패 로그 참조)

### 3-2. 프라이싱 언어 종합 관찰

1. **"무료"를 부르는 말이 최소 4갈래로 갈린다**: ① 순수 Free(가입만, Humata·Chatbase) ② 로그인조차 없는 일일 한도(ChatPDF) ③ 카드 등록이 필요한 "Trial"(Onyx·CustomGPT.ai — 사실상 유료 전환을 전제) ④ 상위 플랜 안의 "기본 제공량"(채널톡 ALF — 무료 플랜 자체가 없고 유료 플랜 안에 무료 크레딧만 있음). "Free"라는 단어를 쓰는지 여부가 곧 그 제품이 개인 사용자를 1차 타깃으로 하는지의 신호로 보인다.
2. **제한 단위가 곧 그 제품이 파는 것을 드러낸다**: 페이지 수(Humata·AskYourPDF)=문서량이 핵심 자원, 메시지/대화 크레딧(Chatbase)=대화량이 핵심 자원, 커넥터·에이전트 개수(Onyx)=조직 범위가 핵심 자원, AU 종량제(채널톡)=상담 해결 자체가 상품.
3. **엔터프라이즈행 제품일수록 가격을 아예 공개하지 않는다**(Glean·Allganize·Perplexity Enterprise류). 반대로 1인/소규모 팀 대상 제품(Humata·AskYourPDF·Chatbase)은 숫자를 표 형태로 전부 공개 — "말 걸어야 아는 가격"이 신뢰의 신호가 아니라 **영업조직 유무의 신호**로 읽힌다.
4. **무료 플랜에 벌칙 조항을 명문화하는 제품은 Chatbase뿐**("14일 비활성 시 에이전트 삭제") — 나머지는 계정 자체가 소멸한다는 표현을 쓰지 않는다.

---

## 4. 랜딩에서 "문서 근거·인용"을 파는 방식 — 신규 확인분

`03-rag-citation-ux.md`가 UI 패턴 자체는 이미 상세히 다뤘으므로, 여기서는 **랜딩(마케팅 페이지) 차원에서 인용을 어떻게 파는지**만 추가로 확인했다.

- **Upstage AI Space**: 히어로 서브카피에 바로 "delivers answers you can trust—grounded in your files with **citations and full traceability**"라고 텍스트로 명시. "**clause‑level citations**"(조항 단위 인용)라는 표현까지 히어로 근처에 등장 — Allganize의 "p.4 §2.3" 패턴과 동일한 조항 단위 구체화를 한국 문서AI 제품에서 한 곳 더 확인.
- **Allganize Alli SaaS**: 히어로 자체에는 인용 언급이 없고("인프라 없이 시작하고, IT 통제권은 그대로 유지합니다"), 인용 세일즈는 스크롤 하단 섹션에 위치(기존 조사와 동일 결론 재확인).
- **결론**: 이번에 새로 본 2개 제품(Upstage, Allganize)을 포함해 조사 누적 총 14개 제품 중 **히어로 최상단에 실제 각주/칩 UI 스크린샷을 넣은 사례는 여전히 Gemini Notebook 1건뿐**이다. 다른 제품들은 "인용/근거"를 문구로 히어로에 넣거나(Upstage), 아예 하단 섹션으로 미룬다(Allganize). 즉 "인용 UI를 보여주는 것"과 "인용을 판다는 문장을 쓰는 것"은 별개 전략이고, 전자를 택한 제품이 극소수라는 기존 결론이 신규 표본에서도 유지된다.

출처: https://www.upstage.ai/products/ai-space · https://www.allganize.ai/ko/products/alli-saas (둘 다 WebFetch, 2026-08-06)

---

## 5. 멀티봇/멀티 어시스턴트 포털형 제품 — 로스터 표현

이 라운드(`_brief.md`)가 요구하는 "N-가변 로스터"와 가장 직접적으로 비교할 수 있는 사례들이다.

| 제품 | 로스터 구조 | 개별 개체를 어떻게 구분·소개하는가 |
|---|---|---|
| **Glean** | Agent Orchestration → Agent Builder → **Agent Library** → Agentic Engine 4계층 | 개별 에이전트에 캐릭터·아바타를 주지 않고 **기능 카테고리**로 분류("reasoning-based agents" 등). 헤드라인은 "The platform for enterprise agents" — 로스터가 아니라 플랫폼 능력을 판다 |
| **Onyx** | 조직 내에서 사용자가 여러 "Custom Agents"를 만들어 팀원과 공유 | 각 에이전트는 "unique instructions, knowledge, and actions"로 구분되는 **설정값의 집합**으로 소개됨(캐릭터화 없음). 공식 문서가 "테스트 후 팀에 널리 공유하기 전 검증 권장"이라고 명시 — 로스터 확장을 신중히 관리하라는 톤 |
| **뤼튼 스튜디오** | 사용자가 만든 챗봇/도구를 **"AI 서포터"**로 부르고, 완성물을 마켓플레이스형 공간(검색 스니펫 기준 "AI 스토어")에 게시 | GPT Store와 유사한 **사용자 제작 로스터**형. 단, 공식 랜딩 원문은 접근 제한으로 부분 확인(help.wrtn.ai 문서 일부만 확인, 상세 UI 미확인) |
| **채널톡 ALF** | 단일 에이전트(ALF) 브랜드 하나를 "고객 ALF"/"팀 ALF"/"전화 ALF" 등 **채널(용도)별로 분화** | 로스터가 여러 봇이 아니라 **하나의 이름을 여러 접점에 재사용**하는 방식 — 이 프로젝트의 "N-가변 로스터"와는 반대되는 전략(단일 브랜드 확장) |
| **Dust** | "Multiplayer AI" — 사람과 에이전트가 **같은 대화 스레드에서 함께 협업**하는 것을 시각화(히어로에 "Ryan · Marketing Ops · just now"처럼 실명 사용자 프로필과 에이전트 멘션을 나란히 배치) | 봇 목록형 로스터가 아니라 **사람·에이전트 혼합 피드**로 표현 — 조사 대상 중 유일하게 로스터를 "명단"이 아니라 "대화 참여자 목록"으로 시각화 |
| **Poe** | (접속 실패) 여러 AI 모델/봇을 한 화면에 나열하는 대표 사례로 널리 알려져 있으나, 이번 조사에서 WebFetch(403)·Jina Reader(쿠키 배너만 반환) 모두 실패해 **원문 확인 못함**. UI 세부는 2차 지식에 의존하게 되므로 이 문서에서는 인용하지 않음 |

출처: https://www.glean.com/product/agents · https://docs.onyx.app/overview/core_features/agents(WebSearch 스니펫 경유, 문서 직접 인용은 검색 결과 요약) · https://help.wrtn.ai/studio · https://channel.io/ko/blog/articles/ai-assistant-alf-1ba879b9 · https://dust.tt (Jina Reader) — 전부 2026-08-06 확인

**핵심 관찰**: 조사한 멀티 에이전트 제품 중 어느 곳도 우리 라운드가 요구하는 "이니셜+컬러 시드 아바타로 개체를 시각적으로 구분한 카드형 로스터"를 쓰지 않는다. Glean·Onyx는 **기능 목록**으로, Dust는 **대화 피드**로, 뤼튼은 **마켓플레이스 그리드**(미확인, 추정)로 로스터를 표현한다 — 즉 "봇 카드 그리드"는 이번 조사 범위 내 상용 레퍼런스가 사실상 없는 설계 공백이며, 참고할 선례보다 자체 판단이 더 크게 작용해야 하는 영역으로 보인다.

---

## 6. 2026년 상반기 기준 변화분

1. **NotebookLM → Gemini Notebool 리브랜딩 + 유료 플랜의 구독 번들화**: 리브랜딩 자체는 기존 조사(`02-rag-product-landings.md`)에 이미 기록됨. 이번에 새로 확인한 것은 **유료 플랜(Plus)이 단독 상품이 아니라 Google One AI Premium($19.99/월) 안에서만 구매 가능**하다는 점 — 문서 챗봇 카테고리 자체가 범용 AI 구독의 부속 기능으로 편입되는 추세를 보여줌(WebFetch, workspace.google.com).
2. **채널톡 ALF v1→v2 과금 체계 전면 개편**(2025-11-28 공지 확정, 2026년 현재 적용 중): "해결당 정액"에서 "상담 참여당 종량(AU 단위)"으로 바뀌며 가격도 인상(96,000원→120,000원/월 등). 종량제 챗봇 상품이 사용량 정의를 세분화하는 방향으로 가고 있음을 보여주는 사례(WebFetch, docs.channel.io).
3. **Perplexity 요금제 재편**(서드파티 집계 기준, 공식 미확인): Max($200) 티어와 Education Pro($10) 티어가 신설되고 Enterprise가 Pro/Max로 분리된 것으로 보이나, 1차 페이지 접근 실패로 **확정할 수 없음** — 다음 조사 때 공식 페이지 재시도 필요.
4. **Upstage AI Space처럼 "조항 단위 인용"을 정면 카피로 내세우는 한국 제품이 최소 2곳(Allganize, Upstage)으로 늘었다** — 국내 문서AI 시장에서 이 표현이 표준 세일즈 포인트로 자리잡는 중일 가능성.

---

## 7. 우리 라운드에 주는 시사점

1. **"Trust/actually" 반증 프레임을 카피에 그대로 쓰지 말 것** — `_brief.md`가 이미 "근거 없는 답은 하지 않습니다류 플랫폼 카피 금지"를 명시했는데, 이번 조사로 그 이유가 보강된다: Glean·Allganize·CustomGPT.ai가 전부 같은 "actually work/trust" 수사를 쓰는 순간 **레드오션 문구**가 된다. 서약형 카피는 봇별 속성으로 구체적 사실(조항·문서명)을 담아야 차별화된다.
2. **"Agent"는 관리자용, "Assistant/어시스턴트"는 사용자용으로 계층을 나눠 쓰는 업계 관행을 따를 것** — 로스터를 만드는 관리자 화면과 실제 대화하는 사용자 화면에서 지칭어를 의도적으로 분리하면(Glean·Onyx가 실제로 그렇게 함) 두 페르소나의 눈높이를 맞추기 쉽다.
3. **무료 경계를 명확한 명사 하나로 못박을 것** — 조사 대상들은 "Free"·"Trial"·"기본 제공량" 등 서로 다른 개념을 쓰지만 각자 **하나의 일관된 용어**를 고수한다. 우리 봇 로스터에 유료/무료 구분이 생긴다면 처음부터 용어를 하나로 고정해야 한다(현재 브리프 범위엔 가격 UI가 없으나, 향후 확장 시 참고).
4. **"봇 카드 그리드형 로스터"는 참고할 상용 선례가 사실상 없다** — Glean(기능 목록)·Onyx(설정값 목록)·Dust(대화 피드) 어느 것도 우리가 만들려는 "이니셜 아바타 카드 그리드"와 겹치지 않는다. 즉 이 라운드의 로스터 UI는 문서AI 업계보다 오히려 소비자 앱(뮤직 플레이어·연락처 앱 등)의 그리드 패턴에서 차용하는 편이 더 근거 있는 선택일 수 있다.
5. **인용을 히어로에 "문구로" 넣는 옵션은 여전히 안전한 선택지다** — Upstage AI Space 사례가 추가되며, "그라운딩/추적가능성"을 텍스트 한 줄로 히어로에 넣는 전략이 국내 B2B 문서AI 제품 2곳(Allganize 별도 섹션 vs Upstage 히어로)에서 서로 다른 배치로 검증됨. 우리는 봇별 서약 카피(브리프 §대화·인용 UI 제약)에 이 조항 단위 구체성("규정집 §4" 식)을 반영할 근거가 하나 더 늘었다.
6. **무료 플랜에 벌칙 조항을 명문화하는 관행(Chatbase)은 신뢰 카피와 상충할 위험이 있다** — 우리는 참고하되 그대로 채택하지 말 것. 특히 인용·근거를 신뢰 언어로 파는 도메인에서 "방치하면 삭제"류 문구는 톤 충돌을 일으킬 수 있다.
7. **채널톡 ALF의 "단일 브랜드를 여러 접점에 재사용"하는 전략은 우리 라운드와 정반대 방향**이므로 오답 사례로만 참고한다 — 우리는 N개의 서로 다른 봇을 보여줘야 하는데, ALF는 반대로 여러 접점에서 하나의 이름을 재사용해 브랜드를 통합한다. 이 차이를 팀 내부 설명자료에 "우리가 안 하는 것"으로 남겨둘 가치가 있다.

---

## 부록: 접속 실패 로그

| 대상 | 1차 시도 | 결과 | 우회 | 최종 상태 |
|---|---|---|---|---|
| perplexity.ai/pricing | WebFetch | 403 Forbidden | Jina Reader(캐시 배너만 반환) | 실패, 서드파티 집계로 대체(§3-1 명시) |
| perplexity.ai/enterprise | WebFetch | 403 Forbidden | 미시도(시간 제약) | 실패, 표에서 제외 |
| chatpdf.com/pricing | WebFetch | 404 Not Found | Jina Reader(동일 404) | 실패, 서드파티 소스 간 가격 상충 확인 후 금액 미확인 처리 |
| sendbird.com/products/ai-agent(s) | WebFetch(2회, URL 추정) | 404 Not Found | WebSearch로 정확한 URL 재탐색했으나 시간 제약으로 재시도 중단 | 실패, 이번 문서에서 Sendbird 제외 |
| poe.com | WebFetch | 403 Forbidden | Jina Reader(쿠키 배너 텍스트만 반환, 본문 없음) | 실패, §5에서 미확인으로 명시하고 인용 안 함 |
| docs.onyx.app/overview/core_features/agents | 미시도(직접 WebFetch 대신 WebSearch로 대체) | — | WebSearch 스니펫으로 대체 확인 | 부분 성공(원문 전체는 미확인) |
