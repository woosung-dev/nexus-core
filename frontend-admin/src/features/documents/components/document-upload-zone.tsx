"use client"

/**
 * 문서 파일 업로드 영역 컴포넌트.
 * Drag & Drop 또는 버튼 클릭으로 파일을 선택하고 업로드한다.
 * react-hook-form + zod로 파일 검증을 처리한다.
 */
import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { CloudUpload, FileText, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form"
import { useUploadDocument } from "@/features/documents/hooks"
import {
  uploadFormSchema,
  type UploadFormValues,
  ALLOWED_EXTENSIONS_LABEL,
} from "@/features/documents/schemas"

interface DocumentUploadZoneProps {
  botId: number
}

export function DocumentUploadZone({ botId }: DocumentUploadZoneProps) {
  const [isDragging, setIsDragging] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)
  const { mutate: uploadDoc, isPending } = useUploadDocument(botId)

  const form = useForm<UploadFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈
    resolver: zodResolver(uploadFormSchema as any),
  })

  // 파일 제출
  function onSubmit(values: UploadFormValues) {
    uploadDoc(values.file, {
      onSuccess: () => form.reset(),
    })
  }

  // 파일 선택 처리 (input 및 Drag & Drop 공용)
  function handleFileSelect(file: File | undefined) {
    if (!file) return
    form.setValue("file", file, { shouldValidate: true })
    // 유효성 통과 시 즉시 제출
    form.handleSubmit(onSubmit)()
  }

  // Drag & Drop 핸들러
  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }

  const selectedFile = form.watch("file")

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="file"
          render={() => (
            <FormItem>
              <FormControl>
                {/* Drop Zone */}
                <div
                  onClick={() => inputRef.current?.click()}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={[
                    "flex flex-col items-center justify-center gap-3",
                    "rounded-xl border-2 border-dashed p-10 transition-colors cursor-pointer",
                    "text-center select-none",
                    isDragging
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50",
                  ].join(" ")}
                >
                  {/* 파일 선택 input (hidden) */}
                  <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.txt,.csv"
                    onChange={(e) => handleFileSelect(e.target.files?.[0])}
                  />

                  {/* 아이콘 & 안내 문구 */}
                  {isPending ? (
                    <>
                      <Loader2 className="h-10 w-10 animate-spin text-primary" />
                      <p className="text-sm text-muted-foreground">업로드 중...</p>
                    </>
                  ) : selectedFile ? (
                    <>
                      <FileText className="h-10 w-10 text-primary" />
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">{selectedFile.name}</p>
                        <p className="text-xs text-muted-foreground">클릭하거나 다른 파일을 드래그하여 교체</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <CloudUpload className="h-10 w-10 text-muted-foreground/60" />
                      <div className="space-y-1">
                        <p className="text-sm font-medium">
                          파일을 드래그하거나{" "}
                          <span className="text-primary underline underline-offset-2">클릭하여 선택</span>하세요
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {ALLOWED_EXTENSIONS_LABEL} · 최대 20MB
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* 파일이 선택된 경우에만 업로드 버튼 노출 (자동 제출이 실패한 경우 대비) */}
        {selectedFile && !isPending && (
          <div className="mt-3 flex justify-end">
            <Button type="submit" size="sm">업로드</Button>
          </div>
        )}
      </form>
    </Form>
  )
}
