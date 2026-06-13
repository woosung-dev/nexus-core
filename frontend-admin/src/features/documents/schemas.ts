import { z } from "zod/v4"

// 허용 확장자 — Gemini File Search 지원 문서·데이터 형식.
// (코드/스크립트 .py·.js·.sh·.ps1·.php 등과 오디오·비디오는 RAG 용도상 비추라 제외)
export const ALLOWED_EXTENSIONS = [
  "pdf",
  "doc", "docx", "xls", "xlsx", "pptx", // MS Office
  "txt", "md", "html", "htm", "csv", "tsv", "rtf", // 텍스트·마크업
  "json", "xml", // 데이터
] as const
export const ALLOWED_EXTENSIONS_LABEL =
  "PDF · 오피스(doc/docx·xls/xlsx·pptx) · 텍스트(txt·md·html·csv·tsv·rtf) · 데이터(json·xml)"
// <input accept> 속성 — ALLOWED_EXTENSIONS 와 항상 동기화 (드리프트 방지)
export const ACCEPT_ATTR = ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",")
const MAX_FILE_SIZE_MB = 20
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

function getExtension(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() ?? ""
}

// --- 문서 업로드 폼 Zod 스키마 ---
export const uploadFormSchema = z.object({
  file: z
    .instanceof(File, { message: "파일을 선택해 주세요." })
    .refine(
      (file) => ALLOWED_EXTENSIONS.includes(getExtension(file.name) as (typeof ALLOWED_EXTENSIONS)[number]),
      { message: `${ALLOWED_EXTENSIONS_LABEL} 파일만 업로드 가능합니다.` }
    )
    .refine(
      (file) => file.size <= MAX_FILE_SIZE_BYTES,
      { message: `파일 크기는 ${MAX_FILE_SIZE_MB}MB 이하여야 합니다.` }
    ),
})

export type UploadFormValues = z.infer<typeof uploadFormSchema>
