import { z } from "zod/v4"

// 허용 확장자
export const ALLOWED_EXTENSIONS = ["pdf", "txt", "csv"] as const
export const ALLOWED_EXTENSIONS_LABEL = "PDF, TXT, CSV"
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
