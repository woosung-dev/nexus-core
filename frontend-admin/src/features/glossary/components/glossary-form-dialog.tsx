// 용어집 항목을 등록하거나 수정하는 다이얼로그 폼입니다.
"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
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
  glossaryFormSchema,
  type GlossaryFormValues,
} from "@/features/glossary/schemas"
import type { Glossary } from "@/features/glossary/types"

interface GlossaryFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialData: Glossary | null
  selectedBotIdForCreate: number | null
  onSubmit: (values: GlossaryFormValues) => void
  isPending: boolean
}

export function GlossaryFormDialog({
  open,
  onOpenChange,
  initialData,
  selectedBotIdForCreate,
  onSubmit,
  isPending,
}: GlossaryFormDialogProps) {
  const [aliasInput, setAliasInput] = React.useState("")
  const [isComposing, setIsComposing] = React.useState(false)
  const isEditMode = !!initialData
  const form = useForm<GlossaryFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈 (런타임 정상 동작)
    resolver: zodResolver(glossaryFormSchema as any),
    defaultValues: {
      term: "",
      aliases: [],
      definition: "",
      priority: 100,
      threshold: 0.88,
      scope: "global",
    },
  })
  const aliases = useWatch({ control: form.control, name: "aliases" })

  React.useEffect(() => {
    if (open && initialData) {
      form.reset({
        term: initialData.term,
        aliases: initialData.aliases,
        definition: initialData.definition,
        priority: initialData.priority,
        threshold: initialData.threshold,
        scope: initialData.bot_id ? "bot" : "global",
      })
    } else if (open) {
      form.reset({
        term: "",
        aliases: [],
        definition: "",
        priority: 100,
        threshold: 0.88,
        scope: selectedBotIdForCreate ? "bot" : "global",
      })
    }
    setAliasInput("")
  }, [form, initialData, open, selectedBotIdForCreate])

  function addAlias() {
    const alias = aliasInput.trim()
    if (alias && !form.getValues("aliases").includes(alias)) {
      form.setValue("aliases", [...form.getValues("aliases"), alias])
      setAliasInput("")
    }
  }

  function handleAliasKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      if (isComposing) return
      event.preventDefault()
      addAlias()
    }
  }

  function removeAlias(aliasToRemove: string) {
    form.setValue(
      "aliases",
      form.getValues("aliases").filter((alias) => alias !== aliasToRemove)
    )
  }

  function handleSubmit(values: GlossaryFormValues) {
    if (!isEditMode && values.scope === "bot" && !selectedBotIdForCreate) {
      form.setError("scope", { message: "봇 범위는 먼저 봇을 선택해 주세요." })
      return
    }
    onSubmit(values)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{isEditMode ? "용어 수정" : "새 용어 추가"}</DialogTitle>
          <DialogDescription>
            {isEditMode ? "기존 용어의 정의와 적용 기준을 수정합니다." : "답변에 주입할 용어 정의를 등록합니다."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="term"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>용어</FormLabel>
                  <FormControl>
                    <Input placeholder="예: RAG" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="aliases"
              render={() => (
                <FormItem>
                  <FormLabel>동의어</FormLabel>
                  <FormControl>
                    <div>
                      <Input
                        placeholder="동의어를 입력하고 Enter를 누르세요"
                        value={aliasInput}
                        onChange={(event) => setAliasInput(event.target.value)}
                        onCompositionStart={() => setIsComposing(true)}
                        onCompositionEnd={() => setIsComposing(false)}
                        onKeyDown={handleAliasKeyDown}
                      />
                      {aliases.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {aliases.map((alias) => (
                            <Badge key={alias} variant="secondary" className="gap-1">
                              {alias}
                              <button
                                type="button"
                                onClick={() => removeAlias(alias)}
                                className="rounded-full p-0.5 hover:bg-muted-foreground/20"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </FormControl>
                  <FormDescription>Enter를 눌러 동의어를 추가합니다.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="definition"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>정의</FormLabel>
                  <FormControl>
                    <Textarea rows={4} placeholder="답변에 사용할 용어 정의를 입력하세요." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="priority"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>우선순위</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="threshold"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>유사도 임계값</FormLabel>
                    <FormControl>
                      <Input type="number" min="0" max="1" step="0.01" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="scope"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>범위</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={isEditMode}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="global">전역</SelectItem>
                      <SelectItem value="bot">이 봇</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {isEditMode ? "기존 용어의 적용 범위는 변경할 수 없습니다." : "전역 용어는 모든 봇에 적용됩니다."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                취소
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "저장 중..." : isEditMode ? "수정" : "등록"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
