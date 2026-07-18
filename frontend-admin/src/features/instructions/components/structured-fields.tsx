"use client"

// 지침 생성을 위한 구조화 입력 필드를 렌더링한다.
import * as React from "react"
import { Controller, type Control, type UseFormRegister, type UseFormSetValue, type UseFormWatch } from "react-hook-form"
import { X } from "lucide-react"
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
import { Textarea } from "@/components/ui/textarea"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { TONE_PRESETS, type BuilderValues } from "../schemas"

type StructuredFieldsProps = {
  control: Control<BuilderValues>
  register: UseFormRegister<BuilderValues>
  watch: UseFormWatch<BuilderValues>
  setValue: UseFormSetValue<BuilderValues>
}

function ListEditor({
  label,
  helper,
  name,
  values,
  setValue,
}: {
  label: string
  helper: string
  name: "dos" | "donts"
  values: string[]
  setValue: UseFormSetValue<BuilderValues>
}) {
  const [input, setInput] = React.useState("")
  const isComposing = React.useRef(false)

  function addValue() {
    const value = input.trim()
    if (!value || values.includes(value)) return
    setValue(name, [...values, value], { shouldDirty: true })
    setInput("")
  }

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <p className="text-xs text-muted-foreground">{helper}</p>
      <Input
        aria-label={`${label} 추가`}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onCompositionStart={() => { isComposing.current = true }}
        onCompositionEnd={() => { isComposing.current = false }}
        onKeyDown={(event) => {
          if (event.key !== "Enter" || isComposing.current) return
          event.preventDefault()
          addValue()
        }}
        placeholder="입력 후 Enter를 누르세요"
      />
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {values.map((value) => (
            <Badge key={value} variant="secondary" className="gap-1">
              {value}
              <button
                type="button"
                aria-label="삭제"
                className="rounded-full p-0.5 hover:bg-muted-foreground/20"
                onClick={() => setValue(name, values.filter((item) => item !== value), { shouldDirty: true })}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

export function StructuredFields({ control, register, watch, setValue }: StructuredFieldsProps) {
  const dos = watch("dos")
  const donts = watch("donts")
  const examples = watch("examples")

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="instruction-role">역할</Label>
        <Input id="instruction-role" {...register("role")} />
        <p className="text-xs text-muted-foreground">이 봇이 맡을 전문 역할을 적어 주세요.</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="instruction-goal">목표</Label>
        <Textarea id="instruction-goal" rows={2} {...register("goal")} />
        <p className="text-xs text-muted-foreground">사용자에게 제공할 결과를 구체적으로 적어 주세요.</p>
      </div>
      <div className="space-y-2">
        <Label>말투</Label>
        <Controller
          control={control}
          name="tone"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger aria-label="말투">
                <SelectValue placeholder="말투를 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {TONE_PRESETS.map((preset) => (
                  <SelectItem key={preset.value} value={preset.value}>{preset.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        <p className="text-xs text-muted-foreground">답변에서 유지할 언어적 분위기입니다.</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="instruction-audience">대상 독자</Label>
        <Input id="instruction-audience" {...register("audience")} />
        <p className="text-xs text-muted-foreground">주요 사용자와 그들의 배경을 적어 주세요.</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="instruction-constraints">제약</Label>
        <Textarea id="instruction-constraints" rows={2} {...register("constraints")} />
        <p className="text-xs text-muted-foreground">반드시 지켜야 할 범위와 한계를 적어 주세요.</p>
      </div>
      <ListEditor label="해야 할 일" helper="답변에 포함할 행동 원칙입니다." name="dos" values={dos} setValue={setValue} />
      <Collapsible className="rounded-md border p-3">
        <CollapsibleTrigger className="text-sm font-medium">고급 옵션</CollapsibleTrigger>
        <CollapsibleContent className="space-y-4 pt-4">
          <ListEditor label="하지 말아야 할 일" helper="피해야 할 답변과 행동을 추가하세요." name="donts" values={donts} setValue={setValue} />
          <div className="space-y-2">
            <Label>예시</Label>
            <p className="text-xs text-muted-foreground">입력과 원하는 답변 예시를 쌍으로 추가하세요.</p>
            <div className="space-y-3">
              {examples.map((_, index) => (
                <div key={index} className="grid gap-2 rounded-md border p-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label htmlFor={`example-input-${index}`} className="text-xs">입력</Label>
                    <Textarea id={`example-input-${index}`} rows={2} {...register(`examples.${index}.input`)} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={`example-output-${index}`} className="text-xs">출력</Label>
                    <Textarea id={`example-output-${index}`} rows={2} {...register(`examples.${index}.output`)} />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="sm:col-span-2 sm:justify-self-end"
                    onClick={() => setValue("examples", examples.filter((_, itemIndex) => itemIndex !== index), { shouldDirty: true })}
                  >
                    <X className="size-4" />
                    삭제
                  </Button>
                </div>
              ))}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setValue("examples", [...examples, { input: "", output: "" }], { shouldDirty: true })}
            >
              예시 추가
            </Button>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
