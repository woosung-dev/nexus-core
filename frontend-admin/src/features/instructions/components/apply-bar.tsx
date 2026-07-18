"use client"

// 완성한 지침을 선택한 봇에 적용하는 하단 작업 표시줄.
import * as React from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useApplyToBot } from "../hooks"

type ApplyBarProps = {
  systemPrompt: string
  botId: number | null
  llm_model: string
}

export function ApplyBar({ systemPrompt, botId, llm_model }: ApplyBarProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [applied, setApplied] = React.useState(false)
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const apply = useApplyToBot()

  React.useEffect(() => () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
  }, [])

  function confirmApply() {
    if (botId === null) return
    apply.mutate(
      { botId, system_prompt: systemPrompt, llm_model },
      {
        onSuccess: () => {
          setIsOpen(false)
          setApplied(true)
          if (timeoutRef.current) clearTimeout(timeoutRef.current)
          timeoutRef.current = setTimeout(() => setApplied(false), 3_000)
        },
      }
    )
  }

  return (
    <>
      <div className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-background/95 p-3 backdrop-blur">
        <div className="text-sm">
          {applied && <span className="text-primary">적용됨 ✓</span>}
          {apply.isError && <span className="text-destructive">봇 지침 적용에 실패했습니다.</span>}
        </div>
        <div className="flex gap-2">
          <Button type="button" disabled={botId === null || !systemPrompt.trim() || apply.isPending} onClick={() => setIsOpen(true)}>
            {apply.isPending && <Loader2 className="animate-spin" />}
            봇에 적용
          </Button>
        </div>
      </div>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>봇에 지침 적용</DialogTitle>
            <DialogDescription>이 봇의 기존 지침을 덮어씁니다. 계속할까요?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)} disabled={apply.isPending}>취소</Button>
            <Button type="button" onClick={confirmApply} disabled={apply.isPending}>
              {apply.isPending && <Loader2 className="animate-spin" />}
              적용
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
