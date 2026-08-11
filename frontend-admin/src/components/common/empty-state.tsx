// 빈 상태. 15곳이 제각각이었다 — 테두리 유/무, dashed/solid, p-10/p-12/py-6/h-64,
// 흰 배경에 그림자가 붙은 곳도 있었다. 하나로 모은다.
import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed bg-card px-6 py-12 text-center">
      {Icon ? <Icon className="size-6 text-muted-foreground/60" aria-hidden /> : null}
      <p className="text-sm font-medium">{title}</p>
      {description ? (
        <p className="max-w-md text-xs leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}
