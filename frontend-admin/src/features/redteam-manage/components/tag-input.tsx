"use client"

// 피드백 유형 태그 입력 — 프리셋 제안(datalist) + 자유 추가, 칩 제거.
import * as React from "react"
import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { useManageTags } from "../hooks"

export function TagInput({
  tags,
  onChange,
  disabled,
}: {
  tags: string[]
  onChange: (next: string[]) => void
  disabled?: boolean
}) {
  const { data: suggestions } = useManageTags()
  const [draft, setDraft] = React.useState("")
  const listId = React.useId()

  const add = (raw: string) => {
    const v = raw.trim()
    if (!v || tags.includes(v)) {
      setDraft("")
      return
    }
    onChange([...tags, v])
    setDraft("")
  }

  const remove = (t: string) => onChange(tags.filter((x) => x !== t))

  const unusedPresets = (suggestions ?? []).filter((s) => !tags.includes(s)).slice(0, 8)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1.5">
        {tags.length === 0 && (
          <span className="text-xs text-muted-foreground">태그 없음</span>
        )}
        {tags.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1 rounded-md border bg-secondary/60 px-2 py-0.5 text-xs"
          >
            #{t}
            {!disabled && (
              <button
                type="button"
                onClick={() => remove(t)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={`${t} 태그 제거`}
              >
                <X className="size-3" />
              </button>
            )}
          </span>
        ))}
      </div>

      {!disabled && (
        <>
          <div className="flex items-center gap-2">
            <Input
              value={draft}
              list={listId}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  add(draft)
                }
              }}
              placeholder="태그 입력 후 Enter (프리셋 제안 또는 자유 추가)"
              className="h-8 text-xs"
            />
            <datalist id={listId}>
              {(suggestions ?? []).map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 shrink-0 px-2"
              onClick={() => add(draft)}
              disabled={!draft.trim()}
            >
              <Plus className="size-3" /> 추가
            </Button>
          </div>

          {unusedPresets.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {unusedPresets.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => add(s)}
                  className={cn(
                    "rounded-md border border-dashed px-1.5 py-0.5 text-[10px] text-muted-foreground",
                    "hover:border-solid hover:bg-secondary/60 hover:text-foreground"
                  )}
                >
                  + {s}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
