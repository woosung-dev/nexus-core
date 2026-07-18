"use client"

// 구조화된 입력으로 봇 지침을 작성하고 즉시 검증하는 관리자 페이지.
import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { BotSelector } from "@/features/documents/components/bot-selector"
import { cn } from "@/lib/utils"
import { ApplyBar } from "@/features/instructions/components/apply-bar"
import { KnowledgeFiles } from "@/features/instructions/components/knowledge-files"
import { StructuredFields } from "@/features/instructions/components/structured-fields"
import { TestPanel } from "@/features/instructions/components/test-panel"
import { WandBar } from "@/features/instructions/components/wand-bar"
import { builderSchema, type BuilderValues } from "@/features/instructions/schemas"

export default function InstructionsPage() {
  const form = useForm<BuilderValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 resolver의 타입 정의 차이.
    resolver: zodResolver(builderSchema as any),
    defaultValues: {
      role: "",
      goal: "",
      tone: "",
      audience: "",
      constraints: "",
      dos: [],
      donts: [],
      examples: [],
      system_prompt: "",
      llm_model: "gemini-2.5-flash",
    },
  })
  const values = form.watch()
  const [selectedBotId, setSelectedBotId] = React.useState<number | null>(null)
  const [mobileView, setMobileView] = React.useState<"build" | "test">("build")
  const prevPromptRef = React.useRef<string | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-semibold">지침 빌더</h1>
          <p className="mt-1 text-muted-foreground">구조화 입력으로 봇 지침을 만들고, 바로 테스트한 뒤 적용하세요.</p>
        </div>
        <BotSelector selectedBotId={selectedBotId} onSelect={setSelectedBotId} />
      </div>

      <div className="grid grid-cols-2 rounded-md border p-1 lg:hidden">
        <Button type="button" variant="ghost" onClick={() => setMobileView("build")} className={cn("rounded px-3 py-2 text-sm font-medium", mobileView === "build" && "bg-muted")}>
          작성
        </Button>
        <Button type="button" variant="ghost" onClick={() => setMobileView("test")} className={cn("rounded px-3 py-2 text-sm font-medium", mobileView === "test" && "bg-muted")}>
          테스트
        </Button>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        <div className={cn("space-y-6", mobileView === "test" && "hidden lg:block")}>
          <Card>
            <CardHeader>
              <CardTitle>구조화 입력</CardTitle>
              <CardDescription>봇의 역할과 답변 원칙을 간단히 정리해 주세요.</CardDescription>
            </CardHeader>
            <CardContent>
              <StructuredFields control={form.control} register={form.register} watch={form.watch} setValue={form.setValue} />
            </CardContent>
          </Card>
          <WandBar
            values={values}
            onModelChange={(llmModel) => form.setValue("llm_model", llmModel, { shouldDirty: true })}
            onGenerated={(prompt) => {
              prevPromptRef.current = form.getValues("system_prompt")
              form.setValue("system_prompt", prompt, { shouldDirty: true })
            }}
          />
          <Card>
            <CardHeader>
              <CardTitle>완성된 지침</CardTitle>
              <CardDescription>생성된 지침을 직접 편집할 수 있습니다.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <Label htmlFor="system-prompt">완성된 지침 (system prompt)</Label>
              <Textarea id="system-prompt" className="min-h-[300px] resize-y text-sm leading-relaxed" {...form.register("system_prompt")} />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{values.system_prompt.length.toLocaleString()}자</span>
                {prevPromptRef.current !== null && (
                  <button
                    type="button"
                    className="text-primary underline-offset-4 hover:underline"
                    onClick={() => {
                      form.setValue("system_prompt", prevPromptRef.current ?? "", { shouldDirty: true })
                      prevPromptRef.current = null
                    }}
                  >
                    되돌리기
                  </button>
                )}
              </div>
            </CardContent>
          </Card>
          <KnowledgeFiles botId={selectedBotId} />
        </div>
        <div className={cn("lg:sticky lg:top-6", mobileView === "build" && "hidden lg:block")}>
          <Card>
            <CardHeader>
              <CardTitle>실시간 테스트</CardTitle>
              <CardDescription>현재 지침과 선택한 봇의 RAG 설정으로 답변을 확인하세요.</CardDescription>
            </CardHeader>
            <CardContent>
              <TestPanel systemPrompt={values.system_prompt} botId={selectedBotId} llm_model={values.llm_model} />
            </CardContent>
          </Card>
        </div>
      </div>
      <ApplyBar systemPrompt={values.system_prompt} botId={selectedBotId} llm_model={values.llm_model} />
    </div>
  )
}
