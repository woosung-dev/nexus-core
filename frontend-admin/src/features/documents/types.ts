/**
 * 문서 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/rag.py의 Pydantic 스키마를 기반으로 작성.
 */

// GET /api/v1/admin/bots/:bot_id/documents (개별 문서)
export type DocumentInfo = {
  file_id: string
  display_name: string
  created_at: string | null
  // "completed" | "in_progress" | "queued" | "failed" | "unknown"
  status: string | null
  size_bytes: number | null
}

// GET /api/v1/admin/bots/:bot_id/documents (목록)
export type DocumentListResponse = {
  bot_id: number
  documents: DocumentInfo[]
  total: number
}

// POST /api/v1/admin/bots/:bot_id/documents (업로드 응답)
export type DocumentUploadResponse = {
  file_name: string
  display_name: string
  bot_id: number
  message: string
}
