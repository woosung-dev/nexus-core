import type { OpsFactKind, OpsFactStatus } from "./types"

export const KIND_LABEL: Record<OpsFactKind, string> = {
  deprecated: "폐지·현행 미적용",
  forbidden: "존재하지 않는 것",
  term: "표기 통일",
  contact: "연락처",
  crisis: "위기 자원",
}

/** 각 종류가 런타임에서 실제로 무엇을 하는지 — 화면에서 오해가 없어야 한다 */
export const KIND_EFFECT: Record<OpsFactKind, string> = {
  deprecated: "프롬프트에 항상 실린다",
  forbidden: "프롬프트에 항상 실린다",
  term: "프롬프트에 넣지 않고, 답변 문구를 직접 바꾼다",
  contact: "프롬프트에 항상 실린다",
  crisis: "질문에 트리거 표현이 있을 때만 실린다",
}

export const KIND_ORDER: OpsFactKind[] = [
  "crisis",
  "deprecated",
  "forbidden",
  "contact",
  "term",
]

export const KIND_STYLE: Record<OpsFactKind, string> = {
  deprecated: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  forbidden: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  term: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  contact: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  crisis: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
}

export const STATUS_STYLE: Record<OpsFactStatus, string> = {
  초안: "bg-muted text-muted-foreground",
  승인: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  수정승인: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  반려: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
}

/** 런타임에 실제로 반영되는 상태 */
export const RUNTIME_STATUS: OpsFactStatus[] = ["승인", "수정승인"]

export const DOC_STYLE: Record<string, string> = {
  규정집v20: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  공문: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  관리자확인: "bg-muted text-muted-foreground",
}
