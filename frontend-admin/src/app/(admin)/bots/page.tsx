import type { Bot } from "@/features/bots/schemas"
import { columns } from "@/features/bots/components/columns"
import { BotsDataTable } from "@/features/bots/components/bots-data-table"

// --- Mock 데이터 (추후 API fetch로 교체) ---
const mockBots: Bot[] = [
  {
    id: "bot-001",
    name: "고객 상담 봇",
    description: "일반 고객 문의에 응답하는 AI 챗봇입니다.",
    tags: ["고객", "상담", "FAQ"],
    is_active: true,
    system_prompt: "당신은 친절한 고객 상담 전문가입니다.",
    llm_model: "gpt-4o",
    created_at: "2025-01-15T09:00:00Z",
    updated_at: "2025-02-01T10:30:00Z",
  },
  {
    id: "bot-002",
    name: "기술 지원 봇",
    description: "기술 관련 문의를 처리하는 전문 봇입니다.",
    tags: ["기술", "IT", "지원"],
    is_active: true,
    system_prompt: "당신은 IT 기술 지원 전문가입니다.",
    llm_model: "gemini-2.5-flash",
    created_at: "2025-01-20T14:00:00Z",
    updated_at: "2025-02-10T08:00:00Z",
  },
  {
    id: "bot-003",
    name: "마케팅 어시스턴트",
    description: "마케팅 콘텐츠 생성을 도와주는 봇입니다.",
    tags: ["마케팅", "콘텐츠"],
    is_active: false,
    system_prompt: "당신은 창의적인 마케팅 전문가입니다.",
    llm_model: "gpt-4o-mini",
    created_at: "2025-02-01T11:00:00Z",
    updated_at: "2025-02-15T16:00:00Z",
  },
  {
    id: "bot-004",
    name: "HR 도우미",
    description: "인사 관련 질문에 답변하는 봇입니다.",
    tags: ["HR", "인사", "복지"],
    is_active: true,
    system_prompt: "당신은 HR 전문가입니다.",
    llm_model: "gemini-2.5-pro",
    created_at: "2025-02-05T10:00:00Z",
    updated_at: "2025-02-20T09:00:00Z",
  },
  {
    id: "bot-005",
    name: "교육 튜터 봇",
    description: null,
    tags: ["교육"],
    is_active: true,
    system_prompt: "당신은 친절한 교육 튜터입니다.",
    llm_model: "gpt-4o",
    created_at: "2025-02-10T13:00:00Z",
    updated_at: "2025-02-25T11:00:00Z",
  },
]

export default function BotsPage() {
  // TODO: 추후 React Query useQuery로 API fetch 교체
  const bots = mockBots

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bots Management</h1>
        <p className="text-muted-foreground">
          등록된 AI 챗봇을 관리하고 새로운 봇을 생성합니다.
        </p>
      </div>
      <BotsDataTable columns={columns} data={bots} />
    </div>
  )
}
