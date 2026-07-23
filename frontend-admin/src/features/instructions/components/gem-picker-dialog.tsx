"use client"

// 저장된 Gem을 골라 오는 공용 선택 모달 — 비교 탭(열별 불러오기)과 프롬프트 생성 탭(생성기 선택)에서 함께 쓴다.
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { BotInstruction } from "../types"

type GemPickerDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  gems: BotInstruction[]
  onSelect: (gem: BotInstruction) => void
  title?: string
  description?: string
}

export function GemPickerDialog({
  open,
  onOpenChange,
  gems,
  onSelect,
  title = "Gem 불러오기",
  description = "적용할 Gem을 선택하세요.",
}: GemPickerDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {gems.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            저장된 Gem이 없어요. 먼저 빌더 탭에서 만들어 주세요.
          </p>
        ) : (
          <ul className="max-h-[50vh] divide-y overflow-y-auto">
            {gems.map((gem) => (
              <li key={gem.id}>
                <button
                  type="button"
                  className="flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-accent/50"
                  onClick={() => {
                    onSelect(gem)
                    onOpenChange(false)
                  }}
                >
                  <span className="text-sm font-medium">{gem.name || "(제목 없음)"}</span>
                  {gem.description && (
                    <span className="line-clamp-1 text-xs text-muted-foreground">{gem.description}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  )
}
