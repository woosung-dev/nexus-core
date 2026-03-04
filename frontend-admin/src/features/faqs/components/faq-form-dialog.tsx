"use client"

import { useEffect } from "react"
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
import { faqFormSchema, type FaqFormValues } from "@/features/faqs/schemas"
import type { FaqResponse } from "@/features/faqs/types"

// --- Props ---
interface FaqFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** null이면 등록(create) 모드, 객체면 수정(edit) 모드 */
  initialData: FaqResponse | null
  bots: { id: number; name: string }[]
  selectedBotIdForCreate: number | null
  onSubmit: (values: { bot_id: number; question: string; answer: string; threshold: number }) => void
  isPending: boolean
}

export function FaqFormDialog({
  open,
  onOpenChange,
  initialData,
  bots,
  selectedBotIdForCreate,
  onSubmit,
  isPending,
}: FaqFormDialogProps) {
  const isEditMode = !!initialData

  // ── react-hook-form + zod 연동 ──
  const form = useForm<FaqFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈 (런타임 정상 동작)
    resolver: zodResolver(faqFormSchema as any),
    defaultValues: {
      bot_id: 0,
      question: "",
      answer: "",
      threshold: 0.8,
    },
  })

  // 수정 모드 진입 시 기존 데이터를 폼에 채움
  useEffect(() => {
    if (open && initialData) {
      form.reset({
        bot_id: initialData.bot_id,
        question: initialData.question,
        answer: initialData.answer,
        threshold: initialData.threshold,
      })
    } else if (open && !initialData) {
      form.reset({
        bot_id: selectedBotIdForCreate || 0,
        question: "",
        answer: "",
        threshold: 0.8,
      })
    }
  }, [open, initialData, form, selectedBotIdForCreate])

  function handleSubmit(values: FaqFormValues) {
    onSubmit({
      bot_id: values.bot_id,
      question: values.question,
      answer: values.answer,
      threshold: values.threshold,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>
            {isEditMode ? "FAQ 수정" : "새 FAQ 추가"}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? "기존 FAQ의 질문, 답변, 유사도 임계값을 수정합니다."
              : "AI 추론 대신 출력할 우선순위 답변(FAQ Override)을 등록합니다."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className="space-y-4"
          >
            {/* 봇 선택 */}
            <FormField
              control={form.control}
              name="bot_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>대상 봇</FormLabel>
                  {isEditMode ? (
                    <FormControl>
                      <Input
                        disabled
                        value={
                          bots.find((b) => b.id === field.value)?.name ??
                          "알 수 없는 봇"
                        }
                      />
                    </FormControl>
                  ) : (
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="봇을 선택해 주세요" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {bots.map((bot) => (
                          <SelectItem key={bot.id} value={String(bot.id)}>
                            {bot.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 질문 */}
            <FormField
              control={form.control}
              name="question"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>질문</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="예: 환불 정책이 어떻게 되나요?"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 답변 */}
            <FormField
              control={form.control}
              name="answer"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>답변</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="사용자에게 출력될 100% 정답을 입력하세요."
                      rows={4}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 유사도 임계값 */}
            <FormField
              control={form.control}
              name="threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>유사도 임계값</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      placeholder="0.80"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    0.0 ~ 1.0 사이의 값. 이 값 이상의 유사도를 가지면 해당 답변을
                    우선 출력합니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                취소
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending
                  ? "저장 중..."
                  : isEditMode
                    ? "수정"
                    : "등록"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
