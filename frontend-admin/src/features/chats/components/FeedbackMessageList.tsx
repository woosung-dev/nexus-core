// 어드민 - 피드백 포커스 탭: 사유 카테고리/자유텍스트 포함 메시지 목록 + 필터
"use client";

import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataPagination } from "@/components/common/data-pagination";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import {
  MessageSquare,
  Calendar,
  ThumbsUp,
  ThumbsDown,
  User,
  Bot,
  X,
} from "lucide-react";
import { useFeedbackMessages } from "../hooks";
import {
  ALL_REASON_LABELS,
  NEGATIVE_REASON_LABELS,
  POSITIVE_REASON_LABELS,
} from "../schemas";

interface FeedbackMessageListProps {
  onRowClick: (sessionId: number) => void;
  sessionIdFilter?: number | null;
  sessionTitleFilter?: string | null;
  onClearSessionFilter?: () => void;
}

export function FeedbackMessageList({
  onRowClick,
  sessionIdFilter,
  sessionTitleFilter,
  onClearSessionFilter,
}: FeedbackMessageListProps) {
  const [page, setPage] = useState(1);
  const [feedbackType, setFeedbackType] = useState<string>("all");
  const [reason, setReason] = useState<string>("all");
  const pageSize = 10;

  // 필터 변경 시 페이지 리셋
  useEffect(() => {
    setPage(1);
  }, [feedbackType, reason, sessionIdFilter]);

  const { data, isLoading, isError } = useFeedbackMessages({
    page,
    pageSize,
    feedback_type: feedbackType,
    reason,
    session_id: sessionIdFilter ?? undefined,
  });

  const items = data?.items || [];
  const total = data?.total || 0;

  if (isError) {
    return <ErrorState title="피드백을 불러오지 못했습니다" />;
  }

  return (
    <div className="space-y-3">
      {/* 필터 행 */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border bg-card p-3">
        <span className="text-sm text-muted-foreground">필터</span>
        <Select value={feedbackType} onValueChange={setFeedbackType}>
          <SelectTrigger className="w-[150px]" aria-label="피드백 종류">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">모든 피드백</SelectItem>
            <SelectItem value="up">좋아요</SelectItem>
            <SelectItem value="down">싫어요</SelectItem>
          </SelectContent>
        </Select>
        <Select value={reason} onValueChange={setReason}>
          <SelectTrigger className="w-[200px]" aria-label="사유">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">모든 사유</SelectItem>
            <SelectGroup>
              <SelectLabel>긍정 사유</SelectLabel>
              {Object.entries(POSITIVE_REASON_LABELS).map(([code, label]) => (
                <SelectItem key={`up-${code}`} value={code}>
                  {label}
                </SelectItem>
              ))}
            </SelectGroup>
            <SelectGroup>
              <SelectLabel>부정 사유</SelectLabel>
              {Object.entries(NEGATIVE_REASON_LABELS).map(([code, label]) => (
                <SelectItem key={`down-${code}`} value={code}>
                  {label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>

        {sessionIdFilter != null && (
          <div className="ml-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs">
            <span className="text-muted-foreground">세션 필터</span>
            <span className="font-medium">
              {sessionTitleFilter ?? `#${sessionIdFilter}`}
            </span>
            <button
              onClick={onClearSessionFilter}
              className="rounded-full p-0.5 hover:bg-accent"
              aria-label="세션 필터 해제"
            >
              <X className="size-3" aria-hidden />
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-col overflow-hidden rounded-md border">
        {/* 열이 일곱이라 좁은 화면에서는 가로로 민다. 페이지 자체가 밀리면 안 된다. */}
        <div className="min-h-[400px] overflow-x-auto">
          <Table className="w-full min-w-[1160px]">
            <TableHeader className="sticky top-0 z-10 bg-card">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[100px]">상태</TableHead>
                <TableHead className="w-[180px]">세션 / 봇</TableHead>
                <TableHead className="w-[180px]">사용자</TableHead>
                <TableHead className="min-w-[200px]">사용자 질문</TableHead>
                <TableHead className="min-w-[220px]">봇 응답</TableHead>
                <TableHead className="w-[220px]">사유</TableHead>
                <TableHead className="w-[140px] pr-4 text-right">일시</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-6 w-16 rounded-full" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24 mb-1" /><Skeleton className="h-3 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-full" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-full" /></TableCell>
                    <TableCell><Skeleton className="h-6 w-32" /></TableCell>
                    <TableCell className="text-right pr-4"><Skeleton className="h-4 w-20 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : items.length === 0 ? (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={7} className="p-0">
                    <EmptyState
                      icon={MessageSquare}
                      title="피드백을 받은 메시지가 없습니다"
                      description="필터를 지우면 전체 피드백을 볼 수 있습니다."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                items.map((msg) => {
                  const reasons = msg.feedback_reasons ?? [];
                  const comment = msg.feedback_comment ?? "";
                  const hasReason = reasons.length > 0 || comment.length > 0;
                  return (
                    <TableRow
                      key={msg.id}
                      className="cursor-pointer"
                      tabIndex={0}
                      role="button"
                      aria-label={`${msg.session_title ?? "대화"} 열기`}
                      onClick={() => onRowClick(msg.session_id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onRowClick(msg.session_id);
                        }
                      }}
                    >
                      <TableCell className="py-4 align-top">
                        {msg.feedback === "up" ? (
                          <span className="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium">
                            <ThumbsUp className="size-3.5" aria-hidden /> 좋아요
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full border border-destructive/30 bg-destructive/5 px-2.5 py-1 text-xs font-medium text-destructive">
                            <ThumbsDown className="size-3.5" aria-hidden /> 싫어요
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="py-4 align-top">
                        <div className="mb-1.5 flex items-center gap-1.5">
                          <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                          <span className="max-w-[140px] truncate text-sm font-medium" title={msg.session_title || ""}>
                            {msg.session_title}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Bot className="size-3 shrink-0 text-muted-foreground" aria-hidden />
                          <span className="max-w-[140px] truncate text-xs text-muted-foreground" title={msg.bot_name || ""}>
                            {msg.bot_name || "알 수 없는 봇"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="py-4 align-top">
                        <div className="flex items-center gap-1.5">
                          <User className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                          <span className="max-w-[150px] truncate text-sm text-muted-foreground" title={msg.user_email || "익명"}>
                            {msg.user_email || "익명"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="py-4 align-top">
                        {msg.user_question ? (
                          <div
                            className="line-clamp-3 overflow-hidden text-xs leading-relaxed break-all whitespace-normal text-muted-foreground"
                            title={msg.user_question}
                          >
                            {msg.user_question}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">직전 질문 없음</span>
                        )}
                      </TableCell>
                      <TableCell className="py-4 align-top">
                        <div
                          className="line-clamp-3 overflow-hidden text-sm leading-relaxed break-all whitespace-normal"
                          title={msg.content}
                        >
                          {msg.content}
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[240px] py-4 align-top">
                        {hasReason ? (
                          <div className="flex flex-col gap-1.5">
                            {reasons.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {reasons.map((code) => (
                                  <span
                                    key={code}
                                    className="inline-block rounded border bg-muted px-2 py-0.5 text-2xs"
                                  >
                                    {ALL_REASON_LABELS[code] ?? code}
                                  </span>
                                ))}
                              </div>
                            )}
                            {comment && (
                              <div
                                className="line-clamp-2 text-xs break-all text-muted-foreground"
                                title={comment}
                              >
                                &ldquo;{comment}&rdquo;
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">사유 입력 안 함</span>
                        )}
                      </TableCell>
                      <TableCell className="py-4 pr-4 text-right align-top">
                        <div className="flex items-center justify-end gap-1.5 text-sm text-muted-foreground">
                          <Calendar className="size-3.5" aria-hidden />
                          {new Date(msg.created_at).toLocaleDateString()}
                        </div>
                        <div className="mt-0.5 text-xs tabular-nums text-muted-foreground">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        <div className="mt-auto border-t p-3">
          <DataPagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}
