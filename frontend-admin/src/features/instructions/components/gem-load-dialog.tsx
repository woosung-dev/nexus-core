"use client"

// 비교 탭 전용 Gem 불러오기 — Gem을 골라 원문 그대로 넣거나, 생성기로 삼아 프롬프트를 만들어 열에 적용하는 2단계 모달.
import * as React from "react"
import { ArrowLeft, Loader2, RefreshCw, Sparkles, Wand2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { previewInstruction } from "../api"
import type { BotInstruction } from "../types"

type ApplyPatch = {
  system_prompt: string
  llm_model?: string
  gemId: number | null
}

type GemLoadDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  gems: BotInstruction[]
  onApply: (patch: ApplyPatch) => void
}

const PURPOSE_PLACEHOLDER =
  "예: 이 열에서 비교할 페르소나를 만들어 주세요. 어떤 챗봇인지, 누가 쓰는지, 말투, 답변 범위, 하지 말아야 할 것을 자유롭게 적어주세요."

export function GemLoadDialog({ open, onOpenChange, gems, onApply }: GemLoadDialogProps) {
  // 생성기든 페르소나든 프롬프트가 비어 있으면 쓸 수 없으므로 걸러 낸다.
  const usableGems = React.useMemo(
    () => gems.filter((gem) => gem.system_prompt.trim().length > 0),
    [gems]
  )

  const [selected, setSelected] = React.useState<BotInstruction | null>(null)
  const [purpose, setPurpose] = React.useState("")
  const [result, setResult] = React.useState<string | null>(null)
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [genError, setGenError] = React.useState(false)

  // 모달이 닫히면 내부 상태 초기화 — 다음 열에서 새로 시작한다.
  React.useEffect(() => {
    if (open) return
    setSelected(null)
    setPurpose("")
    setResult(null)
    setIsGenerating(false)
    setGenError(false)
  }, [open])

  function pick(gem: BotInstruction) {
    setSelected(gem)
    setResult(null)
    setGenError(false)
  }

  async function generate() {
    if (!selected || !purpose.trim() || isGenerating) return
    setIsGenerating(true)
    setGenError(false)
    try {
      const res = await previewInstruction({
        system_prompt: selected.system_prompt,
        message: purpose.trim(),
        bot_id: null,
        use_rag: false,
        llm_model: selected.llm_model,
      })
      setResult(res.answer)
    } catch {
      setGenError(true)
    } finally {
      setIsGenerating(false)
    }
  }

  function applyGenerated() {
    if (!result) return
    onApply({ system_prompt: result, gemId: null })
    onOpenChange(false)
  }

  function applyRaw() {
    if (!selected) return
    onApply({ system_prompt: selected.system_prompt, llm_model: selected.llm_model, gemId: selected.id })
    onOpenChange(false)
  }

  const canGenerate = selected !== null && purpose.trim().length > 0 && !isGenerating

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        {selected === null ? (
          // 1단계 — Gem 선택
          <>
            <DialogHeader>
              <DialogTitle>Gem 불러오기</DialogTitle>
              <DialogDescription>
                이 열에 적용할 Gem을 선택하세요. 다음 단계에서 그대로 넣거나, 이 Gem으로 프롬프트를 생성할 수 있어요.
              </DialogDescription>
            </DialogHeader>
            {usableGems.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                저장된 Gem이 없어요. 먼저 빌더 탭에서 만들어 주세요.
              </p>
            ) : (
              <ul className="max-h-[50vh] divide-y overflow-y-auto">
                {usableGems.map((gem) => (
                  <li key={gem.id}>
                    <button
                      type="button"
                      className="flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-accent/50"
                      onClick={() => pick(gem)}
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
          </>
        ) : (
          // 2단계 — 구성 (생성 또는 원문 그대로)
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7 shrink-0"
                  onClick={() => setSelected(null)}
                  aria-label="다른 Gem 선택"
                >
                  <ArrowLeft />
                </Button>
                <DialogTitle className="min-w-0 truncate">{selected.name || "(제목 없음)"}</DialogTitle>
              </div>
              <DialogDescription>
                이 Gem을 생성기로 삼아 필요한 내용을 적으면, 프롬프트가 만들어져 이 열에 채워집니다.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* 요청 입력 → 생성 */}
              <div className="space-y-1.5">
                <Label htmlFor="gem-load-purpose">요청 내용</Label>
                <Textarea
                  id="gem-load-purpose"
                  className="field-sizing-fixed h-[140px] resize-y overflow-y-auto text-sm leading-relaxed"
                  placeholder={PURPOSE_PLACEHOLDER}
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{purpose.length.toLocaleString()}자</span>
                  <Button type="button" size="sm" disabled={!canGenerate} onClick={generate}>
                    {isGenerating ? <Loader2 className="animate-spin" /> : <Wand2 />}
                    {isGenerating ? "생성 중…" : result ? "다시 생성" : "생성"}
                  </Button>
                </div>
              </div>

              {/* 생성 결과 미리보기 */}
              <div className="space-y-1.5">
                <Label>생성 결과 미리보기</Label>
                <div
                  className="max-h-[34vh] min-h-[120px] overflow-y-auto rounded-md border bg-muted/20 p-3"
                  aria-live="polite"
                >
                  {isGenerating ? (
                    <div className="space-y-2 motion-safe:animate-pulse">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className={cn("h-4", i % 3 === 2 ? "w-2/3" : "w-full")} />
                      ))}
                    </div>
                  ) : genError ? (
                    <div className="space-y-2">
                      <p className="text-sm text-destructive">생성에 실패했습니다. 잠시 후 다시 시도해 주세요.</p>
                      <Button type="button" variant="outline" size="sm" disabled={!canGenerate} onClick={generate}>
                        <RefreshCw />다시 시도
                      </Button>
                    </div>
                  ) : result ? (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{result}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      위에 요청 내용을 적고 &lsquo;생성&rsquo;을 누르면 여기에 미리보기가 나와요.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* 적용 액션 — 주: 생성 결과 반영 / 보조: 원문 그대로 */}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
              <Button type="button" variant="ghost" size="sm" className="text-muted-foreground" onClick={applyRaw}>
                생성 없이 이 Gem 원문 그대로 넣기
              </Button>
              <Button type="button" disabled={!result} onClick={applyGenerated}>
                <Sparkles />이 열에 적용
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
