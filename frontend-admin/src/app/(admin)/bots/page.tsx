import { PageHeader } from "@/components/common/page-header"
import { columns } from "@/features/bots/components/columns"
import { BotsDataTable } from "@/features/bots/components/bots-data-table"

/**
 * 봇 목록 페이지 (서버 컴포넌트).
 * 데이터 페칭은 BotsDataTable 내부에서 React Query(useBots)로 처리.
 */
export default function BotsPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* 제목은 사이드바 이름과 같아야 한다 — 다르면 같은 화면인지 매번 확인하게 된다. */}
      <PageHeader
        title="봇 목록"
        description="봇을 만들고, 각 봇의 답변 설정과 자료를 관리합니다."
      />
      <BotsDataTable columns={columns} />
    </div>
  )
}
