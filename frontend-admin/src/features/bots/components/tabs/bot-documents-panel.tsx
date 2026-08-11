"use client"

// 봇 상세 「자료」 탭. 전에는 최상위 `/documents` 에서 봇을 다시 골라야 했다.
// 봇이 이미 정해진 자리라 선택기가 필요 없다.
import { DocumentUploadZone } from "@/features/documents/components/document-upload-zone"
import { DocumentTable } from "@/features/documents/components/document-table"
import { useDocuments } from "@/features/documents/hooks"
import { ErrorState } from "@/components/common/error-state"
import { Separator } from "@/components/ui/separator"

export function BotDocumentsPanel({ botId }: { botId: number }) {
  const { data, isLoading, isError, error, refetch } = useDocuments(botId)
  const documents = data?.documents ?? []

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="mb-3 text-base font-semibold">자료 올리기</h2>
        <DocumentUploadZone botId={botId} />
      </div>

      <Separator />

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">등록된 자료</h2>
          <span className="text-sm tabular-nums text-muted-foreground">
            총 {data?.total ?? 0}건
          </span>
        </div>
        {isError ? (
          <ErrorState
            title="자료 목록을 불러오지 못했습니다"
            error={error}
            onRetry={() => refetch()}
          />
        ) : (
          <DocumentTable botId={botId} documents={documents} isLoading={isLoading} />
        )}
      </div>
    </div>
  )
}
