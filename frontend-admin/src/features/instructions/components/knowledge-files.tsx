"use client"

// 선택한 봇의 RAG 지식 파일을 지침 화면에서 관리한다.
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { DocumentTable } from "@/features/documents/components/document-table"
import { DocumentUploadZone } from "@/features/documents/components/document-upload-zone"
import { useDocuments } from "@/features/documents/hooks"

export function KnowledgeFiles({ botId }: { botId: number | null }) {
  const { data, isLoading } = useDocuments(botId)

  return (
    <Collapsible className="rounded-lg border p-4">
      <CollapsibleTrigger className="text-sm font-medium">지식 파일 (RAG)</CollapsibleTrigger>
      <CollapsibleContent className="space-y-4 pt-4">
        {botId === null ? (
          <div className="rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
            먼저 대상 봇을 선택하면 지식 파일(RAG)을 첨부할 수 있어요.
          </div>
        ) : (
          <>
            <DocumentUploadZone botId={botId} />
            <DocumentTable botId={botId} documents={data?.documents ?? []} isLoading={isLoading} />
          </>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
