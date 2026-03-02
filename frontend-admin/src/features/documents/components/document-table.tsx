"use client"

/**
 * 문서 목록 Data Table 컴포넌트.
 * 파일명, 크기, 업로드 날짜, 상태(Badge), 삭제 버튼을 표시한다.
 */
import { Loader2, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useDeleteDocument } from "@/features/documents/hooks"
import { DocumentStatusBadge } from "./document-status-badge"
import type { DocumentInfo } from "@/features/documents/types"

interface DocumentTableProps {
  botId: number
  documents: DocumentInfo[]
  isLoading: boolean
}

// 파일 크기를 읽기 좋은 문자열로 변환 (예: 1.2 MB)
function formatBytes(bytes: number | null): string {
  if (bytes === null) return "-"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// 날짜 문자열을 로컬 형식으로 변환
function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  })
}

// --- 삭제 버튼 셀 (훅 사용을 위해 별도 컴포넌트로 분리) ---
function DeleteDocumentButton({ botId, fileId, displayName }: { botId: number; fileId: string; displayName: string }) {
  const { mutate: deleteDoc, isPending } = useDeleteDocument(botId)

  function handleDelete() {
    if (confirm(`'${displayName}' 문서를 삭제하시겠습니까?`)) {
      deleteDoc(fileId)
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleDelete}
      disabled={isPending}
      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
    >
      {isPending
        ? <Loader2 className="h-4 w-4 animate-spin" />
        : <Trash2 className="h-4 w-4" />
      }
      <span className="sr-only">삭제</span>
    </Button>
  )
}

// --- 문서 목록 테이블 ---
export function DocumentTable({ botId, documents, isLoading }: DocumentTableProps) {
  return (
    <div className="overflow-hidden rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>파일명</TableHead>
            <TableHead className="w-[120px]">파일 크기</TableHead>
            <TableHead className="w-[180px]">업로드 날짜</TableHead>
            <TableHead className="w-[130px]">상태</TableHead>
            <TableHead className="w-[60px]" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* 로딩 */}
          {isLoading && (
            <TableRow>
              <TableCell colSpan={5} className="h-32 text-center">
                <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
              </TableCell>
            </TableRow>
          )}

          {/* 데이터 */}
          {!isLoading && documents.map((doc) => (
            <TableRow key={doc.file_id}>
              <TableCell className="font-medium">{doc.display_name}</TableCell>
              <TableCell className="text-muted-foreground text-sm">{formatBytes(doc.size_bytes)}</TableCell>
              <TableCell className="text-muted-foreground text-sm">{formatDate(doc.created_at)}</TableCell>
              <TableCell><DocumentStatusBadge status={doc.status} /></TableCell>
              <TableCell>
                <DeleteDocumentButton botId={botId} fileId={doc.file_id} displayName={doc.display_name} />
              </TableCell>
            </TableRow>
          ))}

          {/* 빈 상태 */}
          {!isLoading && documents.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="h-32 text-center text-sm text-muted-foreground">
                등록된 문서가 없습니다. 위에서 파일을 업로드해 주세요.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
