"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { X } from "lucide-react"

import { Button } from "@/components/ui/button"
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
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  botFormSchema,
  type BotFormValues,
  LLM_MODEL_OPTIONS,
} from "../schemas"

// --- 봇 생성/수정 폼 컴포넌트 ---
export function BotForm() {
  const router = useRouter()
  const [tagInput, setTagInput] = React.useState("")

  const form = useForm<BotFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈 (런타임 정상 동작)
    resolver: zodResolver(botFormSchema as any),
    defaultValues: {
      name: "",
      description: "",
      tags: [],
      is_active: true,
      system_prompt: "",
      llm_model: "",
    },
  })

  // useWatch로 태그 값 구독 (React Compiler 호환)
  const watchedTags = useWatch({ control: form.control, name: "tags" })

  // 태그 추가 (Enter 키)
  function handleTagKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault()
      const value = tagInput.trim()
      if (value && !form.getValues("tags").includes(value)) {
        form.setValue("tags", [...form.getValues("tags"), value])
        setTagInput("")
      }
    }
  }

  // 태그 삭제
  function removeTag(tagToRemove: string) {
    form.setValue(
      "tags",
      form.getValues("tags").filter((tag) => tag !== tagToRemove)
    )
  }

  // 폼 제출
  function onSubmit(values: BotFormValues) {
    // TODO: API 연동 시 React Query mutation으로 교체
    console.log("봇 생성 데이터:", values)
    alert("봇 생성 완료! (콘솔 확인)")
    router.push("/bots")
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>새 봇 만들기</CardTitle>
        <CardDescription>
          AI 챗봇의 기본 정보와 시스템 프롬프트를 설정합니다.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* 봇 이름 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>봇 이름</FormLabel>
                  <FormControl>
                    <Input placeholder="예: 고객 상담 봇" {...field} />
                  </FormControl>
                  <FormDescription>
                    사용자에게 표시될 봇의 이름입니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 설명 */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>설명</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="이 봇의 역할을 간단하게 설명해 주세요."
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 태그 */}
            <FormField
              control={form.control}
              name="tags"
              render={() => (
                <FormItem>
                  <FormLabel>태그</FormLabel>
                  <FormControl>
                    <div>
                      <Input
                        placeholder="태그를 입력하고 Enter를 누르세요"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={handleTagKeyDown}
                      />
                      {watchedTags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {watchedTags.map((tag) => (
                            <Badge
                              key={tag}
                              variant="secondary"
                              className="gap-1"
                            >
                              {tag}
                              <button
                                type="button"
                                onClick={() => removeTag(tag)}
                                className="rounded-full hover:bg-muted-foreground/20 p-0.5"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </FormControl>
                  <FormDescription>
                    봇을 분류하기 위한 태그를 추가합니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* LLM 모델 */}
            <FormField
              control={form.control}
              name="llm_model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>LLM 모델</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="모델을 선택해 주세요" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {LLM_MODEL_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    이 봇이 사용할 AI 모델을 선택합니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 활성 상태 */}
            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">활성 상태</FormLabel>
                    <FormDescription>
                      비활성화하면 이 봇은 사용자에게 노출되지 않습니다.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
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
                    봇의 성격, 말투, 답변 규칙 등을 상세히 기술합니다.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 버튼 */}
            <div className="flex gap-3 pt-4">
              <Button type="submit">저장</Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/bots")}
              >
                취소
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
