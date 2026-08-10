"use client"

/**
 * 한 질문 그룹의 개별 발생.
 *
 * **대화 전문은 여기서 안 편다.** 실사용자 질문에는 성폭력·이혼 같은 사정이 섞여 있다.
 * 전문이 필요하면 `/chats` 로 넘어가게 링크만 걸어 기존 화면에 위임한다 —
 * 노출 지점을 늘리지 않는 것이 이 화면의 규약이다.
 */
import Link from "next/link"
import { ExternalLink, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

import { REASON_EFFECT, REASON_LABEL, REASON_STYLE } from "../constants"
import { useUnansweredOccurrences } from "../hooks"
import type { UnansweredGroup } from "../types"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function UnansweredDetailSheet({
  group,
  onClose,
}: {
  group: UnansweredGroup | null
  onClose: () => void
}) {
  const { data, isLoading, isError, error } = useUnansweredOccurrences(
    group?.question_norm ?? null
  )

  return (
    <Sheet open={group !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-[560px]">
        <SheetHeader>
          <SheetTitle className="text-base leading-snug">
            {group?.question_text ?? ""}
          </SheetTitle>
          <SheetDescription>
            같은 질문이 {group?.count ?? 0}번 들어왔습니다. 아래는 개별 발생입니다.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3 px-4 pb-6">
          {isLoading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> 불러오는 중
            </div>
          ) : isError ? (
            <p className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
              발생 기록을 불러오지 못했습니다: {(error as Error)?.message}
            </p>
          ) : !data?.items.length ? (
            <p className="rounded-md border p-8 text-center text-sm text-muted-foreground">
              보존 기간 안에 남은 발생 기록이 없습니다.
            </p>
          ) : (
            data.items.map((occurrence) => {
              const missing = (occurrence.detail?.missing as string[]) ?? []
              const srcIds = (occurrence.detail?.src_ids as string[]) ?? []
              return (
                <div key={occurrence.id} className="rounded-md border p-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <Badge
                      variant="secondary"
                      className={`text-[11px] ${REASON_STYLE[occurrence.reason]}`}
                    >
                      {REASON_LABEL[occurrence.reason]}
                    </Badge>
                    <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                      {formatDateTime(occurrence.created_at)}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-muted-foreground">
                    {REASON_EFFECT[occurrence.reason]}
                  </p>

                  {occurrence.question_text !== group?.question_text ? (
                    <p className="mt-2 leading-snug">{occurrence.question_text}</p>
                  ) : null}

                  {missing.length ? (
                    <p className="mt-2 text-xs">
                      <span className="text-muted-foreground">되물을 것: </span>
                      {missing.join(" · ")}
                    </p>
                  ) : null}

                  {srcIds.length ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      주입된 원문 {srcIds.length}건: {srcIds.slice(0, 6).join(", ")}
                      {srcIds.length > 6 ? " …" : ""}
                    </p>
                  ) : null}

                  {occurrence.session_id ? (
                    <Link
                      href="/chats"
                      className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground hover:underline"
                    >
                      대화 #{occurrence.session_id} 보기
                      <ExternalLink className="size-3" aria-hidden />
                    </Link>
                  ) : null}
                </div>
              )
            })
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
