"use client"

// Gems 빌더 탭 — 갤러리(좌) + 편집기(우) 2-pane.
import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { gemSchema, type GemValues } from "@/features/instructions/schemas"
import {
  useCreateInstruction,
  useDeleteInstruction,
  useInstructions,
  useUpdateGem,
} from "@/features/instructions/hooks"
import { GemList } from "@/features/instructions/components/gem-list"
import { GemEditor } from "@/features/instructions/components/gem-editor"
import type { BotInstruction } from "@/features/instructions/types"

const EMPTY: GemValues = {
  name: "",
  description: "",
  system_prompt: "",
  llm_model: "gemini-2.5-flash",
}

function toValues(gem: BotInstruction): GemValues {
  return {
    name: gem.name,
    description: gem.description,
    system_prompt: gem.system_prompt,
    llm_model: gem.llm_model,
  }
}

type Selection = number | "new" | null

export function GemBuilder() {
  const form = useForm<GemValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 resolver의 타입 정의 차이.
    resolver: zodResolver(gemSchema as any),
    defaultValues: EMPTY,
    mode: "onChange",
  })

  const { data: gemData, isLoading } = useInstructions()
  const gems = React.useMemo(() => gemData?.instructions ?? [], [gemData])

  const [selectedId, setSelectedId] = React.useState<Selection>(null)
  const [mobileView, setMobileView] = React.useState<"list" | "edit">("list")
  const [pendingSelect, setPendingSelect] = React.useState<Selection>(null)

  const create = useCreateInstruction()
  const updateGem = useUpdateGem()
  const del = useDeleteInstruction()

  const mode: "new" | "edit" = typeof selectedId === "number" ? "edit" : "new"

  function loadSelection(target: Selection) {
    setSelectedId(target)
    if (typeof target === "number") {
      const gem = gems.find((g) => g.id === target)
      form.reset(gem ? toValues(gem) : EMPTY)
    } else {
      form.reset(EMPTY)
    }
    setMobileView("edit")
  }

  function requestSelect(target: Selection) {
    if (target === selectedId) { setMobileView("edit"); return }
    if (form.formState.isDirty) { setPendingSelect(target); return }
    loadSelection(target)
  }

  const onSave = form.handleSubmit((v) => {
    const body = {
      name: v.name,
      description: v.description,
      system_prompt: v.system_prompt,
      llm_model: v.llm_model,
    }
    if (mode === "new") {
      create.mutate(body, {
        onSuccess: (gem) => { setSelectedId(gem.id); form.reset(toValues(gem)) },
      })
    } else if (typeof selectedId === "number") {
      updateGem.mutate({ id: selectedId, body }, { onSuccess: (gem) => form.reset(toValues(gem)) })
    }
  })

  function handleDelete() {
    if (typeof selectedId !== "number") return
    del.mutate(selectedId, {
      onSuccess: () => { setSelectedId(null); form.reset(EMPTY); setMobileView("list") },
    })
  }

  const paneHeight = "h-[70vh] lg:h-[calc(100vh-14rem)]"

  return (
    <div className="flex flex-col gap-4">
      {/* 모바일 세그먼트 토글 */}
      <div className="grid grid-cols-2 rounded-md border p-1 lg:hidden">
        {(["list", "edit"] as const).map((v) => (
          <Button
            key={v}
            type="button"
            variant="ghost"
            onClick={() => setMobileView(v)}
            className={cn("rounded px-3 py-2 text-sm font-medium", mobileView === v && "bg-muted")}
          >
            {v === "list" ? "목록" : "편집"}
          </Button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)]">
        {/* 좌: 갤러리 */}
        <div className={cn("overflow-hidden rounded-lg border", paneHeight, mobileView !== "list" && "hidden lg:block")}>
          <GemList
            gems={gems}
            isLoading={isLoading}
            selectedId={selectedId}
            onSelect={requestSelect}
            onNew={() => requestSelect("new")}
          />
        </div>

        {/* 우: 편집기 */}
        <div className={cn("overflow-hidden rounded-lg border", paneHeight, mobileView !== "edit" && "hidden lg:block")}>
          {selectedId === null ? (
            <div className="flex h-full min-h-80 items-center justify-center p-8 text-center text-sm text-muted-foreground">
              왼쪽에서 Gem을 선택하거나 &lsquo;새 Gem&rsquo;으로 새로 만드세요.
            </div>
          ) : (
            <GemEditor
              form={form}
              mode={mode}
              currentGemId={typeof selectedId === "number" ? selectedId : null}
              onSave={() => onSave()}
              isSaving={create.isPending || updateGem.isPending}
              saveError={create.isError || updateGem.isError}
              onDelete={handleDelete}
              isDeleting={del.isPending}
            />
          )}
        </div>
      </div>

      {/* 미저장 이동 가드 */}
      <Dialog open={pendingSelect !== null} onOpenChange={(open) => !open && setPendingSelect(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>저장하지 않은 변경사항</DialogTitle>
            <DialogDescription>편집 중인 내용이 저장되지 않았습니다. 버리고 이동할까요?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPendingSelect(null)}>취소</Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                const target = pendingSelect
                setPendingSelect(null)
                if (target !== null) loadSelection(target)
              }}
            >
              버리고 이동
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
