"use client"

import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Inbox, Loader2, MessageSquare } from "lucide-react"

import { ErrorState } from "@/components/common/error-state"
import { PageHeader } from "@/components/common/page-header"
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

  const { data: bot, isLoading, isError, error, refetch } = useBot(botId)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-3">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/bots")}
          className="mt-1"
        >
          <ArrowLeft className="size-4" />
          <span className="sr-only">목록으로</span>
        </Button>
        <PageHeader
          title={bot?.name ?? "봇 수정"}
          description="이 봇의 설정과 자료를 한 자리에서 관리합니다."
          actions={
            // 이 봇이 실제로 어떻게 쓰이는지 보러 가는 길. 전에는 이 화면에서
            // 다른 화면으로 가는 링크가 하나도 없었다.
            bot ? (
              <>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/unanswered?bot_id=${bot.id}`}>
                    <Inbox className="size-4" />못 답한 질문
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/chats?botId=${bot.id}`}>
                    <MessageSquare className="size-4" />대화 기록
                  </Link>
                </Button>
              </>
            ) : null
          }
        />
      </div>

      {isLoading && (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {isError && (
        <ErrorState
          title="봇 정보를 불러오지 못했습니다"
          error={error}
          onRetry={() => refetch()}
        />
      )}

      {bot && <BotEditForm bot={bot} />}
    </div>
  )
}
