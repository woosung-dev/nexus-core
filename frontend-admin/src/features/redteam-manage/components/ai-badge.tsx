// AI 자동분류(Lv0) 출처 배지 — 솔리드 바이올렛 + 스파클 아이콘으로 사람 결정과 구분
import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export function AiBadge({ className, title }: { className?: string; title?: string }) {
  return (
    <span
      title={title ?? "AI가 자동 분류한 항목 (codex). 사람이 레벨을 변경하면 수동 검수로 확정됩니다."}
      className={cn(
        "inline-flex items-center gap-1 rounded bg-violet-600 px-1.5 py-0.5 text-[10px] font-semibold text-white shadow-sm",
        className
      )}
    >
      <Sparkles className="size-2.5" aria-hidden />
      AI 자동
    </span>
  )
}
