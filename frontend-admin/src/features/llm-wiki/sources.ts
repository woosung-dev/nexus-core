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

export const CORPUS = { articles: 0, glossary: 0, gongmun: 0, ingested: 0 }

export type SourceKind = "reg" | "glo" | "gm" | "obs"

export type RawSource = { id: string; doc: string; kind: SourceKind; locator: string; /** 레포 기준 실제 파일 경로 */ file: string; quote: string }

export const SOURCES: RawSource[] = []
