"use client"

// 봇 수정 폼 — 기본 정보 / 답변 설정 / 연동 세 탭.
//
// Radix Tabs 를 쓰지 않는다. TabsContent 는 비활성 패널을 언마운트하는데 이 폼에는
// 비제어 입력(이미지 파일 state, 태그 입력)이 섞여 있어 탭을 옮기면 값이 날아간다.
// instructions/page.tsx 와 같은 CSS 숨김 방식으로 전부 마운트해 둔다.

import * as React from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { AlertTriangle, ImagePlus, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { useUpdateBot } from "@/features/bots/hooks"
import { updateBot as updateBotRequest } from "@/features/bots/api"
import { DEFAULT_CLARIFICATION_POLICY, type BotResponse, type ClarificationPolicy } from "@/features/bots/types"

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
  botEditFormSchema,
  type BotEditFormValues,
  PLAN_TYPE_OPTIONS,
} from "../schemas"
import { Separator } from "@/components/ui/separator"
import { AnswerSettings } from "./answer-settings"
import { KakaoChannelSection } from "./kakao-channel-section"
import { ClarificationPolicySection } from "./clarification-policy-section"

const TABS = [
  { key: "basic", label: "기본 정보" },
  { key: "answer", label: "답변 설정" },
  { key: "integration", label: "연동" },
] as const

type TabKey = (typeof TABS)[number]["key"]

// 어느 탭에 어떤 필드가 있는지 — 검증 실패 시 그 탭으로 보내고 배지를 띄운다.
const TAB_FIELDS: Record<TabKey, (keyof BotEditFormValues)[]> = {
  basic: [
    "name",
    "description",
    "tags",
    "plan_required",
    "is_active",
    "is_verified",
    "is_new",
  ],
  answer: [
    "retrieval_mode",
    "evidence_policy_mode",
    "llm_model",
    "history_window",
    "system_prompt",
    "clarify_enabled",
    "clarification_policy",
  ],
  integration: [],
}

interface BotEditFormProps {
  bot: BotResponse
}

