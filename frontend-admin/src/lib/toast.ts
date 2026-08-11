import { AxiosError } from "axios"
import { toast } from "sonner"

/**
 * 변경 작업의 결과를 알린다.
 *
 * 지금까지 이 레포에는 성공·실패를 알리는 수단이 없었다. 훅 20여 개에 onError 가
 * 0건이라 봇 저장이 실패해도 버튼만 원래 글자로 돌아왔고, 사용자는 저장된 줄 알았다.
 */

/** FastAPI 는 오류를 `{ detail: ... }` 로 준다. 사람이 읽을 한 줄만 뽑는다. */
function messageOf(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    // 422 검증 오류는 배열로 온다.
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg
    if (error.code === "ECONNABORTED") return "서버 응답이 늦어 중단했습니다."
    if (!error.response) return "서버에 연결하지 못했습니다."
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export function toastSuccess(message: string) {
  toast.success(message)
}

export function toastError(error: unknown, fallback: string) {
  toast.error(fallback, { description: messageOf(error, fallback) })
}
