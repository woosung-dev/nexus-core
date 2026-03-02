import { columns } from "@/features/bots/components/columns"
import { BotsDataTable } from "@/features/bots/components/bots-data-table"

/**
 * 봇 목록 페이지 (서버 컴포넌트).
 * 데이터 페칭은 BotsDataTable 내부에서 React Query(useBots)로 처리.
 */
export default function BotsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bots Management</h1>
        <p className="text-muted-foreground">
          등록된 AI 챗봇을 관리하고 새로운 봇을 생성합니다.
        </p>
      </div>
      <BotsDataTable columns={columns} />
    </div>
  )
}
