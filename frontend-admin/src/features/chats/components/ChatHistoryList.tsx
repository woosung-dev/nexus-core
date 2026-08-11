"use client";

import { ChatSession } from "../schemas";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { DataPagination } from "@/components/common/data-pagination";
import { EmptyState } from "@/components/common/empty-state";
import { MessageSquare, Calendar, ThumbsUp, ThumbsDown, Eye } from "lucide-react";

interface ChatHistoryListProps {
  items: ChatSession[];
  isLoading: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onRowClick?: (sessionId: number) => void;
  onViewFeedback?: (sessionId: number, sessionTitle: string) => void;
}

export function ChatHistoryList({ items, isLoading, total, page, pageSize, onPageChange, onRowClick, onViewFeedback }: ChatHistoryListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="조건에 맞는 대화 기록이 없습니다"
        description="필터를 지우면 전체 기록을 볼 수 있습니다."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[80px] text-center">ID</TableHead>
              <TableHead className="w-[150px]">봇</TableHead>
              <TableHead className="w-[200px]">사용자</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="w-[140px] text-center">반응</TableHead>
              <TableHead className="w-[140px] pr-4 text-right">일시</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((session) => (
              <TableRow
                key={session.id}
                // 행을 클릭으로만 열 수 있으면 키보드 사용자는 상세로 갈 길이 없다.
                tabIndex={0}
                role="button"
                aria-label={`${session.title} 대화 열기`}
                className="cursor-pointer"
                onClick={() => onRowClick?.(session.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onRowClick?.(session.id);
                  }
                }}
              >
                <TableCell className="text-center font-medium tabular-nums">#{session.id}</TableCell>
                <TableCell className="font-medium">{session.bot_name || "알 수 없음"}</TableCell>
                <TableCell className="text-muted-foreground">{session.user_email || "익명"}</TableCell>
                <TableCell>{session.title}</TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    {session.like_count ? (
                      <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-2xs font-medium tabular-nums">
                        <ThumbsUp className="size-3" aria-hidden /> {session.like_count}
                      </span>
                    ) : null}
                    {session.dislike_count ? (
                      <span className="inline-flex items-center gap-1 rounded-full border border-destructive/30 bg-destructive/5 px-2 py-0.5 text-2xs font-medium tabular-nums text-destructive">
                        <ThumbsDown className="size-3" aria-hidden /> {session.dislike_count}
                      </span>
                    ) : null}
                    {!session.like_count && !session.dislike_count && (
                      <span className="text-2xs text-muted-foreground">-</span>
                    )}
                    {(session.like_count || session.dislike_count) && onViewFeedback ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewFeedback(session.id, session.title);
                        }}
                        className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-2xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                        aria-label="이 대화의 피드백 보기"
                      >
                        <Eye className="size-3" aria-hidden />
                        보기
                      </button>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell className="pr-4 text-right">
                  <div className="flex items-center justify-end gap-1.5 text-muted-foreground">
                    <Calendar className="size-3.5" aria-hidden />
                    {new Date(session.created_at).toLocaleDateString()}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <DataPagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={onPageChange}
        unit="개"
      />
    </div>
  );
}
