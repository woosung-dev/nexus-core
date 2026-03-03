import { FaqDataTable } from "@/features/faqs/components/faq-data-table"

/**
 * FAQ Override 관리 페이지 (서버 컴포넌트).
 * 데이터 페칭은 FaqDataTable 내부에서 React Query(useFaqs)로 처리.
 */
export default function FaqsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">FAQ Override 관리</h1>
        <p className="text-muted-foreground">
          특정 질문에 대해 AI 추론 대신 관리자가 정한 우선순위 답변을 관리합니다.
        </p>
      </div>
      <FaqDataTable />
    </div>
  )
}
