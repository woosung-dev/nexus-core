import { Suspense } from "react"

import { PageHeader } from "@/components/common/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { UnansweredBoard } from "@/features/unanswered/components/unanswered-board"

/**
 * 못 답한 질문 페이지.
 *
 * 챗봇이 답하지 못한 질문을 빈도순으로 보여 준다 — 「무엇부터 채울지」를 이 순서가 정한다.
 * 관리자는 각 질문이 어느 트랙의 일인지만 찍으면 된다.
 */
export default function UnansweredPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="못 답한 질문"
        description={
          <>
            챗봇이 답하지 못한 질문을 <b>많이 물어본 순서</b>로 보여 줍니다. 위에서부터
            채우면 됩니다.
            <br />각 질문이 <b>문서가 없어서</b>인지, <b>있는데 못 찾아서</b>인지,{" "}
            <b>문서가 틀려서</b>인지 찍어 주세요. 고칠 곳이 서로 다릅니다.
          </>
        }
      />
      {/* 보드가 `?bot_id=` 를 읽는다 — useSearchParams 는 Suspense 경계가 필요하다. */}
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <UnansweredBoard />
      </Suspense>
    </div>
  )
}
