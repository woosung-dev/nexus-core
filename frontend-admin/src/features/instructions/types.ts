// 지침 빌더 API 응답과 요청에 사용하는 타입 정의.
export type ExamplePair = {
  input: string
  output: string
}

export type InstructionGenerateResponse = {
  system_prompt: string
}

export type Citation = {
  title?: string | null
  content?: string | null
  approximate?: boolean | null
  uri?: string | null
  page_number?: number | null
  cite_count?: number | null
}

export type InstructionPreviewResponse = {
  answer: string
  citations: Citation[]
  followups: string[]
}

export type BotInstruction = {
  id: number
  bot_id: number | null
  name: string
  description: string
  role: string
  goal: string
  tone: string
  audience: string
  constraints: string
  dos: string[]
  donts: string[]
  examples: ExamplePair[]
  system_prompt: string
  llm_model: string
  version: number
  is_applied: boolean
  created_at: string
  updated_at: string
}

export type BotInstructionListResponse = {
  instructions: BotInstruction[]
  total: number
}
