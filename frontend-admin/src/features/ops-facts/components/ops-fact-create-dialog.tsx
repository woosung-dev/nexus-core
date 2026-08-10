"use client"

/**
 * 운영 사실 등록 — 「못 답한 질문」에서 루프를 닫는 자리.
 *
 * `useCreateOpsFact` 의 첫 소비자다. 등록은 항상 `status='초안'` 으로 들어가고 런타임은
 * 승인분만 읽는다 — 여기서 쓴 문장이 곧바로 사용자에게 가지는 않는다.
 *
 * ⚠ `ops_facts` 는 **문서를 못 고칠 때** 쓰는 런타임 덮개다. FAQ 와 달리 검색을 건너뛰지
 * 않아 near-miss 가 근거 없는 오답이 되지는 않지만, 문서로 고칠 수 있는 것을 여기로
 * 덮으면 문서가 계속 낡은 채로 남는다. 그래서 「문서가 틀림·낡음」에서만 이 창이 열린다.
 */
import { useEffect } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useForm } from "react-hook-form"

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

import { KIND_EFFECT, KIND_LABEL, KIND_ORDER } from "../constants"
import { opsFactCreateSchema, type OpsFactCreateValues } from "../schemas"
import type { OpsFactCreateRequest } from "../types"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** 이 사실을 낳은 질문 — 제목에 프리필한다 */
  sourceQuestion: string
  /** 그 질문이 들어온 봇. null 이면 전역 */
  botId: number | null
  onSubmit: (request: OpsFactCreateRequest) => void
  isPending: boolean
}

export function OpsFactCreateDialog({
  open,
  onOpenChange,
  sourceQuestion,
  botId,
  onSubmit,
  isPending,
}: Props) {
  const form = useForm<OpsFactCreateValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈 (런타임 정상 동작)
    resolver: zodResolver(opsFactCreateSchema as any),
    defaultValues: {
      bot_id: botId,
      kind: "deprecated",
      title: "",
      superseded: "",
      statement: "",
    },
  })

  useEffect(() => {
    if (!open) return
    form.reset({
      bot_id: botId,
      kind: "deprecated",
      // 어느 질문에서 나온 사실인지 남는다. 관리자가 그대로 두거나 고친다.
      title: sourceQuestion.slice(0, 80),
      superseded: "",
      statement: "",
    })
  }, [open, sourceQuestion, botId, form])

  function handleSubmit(values: OpsFactCreateValues) {
    onSubmit({
      bot_id: values.bot_id,
      kind: values.kind,
      title: values.title,
      superseded: values.superseded,
      statement: values.statement,
    })
  }

  const kind = form.watch("kind")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>운영 사실 등록</DialogTitle>
          <DialogDescription>
            초안으로 등록됩니다. 승인 전에는 챗봇 답변에 반영되지 않습니다.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="flex flex-col gap-4">
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p className="text-xs text-muted-foreground">이 질문에서 나왔습니다</p>
              <p className="mt-1 leading-snug">{sourceQuestion}</p>
            </div>

            <FormField
              control={form.control}
              name="kind"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>종류</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {KIND_ORDER.map((k) => (
                        <SelectItem key={k} value={k}>
                          {KIND_LABEL[k]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>{KIND_EFFECT[kind]}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>제목</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="관리자 목록에서 한 줄로 식별할 이름" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="superseded"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>쓰면 안 되는 것</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="예: 천일국매칭 20~30세" />
                  </FormControl>
                  <FormDescription>
                    연락처·위기 자원처럼 대체 대상이 없으면 비워 둡니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="statement"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>대신 쓸 것 / 현행 사실</FormLabel>
                  <FormControl>
                    <Textarea {...field} rows={3} placeholder="예: 현행 미적용" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                취소
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? <Loader2 className="mr-1 size-4 animate-spin" /> : null}
                초안으로 등록
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
