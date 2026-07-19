// 전역 또는 봇별 용어집을 관리하는 관리자 페이지입니다.
"use client"

import * as React from "react"

import { Button } from "@/components/ui/button"
import { BotSelector } from "@/features/documents/components/bot-selector"
import { GlossaryDataTable } from "@/features/glossary/components/glossary-data-table"

export default function GlossaryPage() {
  const [selectedBotId, setSelectedBotId] = React.useState<number | null>(null)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">용어집 관리</h1>
        <p className="text-muted-foreground">
          답변에 주입할 전역 및 봇별 용어 정의를 관리합니다.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <BotSelector selectedBotId={selectedBotId} onSelect={setSelectedBotId} />
        <Button
          variant={selectedBotId === null ? "default" : "outline"}
          onClick={() => setSelectedBotId(null)}
        >
          전역 용어
        </Button>
      </div>

      <GlossaryDataTable botId={selectedBotId} />
    </div>
  )
}
