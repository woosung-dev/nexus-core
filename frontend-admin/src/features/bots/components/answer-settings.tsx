"use client"

// 답변 설정 탭 — 프리셋 3장을 앞에 두고 축별 조정은 접어 둔다(progressive disclosure).
// 관리자는 봇 성격만 고르면 되고, 두 축(조달 방식·근거 검증)을 따로 이해할 필요가 없다.
// 각 모드에 실측 수치를 상시 표기한다 — 규정 봇 설정 화면에서 근거를 보이는 것이
// 이 제품의 성격에 맞는다.

import * as React from "react"
import { ChevronDown, Info } from "lucide-react"
import type { UseFormReturn } from "react-hook-form"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  ANSWER_PRESETS,
  LLM_MODEL_OPTIONS,
  RETRIEVAL_MODE_OPTIONS,
  getModelProvider,
  matchPreset,
  type BotEditFormValues,
} from "../schemas"

interface AnswerSettingsProps {
  form: UseFormReturn<BotEditFormValues>
  initialModel: string
  retrievalMode: string
  evidencePolicyMode: string
}

export function AnswerSettings({
  form,
  initialModel,
  retrievalMode,
  evidencePolicyMode,
}: AnswerSettingsProps) {
  const [advancedOpen, setAdvancedOpen] = React.useState(false)
  const active = matchPreset(retrievalMode, evidencePolicyMode)
  const initialProvider = getModelProvider(initialModel)
  // 어휘 검색은 Gemini 클라이언트를 직접 만든다. 다른 공급자 봇에서는 서버가
  // file_search 로 되돌리므로, 고르기 전에 알려 준다.
  const lexicalUnavailable =
    initialProvider === "openai" && retrievalMode !== "file_search"

  // radiogroup 키보드 조작 — Radix RadioGroup 프리미티브가 이 레포에 없어 직접 만든다.
  const cardRefs = React.useRef<(HTMLButtonElement | null)[]>([])

  function handleCardKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    const last = ANSWER_PRESETS.length - 1
    let next: number | null = null
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = index === last ? 0 : index + 1
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = index === 0 ? last : index - 1
    else if (e.key === "Home") next = 0
    else if (e.key === "End") next = last
    if (next === null) return
    e.preventDefault()
    applyPreset(ANSWER_PRESETS[next])
    cardRefs.current[next]?.focus()
  }

  function applyPreset(preset: (typeof ANSWER_PRESETS)[number]) {
    form.setValue("retrieval_mode", preset.retrieval_mode, {
      shouldDirty: true,
      shouldValidate: true,
    })
    form.setValue("evidence_policy_mode", preset.evidence_policy_mode, {
      shouldDirty: true,
      shouldValidate: true,
    })
  }

  return (
    <div className="space-y-6">
      {/* ── 프리셋 ── */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">답변 방식</h3>
          {active ? (
            <Badge variant="secondary">{active.label}</Badge>
          ) : (
            <Badge variant="outline">사용자 지정</Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          이 봇이 근거를 어떻게 조달하고 얼마나 엄격하게 검증할지 한 번에
          정합니다. 수치는 45문항 실측입니다.
        </p>

        <div
          role="radiogroup"
          aria-label="답변 방식 프리셋"
          className="grid gap-3 sm:grid-cols-3"
        >
          {ANSWER_PRESETS.map((preset, index) => {
            const selected = active?.key === preset.key
            const mode = RETRIEVAL_MODE_OPTIONS.find(
              (m) => m.value === preset.retrieval_mode
            )
            return (
              <button
                key={preset.key}
                type="button"
                role="radio"
                aria-checked={selected}
                ref={(el) => {
                  cardRefs.current[index] = el
                }}
                // 프리셋과 어느 것도 안 맞으면(사용자 지정) 첫 카드가 진입점이 된다.
                tabIndex={selected || (!active && index === 0) ? 0 : -1}
                onKeyDown={(e) => handleCardKeyDown(e, index)}
                onClick={() => applyPreset(preset)}
                className={cn(
                  "flex min-h-11 flex-col items-start gap-1.5 rounded-lg border p-4 text-left transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  selected
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
                )}
              >
                <span className="text-sm font-semibold">{preset.label}</span>
                <span className="text-[11px] text-muted-foreground">
                  {preset.for}
                </span>
                <span className="mt-1 font-mono text-[11px] text-foreground/80">
                  {mode?.summary}
                </span>
                <span className="text-[11px] leading-relaxed text-muted-foreground">
                  {preset.note}
                </span>
              </button>
            )
          })}
        </div>

        {!active && (
          <p className="flex items-start gap-1.5 rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
            <Info className="mt-px size-3.5 shrink-0" aria-hidden />
            축을 직접 조정해 프리셋과 달라진 상태입니다. 프리셋을 누르면 두 축이
            함께 되돌아갑니다.
          </p>
        )}

        {lexicalUnavailable && (
          <p className="flex items-start gap-1.5 rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
            <Info className="mt-px size-3.5 shrink-0" aria-hidden />
            어휘 검색은 Gemini 계열 모델에서만 동작합니다. 이 봇은 OpenAI 모델이라
            서버가 의미 검색으로 되돌립니다.
          </p>
        )}
      </section>

      {/* ── 고급 설정 ── */}
      <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
        <CollapsibleTrigger className="flex min-h-11 w-full items-center gap-1.5 rounded-md text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <ChevronDown
            className={cn(
              "size-4 transition-transform",
              advancedOpen && "rotate-180"
            )}
            aria-hidden
          />
          고급 설정
          <span className="text-xs font-normal">
            축별 조정 · 모델 · 시스템 프롬프트
          </span>
        </CollapsibleTrigger>

        <CollapsibleContent className="mt-4 space-y-4">
          {/* 조달 방식 */}
          <FormField
            control={form.control}
            name="retrieval_mode"
            render={({ field }) => (
              <FormItem className="rounded-lg border p-4">
                <FormLabel className="text-base">근거 조달 방식</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {RETRIEVAL_MODE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormDescription>
                  {RETRIEVAL_MODE_OPTIONS.map((option) => (
                    <span
                      key={option.value}
                      className={cn(
                        "block",
                        option.value === field.value
                          ? "font-medium text-foreground"
                          : "text-muted-foreground"
                      )}
                    >
                      <span className="font-mono">{option.summary}</span> —{" "}
                      {option.detail}
                    </span>
                  ))}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* 근거 검증 */}
          <FormField
            control={form.control}
            name="evidence_policy_mode"
            render={({ field }) => (
              <FormItem className="rounded-lg border p-4">
                <FormLabel className="text-base">근거 검증 모드</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="legacy">기존 호환 모드</SelectItem>
                    <SelectItem value="strict">직접 인용 필수 모드</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  엄격 모드는 이번 답변에 직접 인용을 남기지 못하면 답변을
                  차단합니다. FAQ는 “답변할 수 없습니다” 같은 거절 안내문으로만
                  등록해 주세요. 문서 최신성·용어 검증은 이 모드의 범위가
                  아닙니다.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* LLM 모델 — Provider 간 변경 제한 (RAG 문서 격리 이슈로 같은 Provider 내에서만 지원) */}
          <FormField
            control={form.control}
            name="llm_model"
            render={({ field }) => (
              <FormItem className="rounded-lg border p-4">
                <FormLabel className="text-base">LLM 모델</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="mt-2">
                      <SelectValue placeholder="모델을 선택해 주세요" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {LLM_MODEL_OPTIONS.map((option) => {
                      const isDifferentProvider =
                        initialProvider !== "unknown" &&
                        option.provider !== initialProvider

                      return (
                        <SelectItem
                          key={option.value}
                          value={option.value}
                          disabled={isDifferentProvider}
                        >
                          {option.label}
                          {isDifferentProvider &&
                            " (다른 공급자 모델로 변경 불가)"}
                        </SelectItem>
                      )
                    })}
                  </SelectContent>
                </Select>
                <FormDescription>
                  이 봇이 사용할 AI 모델을 선택합니다.
                  {initialProvider !== "unknown" && (
                    <span className="block mt-1 font-medium text-amber-700 dark:text-amber-400">
                      (이미 등록된 문서와의 호환성을 위해{" "}
                      {initialProvider === "openai" ? "OpenAI" : "Gemini"} 계열의
                      모델만 선택 가능합니다.)
                    </span>
                  )}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* 대화 기억 윈도우 */}
          <FormField
            control={form.control}
            name="history_window"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <FormLabel className="text-base">대화 기억 윈도우</FormLabel>
                  <FormDescription>
                    LLM에 함께 보낼 최근 메시지 수입니다. 0이면 기억하지
                    않습니다(기존 동작). 권장값 8. 카카오 연결 봇은 0을
                    유지하세요.
                  </FormDescription>
                  <FormMessage />
                </div>
                <FormControl>
                  <Input
                    type="number"
                    min={0}
                    step={1}
                    className="w-24 shrink-0"
                    {...field}
                  />
                </FormControl>
              </FormItem>
            )}
          />

          {/* 시스템 프롬프트 */}
          <FormField
            control={form.control}
            name="system_prompt"
            render={({ field }) => (
              <FormItem>
                <FormLabel>시스템 프롬프트</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="봇의 페르소나와 행동 규칙을 정의하세요..."
                    className="min-h-[200px] resize-y"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  봇의 성격, 말투, 답변 규칙 등을 상세히 기술합니다. 현재{" "}
                  {field.value?.length ?? 0}자.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
