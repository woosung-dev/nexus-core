import { PageHeader } from "@/components/common/page-header"
import { WikiWorkbench } from "@/features/llm-wiki/components/wiki-workbench"

/**
 * LLM 위키 — 규정집·용어집·공문·실측을 하나의 상호연결 문서로 컴파일한 층.
 * 챗봇은 원문이 아니라 이 위키를 참조한다.
 */
export default function WikiPage() {
  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="지식 위키"
        description={
          <>
            규정집·용어집·공문·실측을 하나의 문서로 엮습니다. 자료를 넣으면 관련 페이지가 함께
            갱신되고, 문서끼리 어긋난 자리와 답이 없는 자리가 드러납니다.
            <br />
            <b className="text-foreground">모든 문장에 원문이 붙어 있습니다.</b> 누르시면 그
            자리에서 대조하실 수 있습니다.
          </>
        }
      />
      <WikiWorkbench />
    </div>
  )
}
