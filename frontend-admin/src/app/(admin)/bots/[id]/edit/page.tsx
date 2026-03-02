"use client"

import { useParams, useRouter } from "next/navigation"
import { Loader2, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useBot } from "@/features/bots/hooks"
import { BotEditForm } from "@/features/bots/components/bot-edit-form"

/**
 * 봇 수정 페이지.
 * - params.id 로 봇 단일 조회 후 BotEditForm에 데이터를 주입.
 * - 로딩/에러 상태를 처리하고, 성공 시 BotEditForm 내부에서 /bots 로 리디렉션.
 */
export default function EditBotPage() {
  const params = useParams()
  const router = useRouter()
  const botId = Number(params.id)

  const { data: bot, isLoading, isError, error } = useBot(botId)

  return (
    <div className="flex flex-col gap-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/bots")}
          className="h-8 w-8 p-0"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="sr-only">목록으로</span>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">봇 수정</h1>
          <p className="text-muted-foreground">봇의 설정과 운영 상태를 변경합니다.</p>
        </div>
      </div>

      {/* 로딩 상태 */}
      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* 에러 상태 */}
      {isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center text-destructive text-sm">
          봇 정보를 불러오는 데 실패했습니다.{" "}
          {error instanceof Error ? `(${error.message})` : ""}
        </div>
      )}

      {/* 수정 폼 */}
      {bot && <BotEditForm bot={bot} />}
    </div>
  )
}
