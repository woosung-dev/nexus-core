"use client"

// 프롬프트 생성 탭 — 생성기 Gem을 엔진으로, 사용 목적을 넣어 시스템 프롬프트를 만들어 낸다.
import * as React from "react"
import { Check, Copy, Loader2, RefreshCw, Save, Sparkles, Wand2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { previewInstruction } from "../api"
import { useCreateInstruction, useInstructions } from "../hooks"
import { LLM_MODEL_OPTIONS } from "../schemas"
import type { BotInstruction } from "../types"
import { GemPickerDialog } from "./gem-picker-dialog"

const PURPOSE_PLACEHOLDER =
  "예: 축복·가정관리 규정을 안내하는 상담 챗봇을 만들고 싶어요. 주 사용자는 부모 세대 실무자이고, 공식 문서를 근거로만 답해야 해요. 따뜻하되 단정하지 않는 말투로, 확실하지 않으면 담당자 확인을 안내해 주세요."

export function GemGenerate() {
  const { data: gemData } = useInstructions()
  const gems = React.useMemo(
    () => (gemData?.instructions ?? []).filter((gem) => gem.system_prompt.trim().length > 0),
    [gemData]
  )
  const createGem = useCreateInstruction()

  const [generator, setGenerator] = React.useState<BotInstruction | null>(null)
  const [pickerOpen, setPickerOpen] = React.useState(false)
  const [model, setModel] = React.useState("gemini-2.5-flash")
  const [purpose, setPurpose] = React.useState("")

  const [result, setResult] = React.useState<string | null>(null)
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [genError, setGenError] = React.useState(false)

  const [copied, setCopied] = React.useState(false)
  const [savedMsg, setSavedMsg] = React.useState(false)
  const [saveOpen, setSaveOpen] = React.useState(false)
  const [saveName, setSaveName] = React.useState("")
  const [saveDesc, setSaveDesc] = React.useState("")
  const copyTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const savedTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(
    () => () => {
      if (copyTimer.current) clearTimeout(copyTimer.current)
      if (savedTimer.current) clearTimeout(savedTimer.current)
    },
    []
  )

  const canGenerate = generator !== null && purpose.trim().length > 0 && !isGenerating
  const blockedReason =
    generator === null ? "생성기 Gem을 먼저 선택하세요." : purpose.trim() ? null : "만들고 싶은 챗봇의 목적을 입력하세요."

  async function generate() {
    if (!generator || !purpose.trim() || isGenerating) return
    setIsGenerating(true)
    setGenError(false)
    try {
      const res = await previewInstruction({
        system_prompt: generator.system_prompt,
        message: purpose.trim(),
        bot_id: null,
        use_rag: false,
        llm_model: model,
      })
      setResult(res.answer)
    } catch {
      setGenError(true)
    } finally {
      setIsGenerating(false)
    }
  }

  async function copyResult() {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result)
      setCopied(true)
      if (copyTimer.current) clearTimeout(copyTimer.current)
      copyTimer.current = setTimeout(() => setCopied(false), 3000)
    } catch {
      // 클립보드 권한이 없으면 조용히 무시 — 사용자가 직접 선택해 복사할 수 있다.
    }
  }

  function saveAsGem() {
    if (!result || !saveName.trim()) return
    createGem.mutate(
      {
        name: saveName.trim(),
        description: saveDesc.trim(),
        system_prompt: result,
        llm_model: model,
      },
      {
        onSuccess: () => {
          setSaveOpen(false)
          setSavedMsg(true)
          if (savedTimer.current) clearTimeout(savedTimer.current)
          savedTimer.current = setTimeout(() => setSavedMsg(false), 4000)
        },
      }
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)]">
      {/* 좌: 입력 */}
      <div className="flex flex-col gap-5 rounded-lg border p-4">
        {/* 생성기 Gem */}
        <div className="space-y-1.5">
          <Label>생성기 Gem</Label>
          <p className="text-xs text-muted-foreground">시스템 프롬프트를 작성해 주는 역할의 Gem을 고르세요.</p>
          {generator ? (
            <div className="flex items-start gap-2 rounded-md border p-3">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="line-clamp-1 text-sm font-medium">{generator.name || "(제목 없음)"}</p>
                {generator.description && (
                  <p className="line-clamp-2 text-xs text-muted-foreground">{generator.description}</p>
                )}
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => setPickerOpen(true)}>변경</Button>
            </div>
          ) : (
            <Button type="button" variant="outline" className="w-full justify-start" onClick={() => setPickerOpen(true)}>
              <Sparkles />생성기 Gem 선택
            </Button>
          )}
        </div>

        {/* 모델 */}
        <div className="space-y-1.5">
          <Label htmlFor="gen-model">모델</Label>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger id="gen-model" aria-label="모델">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LLM_MODEL_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 목적·요구사항 */}
        <div className="space-y-1.5">
          <Label htmlFor="gen-purpose">목적·요구사항</Label>
          <p className="text-xs text-muted-foreground">어떤 챗봇인지, 누가 쓰는지, 말투, 답변 범위, 하지 말아야 할 것을 자유롭게 적어주세요.</p>
          <Textarea
            id="gen-purpose"
            className="field-sizing-fixed h-[220px] resize-y overflow-y-auto text-sm leading-relaxed"
            placeholder={PURPOSE_PLACEHOLDER}
            value={purpose}
            onChange={(event) => setPurpose(event.target.value)}
          />
          <span className="text-xs text-muted-foreground">{purpose.length.toLocaleString()}자</span>
        </div>

        <div className="space-y-1.5">
          <Button type="button" className="w-full" disabled={!canGenerate} onClick={generate}>
            {isGenerating ? <Loader2 className="animate-spin" /> : <Wand2 />}
            {isGenerating ? "생성 중…" : "시스템 프롬프트 생성"}
          </Button>
          {blockedReason && !isGenerating && (
            <p className="text-center text-xs text-muted-foreground">{blockedReason}</p>
          )}
        </div>
      </div>

      {/* 우: 결과 */}
      <div className="flex flex-col overflow-hidden rounded-lg border lg:h-[calc(100vh-14rem)]">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <h2 className="text-base font-semibold">생성 결과</h2>
          {result && <span className="text-xs text-muted-foreground">{result.length.toLocaleString()}자</span>}
          {result && !isGenerating && (
            <div className="ml-auto flex flex-wrap items-center gap-2">
              {copied && (
                <span className="text-xs text-primary"><Check className="mr-1 inline size-3.5" />복사됨</span>
              )}
              {savedMsg && (
                <span className="text-xs text-primary"><Check className="mr-1 inline size-3.5" />저장됨 · 빌더에서 확인</span>
              )}
              <Button type="button" variant="ghost" size="sm" onClick={copyResult}>
                <Copy />복사
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSaveName("")
                  setSaveDesc("")
                  setSaveOpen(true)
                }}
              >
                <Save />새 Gem으로 저장
              </Button>
              <Button type="button" variant="outline" size="sm" disabled={!canGenerate} onClick={generate}>
                <RefreshCw />다시 생성
              </Button>
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4" aria-live="polite">
          {isGenerating ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                <Loader2 className="mr-2 inline size-4 animate-spin" />생성 중… 최대 30초 걸릴 수 있어요.
              </p>
              <div className="space-y-2 motion-safe:animate-pulse">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className={cn("h-4", i % 3 === 2 ? "w-2/3" : "w-full")} />
                ))}
              </div>
            </div>
          ) : genError ? (
            <div className="space-y-3">
              <p className="text-sm text-destructive">생성에 실패했습니다. 잠시 후 다시 시도해 주세요.</p>
              <Button type="button" variant="outline" size="sm" disabled={!canGenerate} onClick={generate}>
                <RefreshCw />다시 시도
              </Button>
            </div>
          ) : result ? (
            <p className="max-w-[70ch] whitespace-pre-wrap text-sm leading-relaxed">{result}</p>
          ) : (
            <div className="flex h-full min-h-60 items-center justify-center rounded-lg border-2 border-dashed p-8 text-center text-sm text-muted-foreground">
              왼쪽에서 생성기 Gem과 목적을 입력하고 &lsquo;시스템 프롬프트 생성&rsquo;을 눌러보세요.
            </div>
          )}
        </div>
      </div>

      <GemPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        gems={gems}
        onSelect={(gem) => setGenerator(gem)}
        title="생성기 Gem 선택"
        description="시스템 프롬프트를 작성해 주는 역할의 Gem을 고르세요."
      />

      {/* 새 Gem으로 저장 */}
      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>새 Gem으로 저장</DialogTitle>
            <DialogDescription>생성된 시스템 프롬프트를 새 Gem으로 저장합니다. 빌더 탭에서 이어서 편집할 수 있어요.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="save-gem-name">이름</Label>
              <Input
                id="save-gem-name"
                value={saveName}
                onChange={(event) => setSaveName(event.target.value)}
                placeholder="Gem의 이름을 지정하세요."
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="save-gem-desc">설명 (선택)</Label>
              <Input
                id="save-gem-desc"
                value={saveDesc}
                onChange={(event) => setSaveDesc(event.target.value)}
                placeholder="어떤 Gem인지 간단히 적어주세요."
              />
            </div>
            {createGem.isError && <p className="text-xs text-destructive">저장에 실패했습니다.</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setSaveOpen(false)} disabled={createGem.isPending}>
              취소
            </Button>
            <Button type="button" onClick={saveAsGem} disabled={!saveName.trim() || createGem.isPending}>
              {createGem.isPending && <Loader2 className="animate-spin" />}저장
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
