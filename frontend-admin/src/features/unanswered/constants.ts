import type { UnansweredReason, UnansweredTriage } from "./types"

/**
 * 이유코드 — 무엇을 **관측**했는가.
 *
 * 「답할 수 있었나」를 추정한 것이 아니다. 45문항 실측에서 검색 점수 네 갈래가 전부
 * 실패했고 같은 시도가 과거에도 두 번 기각됐다. 여기 있는 것은 전부 사실이다 —
 * 검색이 빈손이었다, 폴백했다, 봇이 스스로 못 답한다고 말했다.
 */
export const REASON_LABEL: Record<UnansweredReason, string> = {
  empty_answer: "답변이 비었음",
  lexical_empty: "어휘 검색 빈손",
  corpus_unavailable: "코퍼스 없음",
  self_refusal: "봇이 거절함",
  judge_clarify: "되물을 것 있음",
}

/** 그 신호가 사용자에게 무엇으로 보였는지 — 화면에서 오해가 없어야 한다 */
export const REASON_EFFECT: Record<UnansweredReason, string> = {
  empty_answer: "고정 문구가 나갔다",
  lexical_empty: "의미 검색으로 되돌려 정상 답변했다",
  corpus_unavailable: "의미 검색으로 되돌려 정상 답변했다",
  self_refusal: "봇이 쓴 거절 문구가 그대로 나갔다",
  judge_clarify: "사용자에겐 안 보였다 (기록 전용)",
}

export const REASON_STYLE: Record<UnansweredReason, string> = {
  empty_answer: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  lexical_empty: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  corpus_unavailable: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  self_refusal: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  judge_clarify: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
}

/**
 * 처리 경로 — 어느 트랙의 일인가.
 *
 * 「운영 사실 등록」 단추 하나로 두지 않았다. `ops_facts` 는 문서를 **못 고칠 때** 쓰는
 * 런타임 덮개라(모델 규약이 positive 지식을 금지한다), 덮개가 기본 경로가 되면 문서 개선
 * 트랙이 조용히 죽는다. 어느 칸에 일이 몰리는지가 먼저 보여야 한다.
 */
export const TRIAGE_LABEL: Record<UnansweredTriage, string> = {
  미분류: "미분류",
  문서없음: "문서 없음",
  검색못함: "문서 있는데 못 찾음",
  문서오류: "문서가 틀림·낡음",
  해당없음: "해당 없음",
}

/** 그 경로를 고르면 실제로 무엇을 해야 하는가 */
export const TRIAGE_ACTION: Record<UnansweredTriage, string> = {
  미분류: "아직 분류하지 않았다",
  문서없음: "Documents 에 원본을 올린다",
  검색못함: "검색기·위키 트랙으로 넘긴다",
  문서오류: "운영 사실로 덮는다",
  해당없음: "답하지 않는 것이 맞다",
}

export const TRIAGE_ORDER: UnansweredTriage[] = [
  "미분류",
  "문서없음",
  "검색못함",
  "문서오류",
  "해당없음",
]

/**
 * 색만으로 뜻을 전하지 않는다 — 라벨과 아이콘이 항상 함께 간다.
 * 여기 스타일은 보조 신호일 뿐이다.
 */
export const TRIAGE_STYLE: Record<UnansweredTriage, string> = {
  미분류: "bg-muted text-muted-foreground",
  문서없음: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  검색못함: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  문서오류: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  해당없음: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
}

/** 표에서 선택 상자를 감싸는 테두리. 색은 거들 뿐, 뜻은 아이콘+라벨이 진다. */
export const TRIAGE_RING: Record<UnansweredTriage, string> = {
  미분류: "",
  문서없음: "ring-1 ring-amber-300 dark:ring-amber-900",
  검색못함: "ring-1 ring-sky-300 dark:ring-sky-900",
  문서오류: "ring-1 ring-violet-300 dark:ring-violet-900",
  해당없음: "ring-1 ring-emerald-300 dark:ring-emerald-900",
}

/** 이 경로에서만 운영 사실 등록으로 넘어간다 */
export const OPS_FACT_TRIAGE: UnansweredTriage = "문서오류"

/** 서버 기본 보존 기간 — `crud_unanswered.RETENTION_DAYS` 와 같아야 한다 */
export const RETENTION_DAYS = 90
