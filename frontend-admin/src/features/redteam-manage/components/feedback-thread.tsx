"use client"

// 담당자 피드백 코멘트 스레드 — 여러 담당자가 각자 의견을 남김(작성자·내용·시각), 추가/삭제.
import * as React from "react"
import { Loader2, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { AVATAR_COLORS, FEEDBACK_AUTHORS } from "../constants"
import { useAddFeedback, useDeleteFeedback } from "../hooks"
import type { ManageFeedbackItem } from "../types"

const CUSTOM = "__custom__"

function colorFor(name: string): string {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

function relTime(iso: string | null): string {
  if (!iso) return ""
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ""
  const diff = (Date.now() - t) / 1000
  if (diff < 60) return "방금"
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return new Date(t).toLocaleDateString("ko-KR", { month: "2-digit", day: "2-digit" })
}

function Avatar({ name }: { name: string }) {
  return (
    <span
      className="flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
      style={{ background: colorFor(name) }}
    >
      {name.slice(0, 1)}
    </span>
  )
}

export function FeedbackThread({
  groupId,
  feedback,
}: {
  groupId: number
  feedback: ManageFeedbackItem[]
}) {
  const add = useAddFeedback(groupId)
  const del = useDeleteFeedback(groupId)

  const [authorSel, setAuthorSel] = React.useState<string>(FEEDBACK_AUTHORS[0])
  const [customName, setCustomName] = React.useState("")
  const [content, setContent] = React.useState("")

  const author = authorSel === CUSTOM ? customName.trim() : authorSel
  const canSubmit = author.length > 0 && content.trim().length > 0 && !add.isPending

  const submit = () => {
    if (!canSubmit) return
    add.mutate(
      { author, content: content.trim() },
      { onSuccess: () => setContent("") }
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">담당자 피드백</h3>
        <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-semibold text-primary-foreground">
          {feedback.length}
        </span>
        <span className="ml-auto text-[11px] text-muted-foreground">
          여러 담당자가 각자 의견을 남깁니다 (최대 3명 권장)
        </span>
      </div>

      {/* 목록 */}
      {feedback.length === 0 ? (
        <p className="text-xs text-muted-foreground">아직 등록된 피드백이 없습니다.</p>
      ) : (
        <ul className="flex flex-col">
          {feedback.map((f) => (
            <li key={f.id} className="group flex gap-3 border-b py-3 last:border-b-0">
              <Avatar name={f.author} />
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="text-sm font-semibold">{f.author}</span>
                  <span className="rtm-mono text-[11px] text-muted-foreground">
                    {relTime(f.created_at)}
                  </span>
                  <button
                    type="button"
                    onClick={() => del.mutate(f.id)}
                    disabled={del.isPending}
                    className="ml-auto text-muted-foreground/40 opacity-0 transition group-hover:opacity-100 hover:text-destructive"
                    aria-label="피드백 삭제"
                    title="삭제"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
                  {f.content}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* 작성 */}
      <div className="flex flex-col gap-2 rounded-md border bg-muted/30 p-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted-foreground">작성자</span>
          <Select value={authorSel} onValueChange={setAuthorSel}>
            <SelectTrigger className="h-7 w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FEEDBACK_AUTHORS.map((a) => (
                <SelectItem key={a} value={a}>
                  {a}
                </SelectItem>
              ))}
              <SelectItem value={CUSTOM}>직접 입력…</SelectItem>
            </SelectContent>
          </Select>
          {authorSel === CUSTOM && (
            <Input
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="담당자 이름"
              className="h-7 w-32 text-xs"
            />
          )}
        </div>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder="피드백을 입력하세요... (⌘/Ctrl+Enter 로 추가)"
          className="min-h-20 text-sm"
        />
        <div className="flex items-center gap-2">
          <Button size="sm" className="h-8" disabled={!canSubmit} onClick={submit}>
            {add.isPending ? (
              <Loader2 className="size-3 animate-spin" />
            ) : (
              <Plus className="size-3" />
            )}
            피드백 추가
          </Button>
          <span className={cn("text-[11px] text-muted-foreground", canSubmit && "invisible")}>
            작성자·내용을 입력하세요.
          </span>
        </div>
      </div>
    </div>
  )
}
