/**
 * FAQ 도메인 — API 호출 함수 + Query Key Factory.
 *
 * 현재는 더미 데이터를 반환하며, 백엔드 연동 시
 * apiClient (Axios) 호출로 교체한다.
 */
// import { apiClient } from "@/lib/api-client"
import type {
  FaqCreateRequest,
  FaqListResponse,
  FaqResponse,
  FaqUpdateRequest,
} from "./types"

// ─── Query Key Factory ────────────────────────────────────────
// Query Key 파편화 방지: 중앙에서 일관되게 관리
export const faqKeys = {
  all: ["faqs"] as const,
  lists: (botId: number) => [...faqKeys.all, "list", botId] as const,
  detail: (id: number) => [...faqKeys.all, "detail", id] as const,
}

// ─── 더미 데이터 ──────────────────────────────────────────────
// 백엔드 연동 전까지 프론트엔드 개발에 사용하는 Mock 데이터
let nextId = 5
const DUMMY_FAQS: FaqResponse[] = [
  {
    id: 1,
    bot_id: 1,
    question: "영업시간이 어떻게 되나요?",
    answer: "평일 09:00 ~ 18:00, 주말 및 공휴일 휴무입니다.",
    threshold: 0.85,
    is_active: true,
    created_at: "2026-02-20T09:00:00Z",
    updated_at: "2026-02-20T09:00:00Z",
  },
  {
    id: 2,
    bot_id: 1,
    question: "환불 정책이 어떻게 되나요?",
    answer: "구매일로부터 7일 이내에 환불 요청이 가능합니다. 단, 사용한 상품은 환불이 불가합니다.",
    threshold: 0.8,
    is_active: true,
    created_at: "2026-02-21T10:30:00Z",
    updated_at: "2026-02-21T10:30:00Z",
  },
  {
    id: 3,
    bot_id: 1,
    question: "배송은 얼마나 걸리나요?",
    answer: "주문 후 2~3 영업일 이내에 배송됩니다. 도서산간 지역은 1~2일 추가 소요될 수 있습니다.",
    threshold: 0.75,
    is_active: true,
    created_at: "2026-02-22T14:00:00Z",
    updated_at: "2026-02-22T14:00:00Z",
  },
  {
    id: 4,
    bot_id: 2,
    question: "비밀번호를 잊어버렸어요.",
    answer: "로그인 화면에서 '비밀번호 찾기'를 클릭한 뒤, 등록된 이메일로 재설정 링크를 받으세요.",
    threshold: 0.9,
    is_active: true,
    created_at: "2026-02-23T11:00:00Z",
    updated_at: "2026-02-23T11:00:00Z",
  },
]

// ─── API 함수 ─────────────────────────────────────────────────

/** FAQ 목록 조회 (특정 봇) */
export async function fetchFaqs(botId: number): Promise<FaqListResponse> {
  // TODO: 백엔드 연동 시 아래로 교체
  // const { data } = await apiClient.get<FaqListResponse>(
  //   "/api/v1/admin/faqs",
  //   { params: { bot_id: botId } }
  // )
  // return data

  await delay(300)
  const filtered = DUMMY_FAQS.filter((faq) => faq.bot_id === botId)
  return { faqs: filtered, total: filtered.length }
}

/** FAQ 단일 조회 */
export async function fetchFaq(id: number): Promise<FaqResponse> {
  // TODO: 백엔드 연동 시 교체
  // const { data } = await apiClient.get<FaqResponse>(`/api/v1/admin/faqs/${id}`)
  // return data

  await delay(200)
  const faq = DUMMY_FAQS.find((f) => f.id === id)
  if (!faq) throw new Error(`FAQ #${id}을(를) 찾을 수 없습니다.`)
  return faq
}

/** FAQ 등록 */
export async function createFaq(
  request: FaqCreateRequest
): Promise<FaqResponse> {
  // TODO: 백엔드 연동 시 교체
  // const { data } = await apiClient.post<FaqResponse>(
  //   "/api/v1/admin/faqs",
  //   request
  // )
  // return data

  await delay(300)
  const now = new Date().toISOString()
  const newFaq: FaqResponse = {
    id: nextId++,
    bot_id: request.bot_id,
    question: request.question,
    answer: request.answer,
    threshold: request.threshold ?? 0.8,
    is_active: request.is_active ?? true,
    created_at: now,
    updated_at: now,
  }
  DUMMY_FAQS.push(newFaq)
  return newFaq
}

/** FAQ 수정 (부분 업데이트) */
export async function updateFaq(
  id: number,
  request: FaqUpdateRequest
): Promise<FaqResponse> {
  // TODO: 백엔드 연동 시 교체
  // const { data } = await apiClient.put<FaqResponse>(
  //   `/api/v1/admin/faqs/${id}`,
  //   request
  // )
  // return data

  await delay(300)
  const idx = DUMMY_FAQS.findIndex((f) => f.id === id)
  if (idx === -1) throw new Error(`FAQ #${id}을(를) 찾을 수 없습니다.`)
  DUMMY_FAQS[idx] = {
    ...DUMMY_FAQS[idx],
    ...request,
    updated_at: new Date().toISOString(),
  }
  return DUMMY_FAQS[idx]
}

/** FAQ 삭제 */
export async function deleteFaq(id: number): Promise<void> {
  // TODO: 백엔드 연동 시 교체
  // await apiClient.delete(`/api/v1/admin/faqs/${id}`)

  await delay(200)
  const idx = DUMMY_FAQS.findIndex((f) => f.id === id)
  if (idx !== -1) DUMMY_FAQS.splice(idx, 1)
}

// ─── 유틸 ─────────────────────────────────────────────────────
function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
