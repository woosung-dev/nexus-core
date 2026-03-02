"use client"

/**
 * 문서(지식 베이스) 관리 페이지.
 * 봇 선택 → 문서 업로드 → 문서 목록 확인의 흐름으로 구성.
 * 비즈니스 로직은 각 컴포넌트 및 훅으로 위임하며, 이 페이지는 조립만 담당.
 */
import * as React from "react"
import { BotSelector } from "@/features/documents/components/bot-selector"
import { DocumentUploadZone } from "@/features/documents/components/document-upload-zone"
import { DocumentTable } from "@/features/documents/components/document-table"
import { useDocuments } from "@/features/documents/hooks"
import { Separator } from "@/components/ui/separator"

// 봇이 선택된 이후 문서 로드 영역을 렌더링하는 하위 컴포넌트
function DocumentSection({ botId }: { botId: number }) {
  const { data, isLoading } = useDocuments(botId)
  const documents = data?.documents ?? []

  return (
    <div className="flex flex-col gap-6">
      {/* 파일 업로드 영역 */}
      <div>
        <h2 className="text-base font-semibold mb-3">문서 업로드</h2>
        <DocumentUploadZone botId={botId} />
      </div>

      <Separator />

      {/* 문서 목록 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">등록된 문서</h2>
          <span className="text-sm text-muted-foreground">
            총 {data?.total ?? 0}건
          </span>
        </div>
        <DocumentTable botId={botId} documents={documents} isLoading={isLoading} />
      </div>
    </div>
  )
}

// 봇이 선택되지 않았을 때 안내 화면
function EmptyBotSelection() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed h-64 text-center gap-3 text-muted-foreground">
      <p className="text-sm font-medium">먼저 상단에서 봇을 선택해 주세요.</p>
      <p className="text-xs">선택한 봇의 지식 베이스(RAG 문서)를 관리할 수 있습니다.</p>
    </div>
  )
}

// --- 페이지 ---
export default function DocumentsPage() {
  const [selectedBotId, setSelectedBotId] = React.useState<number | null>(null)

  return (
    <div className="flex flex-col gap-6">
      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">문서 관리</h1>
        <p className="text-muted-foreground">
          봇별 지식 베이스(RAG 문서)를 업로드하고 관리합니다.
        </p>
      </div>

      {/* 봇 선택 */}
      <BotSelector selectedBotId={selectedBotId} onSelect={setSelectedBotId} />

      <Separator />

      {/* 봇 선택 여부에 따라 분기 */}
      {selectedBotId !== null
        ? <DocumentSection botId={selectedBotId} />
        : <EmptyBotSelection />
      }
    </div>
  )
}
