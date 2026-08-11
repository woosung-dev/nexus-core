// 페이지 머리. 지금까지 10개 화면이 같은 블록을 각자 적었고 h1 크기가 5종이었다
// (text-2xl bold / text-2xl semibold / text-3xl bold / rt-display / chats 는 h2).
// 여기가 유일한 규격이다.
import type { ReactNode } from "react"

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode
  description?: ReactNode
  /** 우측 상단 버튼 자리 */
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold tracking-tight">
          {title}
        </h1>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  )
}
