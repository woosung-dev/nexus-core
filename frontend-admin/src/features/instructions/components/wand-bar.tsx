"use client"

// 구조화된 입력으로 시스템 프롬프트를 생성하거나 개선하는 도구 모음.
import { Loader2, Sparkles, Wand2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { LLM_MODEL_OPTIONS, type BuilderValues } from "../schemas"
import { useGenerateInstruction } from "../hooks"

type WandBarProps = {
  values: BuilderValues
  onGenerated: (prompt: string) => void
  onModelChange?: (model: string) => void
}

export function WandBar({ values, onGenerated, onModelChange }: WandBarProps) {
  const generate = useGenerateInstruction()

  function request(mode: "generate" | "improve") {
    generate.mutate(
      {
        mode,
        role: values.role,
        goal: values.goal,
        tone: values.tone,
        audience: values.audience,
        constraints: values.constraints,
        dos: values.dos,
        donts: values.donts,
        examples: values.examples,
        llm_model: values.llm_model,
        ...(mode === "improve" ? { draft: values.system_prompt } : {}),
      },
      { onSuccess: (result) => onGenerated(result.system_prompt) }
    )
  }

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">LLM 모델</label>
        <Select value={values.llm_model} onValueChange={onModelChange}>
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
      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={generate.isPending} onClick={() => request("generate")}>
          {generate.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {generate.isPending ? "생성 중…" : "AI로 지침 생성"}
        </Button>
        <Button type="button" variant="outline" disabled={generate.isPending} onClick={() => request("improve")}>
          {generate.isPending ? <Loader2 className="animate-spin" /> : <Wand2 />}
          현재 초안 개선
        </Button>
      </div>
      {generate.isError && <p className="text-destructive text-sm">지침 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.</p>}
      <p className="text-xs text-muted-foreground">구조화 입력을 바탕으로 한국어 지침 초안을 만들어요.</p>
    </div>
  )
}
