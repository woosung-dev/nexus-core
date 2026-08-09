"use client"

// 입력관리 보드 상단 — 정답지 검수 진행률 스트립.
//
// 담당자별 잔여를 굳이 노출하는 이유: 배정 836건 중 한 명은 검증완료 0건인 상태가 오래 갔다.
// 총합만 보면 그게 안 보인다. 누가 막혀 있는지가 보여야 재배분 결정이 선다.
import { cn } from "@/lib/utils"
import { useGoldenQueue } from "../hooks"

const SEG: { key: string; label: string; cls: string }[] = [
  { key: "초안", label: "검수 대기", cls: "bg-muted-foreground/40" },
  { key: "승인", label: "맞음", cls: "bg-emerald-500" },
  { key: "수정승인", label: "수정됨", cls: "bg-sky-500" },
  { key: "근거없음", label: "결정 필요", cls: "bg-amber-500" },
  { key: "반려", label: "반려", cls: "bg-red-500" },
]

export function GoldenProgress() {
  const { data } = useGoldenQueue()
  if (!data || data.total === 0) return null

  const pct = Math.round((100 * data.decided) / data.total)

  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="text-muted-foreground">
          정답지 검수{" "}
          <b className="rtm-mono text-sm text-foreground">
            {data.decided}/{data.total}
          </b>{" "}
          ({pct}%)
        </span>
        <span className="h-3.5 w-px bg-border" />
        {SEG.filter((s) => data.by_status[s.key]).map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            <span className={cn("size-2 rounded-full", s.cls)} />
            <span className="text-muted-foreground">{s.label}</span>
            <b className="rtm-mono text-foreground">{data.by_status[s.key]}</b>
          </span>
        ))}
        <span className="ml-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-muted-foreground">
          {Object.entries(data.by_assignee)
            .sort((a, b) => a[1].decided / a[1].total - b[1].decided / b[1].total)
            .map(([who, v]) => (
              <span key={who} className="flex items-center gap-1">
                {who}
                <b
                  className={cn(
                    "rtm-mono",
                    v.decided === 0 ? "text-red-600 dark:text-red-400" : "text-foreground"
                  )}
                >
                  {v.decided}/{v.total}
                </b>
              </span>
            ))}
        </span>
      </div>

      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        {SEG.map((s) => {
          const n = data.by_status[s.key] ?? 0
          if (!n) return null
          return (
            <div
              key={s.key}
              className={s.cls}
              style={{ width: `${(100 * n) / data.total}%` }}
              title={`${s.label} ${n}건`}
            />
          )
        })}
      </div>
    </div>
  )
}
