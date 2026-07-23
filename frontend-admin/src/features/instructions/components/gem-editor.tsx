"use client"

// Gem 편집기(중앙) — 이름·설명·봇·모델·요청사항(문서) 입력 + AI 다듬기 + 저장/삭제.
import * as React from "react"
import type { UseFormReturn } from "react-hook-form"
import { Gem, Loader2, Sparkles, Trash2, Undo2, Upload } from "lucide-react"
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
import { Textarea } from "@/components/ui/textarea"
import { LLM_MODEL_OPTIONS, type GemValues } from "../schemas"
import { useGenerateInstruction, useInstructions, usePreviewInstruction } from "../hooks"

const PROMPT_PLACEHOLDER =
  "예: 당신은 축복·가정관리 규정을 안내하는 상담 도우미입니다. 제공된 공식 문서를 근거로만 답하고, 확인되지 않은 내용은 만들어내지 마세요. 존댓말로, 결론을 먼저 제시하세요."

type GemEditorProps = {
  form: UseFormReturn<GemValues>
  mode: "new" | "edit"
  currentGemId: number | null
  onSave: () => void
  isSaving: boolean
  saveError: boolean
  onDelete: () => void
  isDeleting: boolean
}

export function GemEditor({
  form,
  mode,
  currentGemId,
  onSave,
  isSaving,
  saveError,
  onDelete,
  isDeleting,
}: GemEditorProps) {
  const { register, watch, setValue, formState } = form
  const values = watch()
  const generate = useGenerateInstruction()
  const preview = usePreviewInstruction()
  const { data: gemData } = useInstructions()
  // 다듬기 도구로 쓸 수 있는 Gem — 자기 자신과 내용 없는 Gem은 제외.
  const toolGems = (gemData?.instructions ?? []).filter(
    (gem) => gem.id !== currentGemId && gem.system_prompt.trim().length > 0
  )
  const prevPromptRef = React.useRef<string | null>(null)
  const fileRef = React.useRef<HTMLInputElement | null>(null)
  const [confirmDelete, setConfirmDelete] = React.useState(false)
  const [toolGemId, setToolGemId] = React.useState<number | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [uploadError, setUploadError] = React.useState<string | null>(null)
  const refining = generate.isPending || preview.isPending

  function applyPrompt(text: string) {
    prevPromptRef.current = form.getValues("system_prompt")
    setValue("system_prompt", text.trim(), { shouldDirty: true })
  }

  function runWand() {
    const draft = values.system_prompt.trim()
    if (!draft || refining) return
    const tool = toolGemId === null ? null : toolGems.find((gem) => gem.id === toolGemId)

    if (tool) {
      // 선택한 Gem을 '다듬기 도구'로 실행 — 그 Gem의 지침으로 현재 초안을 다듬는다.
      preview.mutate(
        {
          system_prompt: tool.system_prompt,
          message: draft,
          bot_id: null,
          use_rag: false,
          llm_model: values.llm_model,
        },
        { onSuccess: (result) => applyPrompt(result.answer) }
      )
      return
    }
    generate.mutate(
      { mode: "improve", draft, llm_model: values.llm_model },
      { onSuccess: (result) => applyPrompt(result.system_prompt) }
    )
  }

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = "" // 같은 파일 재선택 허용
    if (!file) return
    setUploading(true)
    setUploadError(null)
    try {
      let text: string
      if (file.name.toLowerCase().endsWith(".docx")) {
        const mammoth = await import("mammoth")
        const result = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })
        text = result.value
      } else {
        text = await file.text()
      }
      if (!text.trim()) {
        setUploadError("문서에서 읽을 텍스트가 없습니다.")
        return
      }
      applyPrompt(text)
    } catch {
      setUploadError("문서를 읽지 못했습니다. .docx / .txt / .md 파일을 올려주세요.")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b p-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Gem className="size-4 text-muted-foreground" />
        </div>
        <h2 className="line-clamp-1 text-lg font-semibold">{values.name || (mode === "new" ? "새 Gem" : "(제목 없음)")}</h2>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
        {/* 이름 */}
        <div className="space-y-1.5">
          <Label htmlFor="gem-name">이름</Label>
          <Input id="gem-name" placeholder="Gem의 이름을 지정하세요." aria-invalid={!!formState.errors.name} {...register("name")} />
          {formState.errors.name && (
            <p className="text-xs font-medium text-destructive">{formState.errors.name.message}</p>
          )}
        </div>

        {/* 설명 */}
        <div className="space-y-1.5">
          <Label htmlFor="gem-description">설명</Label>
          <Textarea id="gem-description" className="min-h-[60px] resize-y" placeholder="어떤 Gem이고 무슨 역할을 하는지 설명하세요." {...register("description")} />
        </div>

        {/* 모델 */}
        <div className="space-y-1.5 sm:max-w-xs">
          <Label>모델</Label>
          <Select value={values.llm_model} onValueChange={(val) => setValue("llm_model", val, { shouldDirty: true })}>
            <SelectTrigger aria-label="LLM 모델">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LLM_MODEL_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 요청 사항 (system prompt) */}
        <div className="space-y-1.5">
          <Label htmlFor="gem-instructions">요청 사항</Label>
          <p className="text-xs text-muted-foreground">직접 작성하거나, 문서(.docx/.txt/.md)를 업로드해 채우세요.</p>
          <Textarea
            id="gem-instructions"
            className="field-sizing-fixed h-[320px] resize-y overflow-y-auto text-sm leading-relaxed"
            placeholder={PROMPT_PLACEHOLDER}
            {...register("system_prompt")}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">{values.system_prompt.length.toLocaleString()}자</span>
            <div className="flex flex-wrap items-center gap-2">
              <input ref={fileRef} type="file" accept=".docx,.txt,.md,.markdown" className="hidden" onChange={handleFile} />
              <Button type="button" variant="ghost" size="sm" disabled={uploading} onClick={() => fileRef.current?.click()}>
                {uploading ? <Loader2 className="animate-spin" /> : <Upload />}문서 업로드
              </Button>
              {prevPromptRef.current !== null && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setValue("system_prompt", prevPromptRef.current ?? "", { shouldDirty: true })
                    prevPromptRef.current = null
                  }}
                >
                  <Undo2 />되돌리기
                </Button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Label htmlFor="gem-tool" className="text-xs text-muted-foreground">다듬기 도구</Label>
            <Select
              value={toolGemId === null ? "builtin" : String(toolGemId)}
              onValueChange={(val) => setToolGemId(val === "builtin" ? null : Number(val))}
            >
              <SelectTrigger id="gem-tool" className="h-8 w-44 text-xs" aria-label="다듬기 도구">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="builtin">기본 (내장 규칙)</SelectItem>
                {toolGems.map((gem) => (
                  <SelectItem key={gem.id} value={String(gem.id)}>{gem.name || "(제목 없음)"}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="button" variant="outline" size="sm" disabled={!values.system_prompt.trim() || refining} onClick={runWand}>
              {refining ? <Loader2 className="animate-spin" /> : <Sparkles />}
              AI 다듬기
            </Button>
          </div>

          {uploadError && <p className="text-xs text-destructive">{uploadError}</p>}
          {(generate.isError || preview.isError) && (
            <p className="text-xs text-destructive">다듬기에 실패했습니다. 잠시 후 다시 시도해 주세요.</p>
          )}
        </div>
      </div>

      {/* 액션 바 */}
      <div className="flex flex-wrap items-center gap-2 border-t p-3">
        {mode === "edit" && (
          <Button type="button" variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={isDeleting} onClick={() => setConfirmDelete(true)}>
            {isDeleting ? <Loader2 className="animate-spin" /> : <Trash2 />}삭제
          </Button>
        )}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          {saveError && <span className="text-sm text-destructive">저장 실패</span>}
          <Button type="button" disabled={isSaving} onClick={onSave}>
            {isSaving && <Loader2 className="animate-spin" />}저장
          </Button>
        </div>
      </div>

      {/* 삭제 확인 */}
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Gem 삭제</DialogTitle>
            <DialogDescription>이 Gem을 삭제합니다. 되돌릴 수 없습니다. 계속할까요?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirmDelete(false)} disabled={isDeleting}>취소</Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeleting}
              onClick={() => {
                setConfirmDelete(false)
                onDelete()
              }}
            >
              {isDeleting && <Loader2 className="animate-spin" />}삭제
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
