/**
 * LLM 위키 — **빈 껍데기다. 실데이터가 아니다.**
 *
 * 채우려면: python3 exports/wiki_2026-08/_gen_admin.py --bot 11
 *   (원본 PDF 2종 + ingest 산출물이 로컬에 있어야 한다)
 *
 * 왜 비어 있나 — 이 레포는 public 이고, 실데이터에는 규정집 v20(승인 전 개정초안,
 * "초안 조문번호의 대외 인용 금지")과 대사전 v4(사용 승인 미결) 전문이 들어간다.
 * 커밋되면 되돌릴 수 없어 껍데기만 둔다. 빌드는 이 파일로 통과한다.
 */

export type Claim = {
  text: string
  /** 이 문장을 뒷받침하는 raw 소스 id. 비면 '근거 없음'으로 표시된다. */
  refs: string[]
  /** 원문에서 그대로 복사한 구간. _verify.py 가 raw 와 대조해 통과한 것만 실린다. */
  quote: string
  /** 이 문장이 모순 안에 있으면 모순 id */
  conflict?: string
}

export type WikiPage = {
  slug: string
  title: string
  category: string
  /** 이 페이지가 참조하는 다른 위키 페이지 slug */
  links: string[]
  summary: string
  claims: Claim[]
  /** 이 페이지를 만든 소스들 */
  updated: string
  /** 레포 기준 실제 파일 경로 */
  file: string
}

export type Conflict = {
  id: string
  title: string
  /** 서로 다른 말을 하는 쪽들 */
  sides: { label: string; says: string; ref: string }[]
  impact: string
  page: string
  status: "미해결" | "확인 요청됨"
}

export type Gap = {
  id: string
  title: string
  detail: string
  page: string
  /** 이 질문을 띄운 소스 */
  hits: string
}

export const PAGES: WikiPage[] = []
export const CONFLICTS: Conflict[] = []
export const GAPS: Gap[] = []
export const LOG: { date: string; op: string; title: string; detail: string }[] = []
