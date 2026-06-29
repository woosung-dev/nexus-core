/**
 * 레드팀 대시보드 상수 — 카테고리/위험도/반영여부/리뷰어 슬롯.
 */
import type { ReflectValue } from "./types"

export const CATEGORIES = [
  "축복 준비 및 매칭",
  "가정출발",
  "축복정리",
  "축복유형",
  "탈선 등 성적 문제",
] as const

// 위험도: 없음 < 하 < 중 < 상
export const RISK_LEVELS = ["없음", "하", "중", "상"] as const

export const RISK_STYLE: Record<string, string> = {
  없음: "bg-muted text-muted-foreground",
  하: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  중: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  상: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
}

export const REFLECT_OPTIONS: { value: ReflectValue; label: string }[] = [
  { value: "reflect", label: "반영" },
  { value: "skip", label: "미반영" },
  { value: "pending", label: "보류" },
]

export const REFLECT_STYLE: Record<ReflectValue, string> = {
  reflect: "bg-emerald-600 text-white border-emerald-600",
  skip: "bg-slate-500 text-white border-slate-500",
  pending: "bg-transparent text-muted-foreground",
}

// 봇 응답 키 → 표시 라벨
export const BOT_LABELS: Record<string, string> = {
  원문: "응답 (원문)",
  A_통합: "A · 통합",
  B_원리: "B · 원리",
  C_정밀: "C · 정밀",
  C: "C · 따뜻한 실무안내자",
  D: "D · 여정 동반자",
  적절챗봇: "응답이 적절한 챗봇",
}

// 보고용 차트 색상 팔레트 — "심의·봉인" (sage/brass/amber/garnet 단계화)
export const RISK_COLOR: Record<string, string> = {
  없음: "#9aa39a", // sage
  하: "#b08524", // brass
  중: "#c2611f", // amber
  상: "#b5321e", // garnet
}

export const WEEK_COLOR: Record<string, string> = {
  "1주차": "#9aa39a", // sage
  "2주차": "#b08524", // brass
  "3주차": "#1e3a34", // pine
}

export const BOT_COLOR: Record<string, string> = {
  C: "#b08524", // brass — 따뜻한 실무안내자
  D: "#1e3a34", // pine — 여정 동반자
  부적절: "#b5321e", // garnet
}

export const BOT_FULL_LABEL: Record<string, string> = {
  C: "C · 따뜻한 실무안내자",
  D: "D · 여정 동반자",
  부적절: "둘 다 부적절",
}

// 카테고리 정성 팔레트 (E 톤 — 파인/브라스/세이지/가넷 계열)
export const CATEGORY_COLOR: Record<string, string> = {
  "축복 준비 및 매칭": "#1e3a34", // pine
  가정출발: "#5e8d80", // sage-pine
  축복정리: "#8a6d3b", // deep brass
  축복유형: "#b08524", // brass
  "탈선 등 성적 문제": "#b5321e", // garnet
  미분류: "#9aa39a", // sage
}

// 리뷰어 슬롯 (최대 3명) — localStorage에 이름 저장
export const REVIEWER_SLOT_COUNT = 3
export const DEFAULT_REVIEWER_NAMES = ["리뷰어 1", "리뷰어 2", "리뷰어 3"]
export const REVIEWER_NAMES_KEY = "redteam.reviewerNames"
export const REVIEWER_ACTIVE_KEY = "redteam.activeReviewer"
