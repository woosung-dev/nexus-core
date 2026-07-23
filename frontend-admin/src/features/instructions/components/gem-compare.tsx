"use client"

// Gems 비교 탭 — 봇·질문 공유, 열마다 시스템 프롬프트·모델로 동시(병렬) 응답 비교(무상태).
import * as React from "react"
import { FolderOpen, Loader2, Plus, RotateCcw, Send, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { MessageCitations } from "@/features/chats/components/MessageCitations"
import { MessageFollowups } from "@/features/chats/components/MessageFollowups"
import { useBots } from "@/features/bots/hooks"
import { previewInstruction } from "../api"
import { useInstructions } from "../hooks"
import { LLM_MODEL_OPTIONS } from "../schemas"
import type { Citation } from "../types"
import { GemPickerDialog } from "./gem-picker-dialog"

const MAX_COLUMNS = 6
const ALPHABET = "ABCDEFGH"

type ColCell = {
  status: "loading" | "done" | "error"
  answer?: string
  citations?: Citation[]
  followups?: string[]
}
type Column = {
  id: string
  system_prompt: string
  llm_model: string
  gemId: number | null
}
type Run = {
  id: number
  question: string
  cells: Record<string, ColCell>
}

let columnSeq = 0
function newColumn(): Column {
  columnSeq += 1
  return { id: `col-${columnSeq}`, system_prompt: "", llm_model: "gemini-2.5-flash", gemId: null }
}

export function GemCompare() {
  const { data: botData } = useBots()
  const bots = React.useMemo(
    () => (botData?.bots ?? []).map((b) => ({ id: Number(b.id), name: b.name })),
    [botData]
  )
  const { data: gemData } = useInstructions()
  const gems = gemData?.instructions ?? []

  const [columns, setColumns] = React.useState<Column[]>(() => [newColumn(), newColumn()])
  const [botId, setBotId] = React.useState<number | null>(null)
  const [useRag, setUseRag] = React.useState(true)
  const [question, setQuestion] = React.useState("")
  const [runs, setRuns] = React.useState<Run[]>([])
  const [pickerColId, setPickerColId] = React.useState<string | null>(null)
  const runSeq = React.useRef(0)

  const pending = runs.some((r) => Object.values(r.cells).some((c) => c.status === "loading"))

  function updateColumn(id: string, patch: Partial<Column>) {
    setColumns((cols) => cols.map((c) => (c.id === id ? { ...c, ...patch } : c)))
  }
  function loadGem(id: string, gemId: number) {
    const gem = gems.find((g) => g.id === gemId)
    if (!gem) return
    updateColumn(id, { gemId, system_prompt: gem.system_prompt, llm_model: gem.llm_model })
  }
  function addColumn() {
    setColumns((cols) => (cols.length >= MAX_COLUMNS ? cols : [...cols, newColumn()]))
  }
  function removeColumn(id: string) {
    setColumns((cols) => (cols.length <= 1 ? cols : cols.filter((c) => c.id !== id)))
  }

  function runAll() {
    const q = question.trim()
    if (!q || pending || columns.length === 0) return
    setQuestion("")
    runSeq.current += 1
    const runId = runSeq.current
    const cols = columns
    setRuns((prev) => [
      ...prev,
      { id: runId, question: q, cells: Object.fromEntries(cols.map((c) => [c.id, { status: "loading" as const }])) },
    ])
    cols.forEach((col) => {
      previewInstruction({
        system_prompt: col.system_prompt,
        message: q,
        bot_id: botId,
        use_rag: useRag,
        llm_model: col.llm_model,
      })
        .then((res) =>
          setRuns((prev) =>
            prev.map((r) =>
              r.id === runId
                ? { ...r, cells: { ...r.cells, [col.id]: { status: "done", answer: res.answer, citations: res.citations, followups: res.followups } } }
                : r
            )
          )
        )
        .catch(() =>
          setRuns((prev) =>
            prev.map((r) => (r.id === runId ? { ...r, cells: { ...r.cells, [col.id]: { status: "error" } } } : r))
          )
        )
    })
  }

  const columnHeight = "h-[58vh] lg:h-[calc(100vh-22rem)]"

  return (
    <div className="flex flex-col gap-4">
      {/* 상단 공용 입력 바 — 질문을 한 번 입력하면 아래 모든 열이 동시 응답 */}
      <div className="sticky top-0 z-10 flex flex-col gap-3 rounded-lg border bg-background/95 p-3 shadow-sm backdrop-blur">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="compare-bot" className="shrink-0">봇 (RAG 지식)</Label>
            <Select value={botId === null ? "none" : String(botId)} onValueChange={(v) => setBotId(v === "none" ? null : Number(v))}>
              <SelectTrigger id="compare-bot" className="w-48" aria-label="봇 선택">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">봇 없음 (LLM만)</SelectItem>
                {bots.map((bot) => (
                  <SelectItem key={bot.id} value={String(bot.id)}>{bot.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Switch id="compare-rag" checked={useRag} onCheckedChange={setUseRag} />
            <Label htmlFor="compare-rag">RAG 사용</Label>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button type="button" variant="ghost" size="sm" disabled={runs.length === 0} onClick={() => setRuns([])}>
              <RotateCcw />결과 초기화
            </Button>
            <Button type="button" variant="outline" size="sm" disabled={columns.length >= MAX_COLUMNS} onClick={addColumn}>
              <Plus />열 추가
            </Button>
          </div>
        </div>
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            runAll()
          }}
        >
          <div className="min-w-0 flex-1 space-y-1">
            <Label htmlFor="compare-message" className="text-xs text-muted-foreground">비교 질문 — 한 번 입력하면 아래 모든 열이 동시에 답합니다 (대화 기록 없음)</Label>
            <Input id="compare-message" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="비교할 질문을 입력하세요" disabled={pending} />
          </div>
          <Button type="submit" disabled={pending || !question.trim()}>
            {pending ? <Loader2 className="animate-spin" /> : <Send />}전송
          </Button>
        </form>
      </div>

      {/* 비교 열 (가로 스크롤) */}
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-4">
          {columns.map((col, index) => {
            const loadedGem = col.gemId === null ? null : gems.find((g) => g.id === col.gemId)
            return (
              <div key={col.id} className={cnCol(columnHeight)}>
                {/* 열 헤더 */}
                <div className="flex items-center gap-2 border-b p-2">
                  <Badge variant="secondary" className="size-6 justify-center p-0 text-xs">{ALPHABET[index] ?? index + 1}</Badge>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 flex-1 justify-start gap-1.5 truncate text-xs font-normal"
                    onClick={() => setPickerColId(col.id)}
                  >
                    <FolderOpen className="shrink-0" />
                    <span className="truncate">{loadedGem ? loadedGem.name : "Gem 불러오기"}</span>
                  </Button>
                  <Button type="button" variant="ghost" size="icon" className="size-8" disabled={columns.length <= 1} onClick={() => removeColumn(col.id)} aria-label="열 삭제">
                    <X />
                  </Button>
                </div>

                {/* 프롬프트 + 모델 */}
                <div className="space-y-2 border-b p-2">
                  <Select value={col.llm_model} onValueChange={(v) => updateColumn(col.id, { llm_model: v, gemId: null })}>
                    <SelectTrigger className="h-8 text-xs" aria-label="모델">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LLM_MODEL_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Textarea
                    className="field-sizing-fixed h-[140px] resize-y overflow-y-auto text-xs leading-relaxed"
                    placeholder="이 열의 시스템 프롬프트를 입력하거나 위 'Gem 불러오기'로 채우세요."
                    value={col.system_prompt}
                    onChange={(e) => updateColumn(col.id, { system_prompt: e.target.value, gemId: null })}
                  />
                </div>

                {/* 응답 스레드 */}
                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-muted/20 p-2">
                  {runs.length === 0 && (
                    <p className="px-1 pt-2 text-xs text-muted-foreground">위에 질문을 입력하면 여기에 답변이 나와요.</p>
                  )}
                  {runs.map((run) => {
                    const cell = run.cells[col.id]
                    return (
                      <div key={run.id} className="space-y-1.5">
                        <p className="ml-auto w-fit max-w-[90%] rounded-lg bg-primary px-2.5 py-1 text-xs text-primary-foreground">{run.question}</p>
                        {!cell ? (
                          <p className="text-xs text-muted-foreground">—</p>
                        ) : cell.status === "loading" ? (
                          <p className="flex items-center gap-1.5 rounded-lg border bg-background px-2.5 py-1.5 text-xs text-muted-foreground">
                            <Loader2 className="size-3.5 animate-spin" />생성 중…
                          </p>
                        ) : cell.status === "error" ? (
                          <p className="rounded-lg border bg-background px-2.5 py-1.5 text-xs text-destructive">응답 생성 실패</p>
                        ) : (
                          <div className="rounded-lg border bg-background px-2.5 py-1.5 text-xs">
                            <p className="whitespace-pre-wrap leading-relaxed">{cell.answer}</p>
                            <MessageCitations citations={cell.citations} />
                            <MessageFollowups items={cell.followups} />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Gem 불러오기 모달 — 저장된 Gem을 골라 그 열 프롬프트·모델에 적용 */}
      <GemPickerDialog
        open={pickerColId !== null}
        onOpenChange={(open) => !open && setPickerColId(null)}
        gems={gems}
        onSelect={(gem) => {
          if (pickerColId) loadGem(pickerColId, gem.id)
        }}
        description="이 열에 적용할 Gem을 선택하세요. 선택한 Gem의 프롬프트와 모델이 채워집니다."
      />
    </div>
  )
}

function cnCol(height: string) {
  // 모바일에선 다음 열이 살짝 보이게 80vw(스크롤 힌트), sm 이상은 고정 340px.
  return `flex w-[80vw] max-w-[380px] shrink-0 flex-col overflow-hidden rounded-lg border sm:w-[340px] ${height}`
}
