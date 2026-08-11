"use client"

// 봇 상세 「지정 답변」 탭.
//
// 이 기능은 RAG 를 건너뛰고 관리자가 정한 답을 그대로 내보낸다. 그래서 사실을
// 등록하는 자리가 아니라 **차단·교정용**이다. 그 성격을 화면에서 한 줄로 밝힌다.
import { FaqDataTable } from "@/features/faqs/components/faq-data-table"

export function BotFaqsPanel({ botId }: { botId: number }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        여기 등록한 질문은 AI 추론을 건너뛰고 지정한 답을 그대로 내보냅니다. 자료로
        답하게 하려면 「자료」 탭에 문서를 올리세요.
      </p>
      <FaqDataTable botId={botId} />
    </div>
  )
}
