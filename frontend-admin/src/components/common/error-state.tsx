// 에러 표시. 네 가지가 병존했다 — text-red-500 / red-50 박스 / text-destructive /
// text-zinc-500(에러인데 회색). 여기가 유일한 규격이고, 토큰만 쓴다.
//
// role="alert" 를 붙이는 이유: 이 레포에 aria-live 가 2건뿐이라 조회 실패가
// 스크린리더에 전혀 고지되지 않았다.
import { AlertCircle } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"

export function ErrorState({
  title = "불러오지 못했습니다",
  error,
  onRetry,
}: {
  title?: ReactNode
  error?: unknown
  onRetry?: () => void
}) {
  const detail = error instanceof Error ? error.message : null

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-6 py-10 text-center"
    >
      <AlertCircle className="size-6 text-destructive" aria-hidden />
      <p className="text-sm font-medium text-destructive">{title}</p>
      {detail ? (
        <p className="max-w-md text-xs leading-relaxed text-destructive/80">{detail}</p>
      ) : null}
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          다시 시도
        </Button>
      ) : null}
    </div>
  )
}
