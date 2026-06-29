/**
 * 중간보고 입력관리 상수 — 상태/레벨/분류/태그/봇 정규화. 공통 상수는 redteam 도메인 재사용.
 */

// 공통(카테고리·위험도·색상) 재사용
export {
  CATEGORIES,
  RISK_LEVELS,
  RISK_STYLE,
  RISK_COLOR,
  WEEK_COLOR,
  CATEGORY_COLOR,
  BOT_FULL_LABEL,
} from "../redteam/constants"

// 검증 상태
export const STATUS_OPTIONS = [
  { value: "대기", label: "대기" },
  { value: "진행중", label: "진행중" },
  { value: "검증완료", label: "검증완료" },
] as const

export const STATUS_STYLE: Record<string, string> = {
  대기: "bg-muted text-muted-foreground",
  진행중: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  검증완료: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
}

export const STATUS_COLOR: Record<string, string> = {
  대기: "#9aa39a", // sage
  진행중: "#b08524", // brass
  검증완료: "#1e3a34", // pine
}

// 보완 레벨 0~3
export const LEVEL_OPTIONS = [
  { value: 0, label: "0 · 보완 불필요" },
  { value: 1, label: "1 · 실무 보완" },
  { value: 2, label: "2 · 가정국 정책결정" },
  { value: 3, label: "3 · 가정국 초과 합의" },
] as const

export const LEVEL_SHORT: Record<number, string> = {
  0: "Lv0 보완불필요",
  1: "Lv1 실무보완",
  2: "Lv2 정책결정",
  3: "Lv3 초과합의",
}

export const LEVEL_STYLE: Record<number, string> = {
  0: "bg-muted text-muted-foreground",
  1: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  2: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  3: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
}

export const LEVEL_COLOR: Record<string, string> = {
  "0": "#9aa39a", // sage
  "1": "#b08524", // brass
  "2": "#c2611f", // amber
  "3": "#b5321e", // garnet
  미분류: "#cbd2cb",
}

// 처리 분류
export const DISPOSITION_OPTIONS = [
  { value: "학습", label: "학습" },
  { value: "FAQ", label: "FAQ" },
  { value: "미정", label: "미정" },
] as const

export const DISPOSITION_STYLE: Record<string, string> = {
  학습: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  FAQ: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  미정: "bg-muted text-muted-foreground",
}

export const DISPOSITION_COLOR: Record<string, string> = {
  학습: "#1e3a34", // pine
  FAQ: "#b08524", // brass
  미정: "#9aa39a", // sage
}

// 이전 주차 봇 → 3주차 C/D 라인업 정규화 (BE crud_redteam.PRIOR_BOT_TO_CD와 동일 기준, 범례용)
export const PRIOR_BOT_TO_CD: Record<string, "C" | "D" | null> = {
  A_통합: "D",
  C_정밀: "C",
  B_원리: null,
  원문: null,
}

// 비교 탭 봇 표시 라벨 (C/D 정규화 + 원문)
export const COMPARE_BOT_LABEL: Record<string, string> = {
  C: "C · 따뜻한 실무안내자",
  D: "D · 여정 동반자",
  원문: "원문 (1주차 단일봇)",
}