export function BotEditForm({ bot }: BotEditFormProps) {
  const router = useRouter()
  const [tab, setTab] = React.useState<TabKey>("basic")
  const [tagInput, setTagInput] = React.useState("")
  const [isComposing, setIsComposing] = React.useState(false)
  const [imageFile, setImageFile] = React.useState<File | null>(null)
  const [confirmLeave, setConfirmLeave] = React.useState(false)

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
      history_window: bot.history_window ?? 0,
      evidence_policy_mode: bot.evidence_policy_mode ?? "legacy",
      retrieval_mode: bot.retrieval_mode ?? "file_search",
      clarify_enabled: bot.clarify_enabled ?? false,
      clarification_policy: bot.clarification_policy ?? DEFAULT_CLARIFICATION_POLICY,
    },
  })

  // useWatch로 값 구독 (React Compiler 호환)
  const watchedTags = useWatch({ control: form.control, name: "tags" })
  const retrievalMode = useWatch({ control: form.control, name: "retrieval_mode" })
  const evidencePolicyMode = useWatch({
    control: form.control,
    name: "evidence_policy_mode",
  })

  const { errors, isDirty } = form.formState
  const errorTabs = React.useMemo(() => {
    const bad = new Set<TabKey>()
    for (const [key, fields] of Object.entries(TAB_FIELDS) as [
      TabKey,
      (keyof BotEditFormValues)[],
    ][]) {
      if (fields.some((f) => errors[f])) bad.add(key)
    }
    return bad
  }, [errors])

  // 검증 실패 시 문제가 있는 첫 탭으로 옮긴다 — 접힌 탭에서 조용히 막히면 원인을 못 찾는다.
  function onInvalid(fieldErrors: typeof errors) {
    const target = TABS.find((t) =>
      TAB_FIELDS[t.key].some((f) => fieldErrors[f])
    )
    if (target) setTab(target.key)
  }

  // 태그 추가 (Enter 키)
  function handleTagKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      if (isComposing) return
      e.preventDefault()
      const value = tagInput.trim()
      if (value && !form.getValues("tags").includes(value)) {
        form.setValue("tags", [...form.getValues("tags"), value], {
          shouldDirty: true,
        })
        setTagInput("")
      }
    }
  }

  // 태그 삭제
  function removeTag(tagToRemove: string) {
    form.setValue(
      "tags",
      form.getValues("tags").filter((tag) => tag !== tagToRemove),
      { shouldDirty: true }
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

  // 취소 — 저장하지 않은 변경이 있으면 확인한다. 시스템 프롬프트가 1,000자를 넘는 봇이 있어
  // 실수로 날리면 복구가 안 된다.
  const hasUnsaved = isDirty || imageFile !== null

  function handleCancel() {
    if (hasUnsaved) {
      setConfirmLeave(true)
      return
    }
    router.push("/bots")
  }

  // 취소 버튼 말고 새로고침·주소창·탭 닫기로 나가는 경로도 막는다.
  // (Next.js 앱 라우터에는 내부 링크 이탈을 가로챌 공개 API 가 없어 사이드바 이동은 못 막는다.)
  React.useEffect(() => {
    if (!hasUnsaved) return
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ""
    }
    window.addEventListener("beforeunload", onBeforeUnload)
    return () => window.removeEventListener("beforeunload", onBeforeUnload)
  }, [hasUnsaved])

  // 탭 목록 키보드 조작 — role=tablist 를 직접 만들었으므로 화살표·Home·End 도 직접 구현한다.
  const tabRefs = React.useRef<(HTMLButtonElement | null)[]>([])

  function handleTabKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    const last = TABS.length - 1
    let next: number | null = null
    if (e.key === "ArrowRight") next = index === last ? 0 : index + 1
    else if (e.key === "ArrowLeft") next = index === 0 ? last : index - 1
    else if (e.key === "Home") next = 0
    else if (e.key === "End") next = last
    if (next === null) return
    e.preventDefault()
    setTab(TABS[next].key)
    tabRefs.current[next]?.focus()
  }

  // 정책은 폼 저장과 별개로 즉시 반영한다 — 카드 편집이 폼 제출과 독립이라서다.
  async function persistClarificationPolicy(policy: ClarificationPolicy) {
    const updated = await updateBotRequest(bot.id, { clarification_policy: policy })
    form.setValue("clarification_policy", updated.clarification_policy)
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
        {/* 탭 — 패널은 전부 마운트된 채 CSS 로만 감춘다 */}
        <div
          role="tablist"
          aria-label="봇 설정 영역"
          className="mb-6 flex gap-1 border-b"
        >
          {TABS.map((item, index) => (
            <button
              key={item.key}
              type="button"
              role="tab"
              id={`bot-tab-${item.key}`}
              ref={(el) => {
                tabRefs.current[index] = el
              }}
              aria-selected={tab === item.key}
              aria-controls={`bot-panel-${item.key}`}
              // roving tabIndex — 탭 목록 전체가 Tab 순서를 세 번 잡아먹지 않게 한다.
              tabIndex={tab === item.key ? 0 : -1}
              onKeyDown={(e) => handleTabKeyDown(e, index)}
              onClick={() => setTab(item.key)}
              className={cn(
                "-mb-px flex min-h-11 items-center gap-1.5 border-b-2 px-4 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
                tab === item.key
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {item.label}
              {errorTabs.has(item.key) && (
                <span
                  className="size-1.5 rounded-full bg-destructive"
                  aria-label="입력 오류 있음"
                />
              )}
            </button>
          ))}
        </div>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit, onInvalid)}
            className="space-y-6"
          >
            {/* ══ 기본 정보 ══ */}
            <div
              id="bot-panel-basic"
              role="tabpanel"
              aria-labelledby="bot-tab-basic"
              className={cn("space-y-6", tab !== "basic" && "hidden")}
            >
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
                        {watchedTags?.length > 0 && (
                          <div className="flex flex-wrap gap-2 pt-3">
                            {watchedTags.map((tag) => (
                              <Badge
                                key={tag}
                                variant="secondary"
                                className="gap-1 pr-1"
                              >
                                {tag}
                                <button
                                  type="button"
                                  onClick={() => removeTag(tag)}
                                  className="rounded-full p-0.5 hover:bg-muted-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                  aria-label={`${tag} 태그 삭제`}
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

              {/* 플랜 */}
              <FormField
                control={form.control}
                name="plan_required"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>요구 플랜</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
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

              {/* 노출 설정 */}
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-semibold">노출 설정</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    봇의 노출 상태 및 인증 여부를 관리합니다.
                  </p>
                </div>

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

                <FormField
                  control={form.control}
                  name="is_new"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">신규 뱃지</FormLabel>
                        <FormDescription>
                          활성화하면 봇 목록에서 &apos;NEW&apos; 뱃지가
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
              </div>
            </div>

            {/* ══ 답변 설정 ══ */}
            <div
              id="bot-panel-answer"
              role="tabpanel"
              aria-labelledby="bot-tab-answer"
              className={cn(tab !== "answer" && "hidden")}
            >
              <AnswerSettings
                form={form}
                initialModel={bot.llm_model}
                retrievalMode={retrievalMode}
                evidencePolicyMode={evidencePolicyMode}
              />

              <Separator className="my-6" />

              {/* 맥락 보완 — 근거 조달 방식과 같은 「답변 설정」 축이라 이 탭에 둔다. */}
              <FormField
                control={form.control}
                name="clarify_enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between gap-4 rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <FormLabel className="text-base">맥락 보완 파일럿</FormLabel>
                        <Badge variant="outline" className="text-[10px] font-normal">
                          미리보기 전용
                        </Badge>
                      </div>
                      <FormDescription>
                        모호한 요청에 선택형 추가 질문을 생성하는 실제 LLM 테스트를 이 봇에서만 허용합니다.
                      </FormDescription>
                      {/* 켜도 사용자 대화는 안 바뀐다 — clarify_enabled 를 읽는 곳은
                          미리보기 엔드포인트 하나뿐이다(clarification_preview.py). */}
                      <div className="mt-2 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                        <p className="text-[11px] leading-relaxed text-foreground/90">
                          아래 「추가 확인 질문 정책」의 <b>「테스트하기」에서만 동작합니다.</b>{" "}
                          실제 사용자 대화에는 아직 연결돼 있지 않습니다.
                        </p>
                      </div>
                      <FormMessage />
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

              <ClarificationPolicySection
                botId={bot.id}
                initialPolicy={bot.clarification_policy ?? DEFAULT_CLARIFICATION_POLICY}
                onPersist={persistClarificationPolicy}
              />
            </div>

            {/* ══ 연동 ══ */}
            <div
              id="bot-panel-integration"
              role="tabpanel"
              aria-labelledby="bot-tab-integration"
              className={cn(tab !== "integration" && "hidden")}
            >
              <KakaoChannelSection botId={bot.id} />
            </div>

            {/* 버튼 */}
            <div className="flex items-center gap-3 border-t pt-4">
              <Button type="submit" disabled={isPending}>
                {isPending ? "저장 중..." : "저장"}
              </Button>
              <Button type="button" variant="outline" onClick={handleCancel}>
                취소
              </Button>
              {isDirty && (
                <span className="text-xs text-muted-foreground">
                  저장하지 않은 변경이 있습니다
                </span>
              )}
            </div>
          </form>
        </Form>
      </CardContent>

      <Dialog open={confirmLeave} onOpenChange={setConfirmLeave}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>저장하지 않은 변경사항</DialogTitle>
            <DialogDescription>
              이 페이지를 벗어나면 변경한 내용이 사라집니다. 시스템 프롬프트는
              복구할 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmLeave(false)}
            >
              계속 편집
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => router.push("/bots")}
            >
              버리고 이동
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
