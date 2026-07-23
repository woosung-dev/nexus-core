"use client"

// Gem 갤러리(좌측 master) — 생성·선택.
import { Gem, Plus } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { BotInstruction } from "../types"

type GemListProps = {
  gems: BotInstruction[]
  isLoading: boolean
  selectedId: number | "new" | null
  onSelect: (id: number) => void
  onNew: () => void
}

export function GemList({ gems, isLoading, selectedId, onSelect, onNew }: GemListProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-3">
        <Button type="button" size="sm" className="w-full" onClick={onNew}>
          <Plus />새 Gem
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {selectedId === "new" && (
          <div className="flex items-center gap-2 border-b bg-accent px-3 py-2.5 text-sm">
            <Gem className="size-4 shrink-0 text-muted-foreground" />
            <span className="font-medium">새 Gem</span>
            <Badge variant="outline" className="ml-auto text-[10px] text-muted-foreground">미저장</Badge>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : gems.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center gap-1 px-4 text-center text-sm text-muted-foreground">
            {selectedId === "new" ? (
              <span>오른쪽에서 첫 Gem을 작성하고 저장하세요.</span>
            ) : (
              <>
                <span>아직 Gem이 없어요.</span>
                <span className="text-xs">위 &lsquo;새 Gem&rsquo;으로 시작해 보세요.</span>
              </>
            )}
          </div>
        ) : (
          <ul className="divide-y">
            {gems.map((gem) => {
              const selected = gem.id === selectedId
              return (
                <li key={gem.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(gem.id)}
                    className={cn(
                      "flex w-full flex-col gap-1 px-3 py-2.5 text-left transition-colors",
                      selected ? "bg-accent" : "hover:bg-accent/50"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Gem className="size-4 shrink-0 text-muted-foreground" />
                      <span className="line-clamp-1 flex-1 text-sm font-medium">{gem.name || "(제목 없음)"}</span>
                    </div>
                    {gem.description && (
                      <p className="line-clamp-2 pl-6 text-xs text-muted-foreground">{gem.description}</p>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
