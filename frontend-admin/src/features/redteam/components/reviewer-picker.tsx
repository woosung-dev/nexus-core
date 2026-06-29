"use client"

// 현재 리뷰어(최대 3명) 선택 + 슬롯 이름 편집 — 인증 없는 admin용 신원 선택기
import * as React from "react"
import { Check, Pencil, UserCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

export function ReviewerPicker({
  names,
  activeIndex,
  onSelect,
  onRename,
}: {
  names: string[]
  activeIndex: number
  onSelect: (index: number) => void
  onRename: (index: number, name: string) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [draft, setDraft] = React.useState<string[]>(names)

  React.useEffect(() => setDraft(names), [names])

  return (
    <div className="flex items-center gap-2">
      <UserCircle className="size-5 text-muted-foreground" />
      <span className="text-sm text-muted-foreground">현재 리뷰어</span>
      <Select value={String(activeIndex)} onValueChange={(v) => onSelect(Number(v))}>
        <SelectTrigger className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {names.map((name, i) => (
            <SelectItem key={i} value={String(i)}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon" title="리뷰어 이름 편집">
            <Pencil className="size-4" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>리뷰어 이름 설정</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-2">
            {draft.map((name, i) => (
              <div key={i} className="flex items-center gap-2">
                <span
                  className={cn(
                    "w-6 shrink-0 text-center text-sm",
                    i === activeIndex && "font-bold text-primary"
                  )}
                >
                  {i + 1}
                </span>
                <Input
                  value={name}
                  onChange={(e) =>
                    setDraft((prev) => prev.map((n, idx) => (idx === i ? e.target.value : n)))
                  }
                  maxLength={20}
                />
              </div>
            ))}
          </div>
          <Button
            onClick={() => {
              draft.forEach((name, i) => {
                const trimmed = name.trim() || `리뷰어 ${i + 1}`
                if (trimmed !== names[i]) onRename(i, trimmed)
              })
              setOpen(false)
            }}
          >
            <Check className="size-4" /> 저장
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  )
}
