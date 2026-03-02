"use client"

/**
 * 문서 상태(Status) 뱃지 컴포넌트.
 * status 값에 따라 시각적으로 구분된 Badge를 렌더링한다.
 */
import { Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface DocumentStatusBadgeProps {
  status: string | null
}

type StatusConfig = {
  label: string
  variant: "secondary" | "outline" | "default" | "destructive"
  showSpinner?: boolean
  className?: string
}

function getStatusConfig(status: string | null): StatusConfig {
  switch (status) {
    case "completed":
      return { label: "완료", variant: "default", className: "bg-emerald-500 hover:bg-emerald-500 text-white" }
    case "in_progress":
      return { label: "처리 중", variant: "outline", showSpinner: true, className: "border-amber-500 text-amber-600" }
    case "queued":
      return { label: "대기 중", variant: "secondary", className: "text-muted-foreground" }
    case "failed":
      return { label: "실패", variant: "destructive" }
    default:
      return { label: "알 수 없음", variant: "secondary", className: "text-muted-foreground" }
  }
}

export function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const config = getStatusConfig(status)

  return (
    <Badge variant={config.variant} className={config.className}>
      {config.showSpinner && (
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
      )}
      {config.label}
    </Badge>
  )
}
