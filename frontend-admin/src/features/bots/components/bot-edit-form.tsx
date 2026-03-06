"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { ImagePlus, X } from "lucide-react"

import { useUpdateBot } from "@/features/bots/hooks"
import type { BotResponse } from "@/features/bots/types"

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
import { Separator } from "@/components/ui/separator"
import {
  botEditFormSchema,
  type BotEditFormValues,
  LLM_MODEL_OPTIONS,
  PLAN_TYPE_OPTIONS,
  getModelProvider,
} from "../schemas"

interface BotEditFormProps {
  bot: BotResponse
}

// --- 봇 수정 폼 컴포넌트 ---
// 기존 봇 데이터를 defaultValues로 주입받아 수정 처리
export function BotEditForm({ bot }: BotEditFormProps) {
  const router = useRouter()
  const [tagInput, setTagInput] = React.useState("")
  const [isComposing, setIsComposing] = React.useState(false)
  const [imageFile, setImageFile] = React.useState<File | null>(null)

  // 상대 경로('/static/uploads/...')를 절대 URL로 변환하여 초기 미리보기 설정
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"
  const resolveImageUrl = (url: string | null): string | null => {
    if (!url) return null
    if (url.startsWith("http")) return url
    return `${apiBase}${url}`
  }

  const [imagePreview, setImagePreview] = React.useState<string | null>(
    resolveImageUrl(bot.image_url)
  )
  const imageInputRef = React.useRef<HTMLInputElement>(null)
  const { mutate: updateBot, isPending } = useUpdateBot(bot.id)

  const form = useForm<BotEditFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Zod v4 타입과 @hookform/resolvers 간 호환성 이슈 (런타임 정상 동작)
    resolver: zodResolver(botEditFormSchema as any),
    defaultValues: {
      name: bot.name,
      description: bot.description,
      tags: bot.tags,
      is_active: bot.is_active ?? true,
      is_verified: bot.is_verified,
      is_new: bot.is_new,
      plan_required: bot.plan_required,
      system_prompt: bot.system_prompt,
      llm_model: bot.llm_model,
    },
  })

  // useWatch로 태그 값 구독 (React Compiler 호환)
  const watchedTags = useWatch({ control: form.control, name: "tags" })

  // 태그 추가 (Enter 키)
  function handleTagKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      if (isComposing) return
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

  // 이미지 파일 선택 처리
  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
  }

  // 이미지 선택 취소
  function handleImageRemove() {
    setImageFile(null)
    setImagePreview(null)
    if (imageInputRef.current) imageInputRef.current.value = ""
  }

  // 폼 제출 — useUpdateBot 훅으로 API 호출 (이미지 변경 시 순차 업로드 처리)
  function onSubmit(values: BotEditFormValues) {
    updateBot({ request: values, imageFile })
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>봇 수정</CardTitle>
        <CardDescription>
          <span className="font-semibold text-foreground">{bot.name}</span>의
          설정을 변경합니다.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* 봇 대표 이미지 */}
            <div className="flex flex-col gap-3 pb-2">
              <span className="text-sm font-medium leading-none">
                대표 이미지 <span className="text-muted-foreground">(선택)</span>
              </span>
              <div className="flex items-start gap-6">
                {/* 프리뷰 박스 */}
                <div className="group relative h-40 w-40 shrink-0 overflow-hidden rounded-2xl border-2 border-dashed bg-muted transition-all hover:border-primary/50 flex flex-col items-center justify-center gap-2">
                  {imagePreview ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={imagePreview}
                        alt="봇 이미지 미리보기"
                        className="h-full w-full object-cover transition-transform group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-black/40 opacity-0 transition-opacity group-hover:opacity-100 flex items-center justify-center">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="h-8 text-xs"
                          onClick={handleImageRemove}
                        >
                          제거
                        </Button>
                      </div>
                    </>
                  ) : (
                    <>
                      <ImagePlus className="h-10 w-10 text-muted-foreground/60" />
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                        Preview
                      </span>
                    </>
                  )}
                </div>

                {/* 가이드 및 버튼 */}
                <div className="flex flex-col gap-3 py-1">
                  <div className="space-y-1">
                    <h4 className="text-sm font-semibold text-foreground">
                      Bot Avatar
                    </h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      클라이언트 채팅 목록과 대화창 상단에
                      <br />
                      표시될 봇의 얼굴입니다.
                      <br />
                      <span className="font-medium text-primary/70">
                        정사각형(1:1) 비율을 권장합니다.
                      </span>
                    </p>
                  </div>

                  <div className="flex flex-col gap-2">
                    <input
                      ref={imageInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageChange}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-fit"
                      onClick={() => imageInputRef.current?.click()}
                    >
                      이미지 선택
                    </Button>
                    <p className="text-[11px] font-mono text-muted-foreground truncate max-w-[180px]">
                      {imageFile ? imageFile.name : "선택된 파일 없음"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

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
                        onCompositionStart={() => setIsComposing(true)}
                        onCompositionEnd={() => setIsComposing(false)}
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

            {/* LLM 모델 — Provider 간 변경 제한 (RAG 문서 격리 이슈로 같은 Provider 내에서만 지원) */}
            <FormField
              control={form.control}
              name="llm_model"
              render={({ field }) => {
                const initialProvider = getModelProvider(bot.llm_model)

                return (
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
                              {isDifferentProvider && " (다른 공급자 모델로 변경 불가)"}
                            </SelectItem>
                          )
                        })}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      이 봇이 사용할 AI 모델을 선택합니다.
                      {initialProvider !== "unknown" && (
                        <span className="block mt-1 font-medium text-amber-600 dark:text-amber-400">
                          (이미 등록된 문서와의 호환성을 위해{" "}
                          {initialProvider === "openai" ? "OpenAI" : "Gemini"}{" "}
                          계열의 모델만 선택 가능합니다.)
                        </span>
                      )}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )
              }}
            />

            {/* 플랜 */}
            <FormField
              control={form.control}
              name="plan_required"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>요구 플랜</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="플랜을 선택해 주세요" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {PLAN_TYPE_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    이 봇을 사용하기 위해 필요한 구독 플랜을 설정합니다.
                  </FormDescription>
                  <FormMessage />
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

            <Separator />

            {/* ── 운영 메타데이터 섹션 ── */}
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold">운영 설정</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  봇의 노출 상태 및 인증 여부를 관리합니다.
                </p>
              </div>

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

              {/* 인증 여부 */}
              <FormField
                control={form.control}
                name="is_verified"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">인증 여부</FormLabel>
                      <FormDescription>
                        활성화하면 사용자에게 &apos;인증된 봇&apos; 뱃지가
                        표시됩니다.
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

              {/* 신규 여부 */}
              <FormField
                control={form.control}
                name="is_new"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">신규 뱃지</FormLabel>
                      <FormDescription>
                        활성화하면 봇 목록에서 &apos;NEW&apos; 뱃지가 표시됩니다.
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
            </div>

            {/* 버튼 */}
            <div className="flex gap-3 pt-4">
              <Button type="submit" disabled={isPending}>
                {isPending ? "저장 중..." : "저장"}
              </Button>
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
