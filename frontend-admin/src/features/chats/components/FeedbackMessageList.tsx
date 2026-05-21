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
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  MessageSquare,
  Calendar,
  ChevronLeft,
  ChevronRight,
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
  const totalPages = Math.ceil(total / pageSize) || 1;

  if (isError) {
    return (
      <div className="bg-white rounded-xl border border-zinc-100 shadow-sm p-10 text-center">
        <p className="text-zinc-500">피드백 데이터를 불러오는데 실패했습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 필터 행 */}
      <div className="bg-white p-3 rounded-xl border border-zinc-100 shadow-sm flex flex-wrap items-center gap-3">
        <span className="text-sm text-zinc-500">필터:</span>
        <select
          value={feedbackType}
          onChange={(e) => setFeedbackType(e.target.value)}
          className="h-9 px-3 text-sm rounded-md border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
        >
          <option value="all">모든 피드백</option>
          <option value="up">👍 좋아요</option>
          <option value="down">👎 싫어요</option>
        </select>
        <select
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="h-9 px-3 text-sm rounded-md border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
        >
          <option value="all">모든 사유</option>
          <optgroup label="긍정 사유">
            {Object.entries(POSITIVE_REASON_LABELS).map(([code, label]) => (
              <option key={`up-${code}`} value={code}>
                {label}
              </option>
            ))}
          </optgroup>
          <optgroup label="부정 사유">
            {Object.entries(NEGATIVE_REASON_LABELS).map(([code, label]) => (
              <option key={`down-${code}`} value={code}>
                {label}
              </option>
            ))}
          </optgroup>
        </select>

        {sessionIdFilter != null && (
          <div className="inline-flex items-center gap-1.5 ml-auto px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-full text-xs">
            <span className="text-zinc-500">세션 필터:</span>
            <span className="font-medium text-amber-700">
              {sessionTitleFilter ?? `#${sessionIdFilter}`}
            </span>
            <button
              onClick={onClearSessionFilter}
              className="p-0.5 hover:bg-amber-100 rounded-full"
              aria-label="세션 필터 해제"
            >
              <X className="w-3 h-3 text-amber-700" />
            </button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-zinc-100 shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto min-h-[400px]">
          <Table className="w-full min-w-[1160px]">
            <TableHeader className="bg-zinc-50/80 sticky top-0 z-10 backdrop-blur-sm">
              <TableRow className="hover:bg-transparent border-zinc-100">
                <TableHead className="w-[100px] font-semibold text-zinc-600">상태</TableHead>
                <TableHead className="w-[180px] font-semibold text-zinc-600">세션/봇 정보</TableHead>
                <TableHead className="w-[180px] font-semibold text-zinc-600">사용자</TableHead>
                <TableHead className="min-w-[200px] font-semibold text-zinc-600">사용자 질문</TableHead>
                <TableHead className="min-w-[220px] font-semibold text-zinc-600">피드백 내용 (봇 응답)</TableHead>
                <TableHead className="w-[220px] font-semibold text-zinc-600">사유</TableHead>
                <TableHead className="w-[140px] font-semibold text-zinc-600 text-right pr-4">일시</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i} className="border-zinc-50">
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
                <TableRow>
                  <TableCell colSpan={7} className="h-48 text-center text-zinc-500">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <MessageSquare className="w-8 h-8 text-zinc-300" />
                      <p>피드백을 받은 메시지가 없습니다.</p>
                    </div>
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
                      className="group hover:bg-zinc-50 cursor-pointer transition-colors border-zinc-50"
                      onClick={() => onRowClick(msg.session_id)}
                    >
                      <TableCell className="py-5 align-top">
                        {msg.feedback === "up" ? (
                          <span className="inline-flex items-center text-xs font-medium text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-100">
                            <ThumbsUp className="w-3.5 h-3.5 mr-1" /> 좋아요
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-medium text-red-600 bg-red-50 px-2.5 py-1 rounded-full border border-red-100">
                            <ThumbsDown className="w-3.5 h-3.5 mr-1" /> 싫어요
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="py-5 align-top">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <MessageSquare className="w-3.5 h-3.5 text-zinc-400" />
                          <span className="text-sm font-medium text-zinc-900 truncate max-w-[140px]" title={msg.session_title || ""}>
                            {msg.session_title}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Bot className="w-3 h-3 text-amber-500" />
                          <span className="text-xs text-zinc-500 truncate max-w-[140px]" title={msg.bot_name || ""}>
                            {msg.bot_name || "알 수 없는 봇"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="py-5 align-top">
                        <div className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-zinc-400" />
                          <span className="text-sm text-zinc-600 truncate max-w-[150px]" title={msg.user_email || "익명"}>
                            {msg.user_email || "익명"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="py-5 align-top">
                        {msg.user_question ? (
                          <div
                            className="text-[13px] text-zinc-600 font-normal leading-relaxed whitespace-normal break-all line-clamp-3 overflow-hidden"
                            title={msg.user_question}
                          >
                            {msg.user_question}
                          </div>
                        ) : (
                          <span className="text-xs text-zinc-400 italic">(직전 질문 없음)</span>
                        )}
                      </TableCell>
                      <TableCell className="py-5 align-top">
                        <div
                          className="text-[14px] text-zinc-700 font-normal leading-relaxed whitespace-normal break-all line-clamp-3 overflow-hidden group-hover:text-zinc-900 transition-colors"
                          title={msg.content}
                        >
                          {msg.content}
                        </div>
                      </TableCell>
                      <TableCell className="py-5 align-top max-w-[240px]">
                        {hasReason ? (
                          <div className="flex flex-col gap-1.5">
                            {reasons.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {reasons.map((code) => (
                                  <span
                                    key={code}
                                    className="inline-block text-[11px] bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded"
                                  >
                                    {ALL_REASON_LABELS[code] ?? code}
                                  </span>
                                ))}
                              </div>
                            )}
                            {comment && (
                              <div
                                className="text-[12px] text-zinc-500 line-clamp-2 break-all"
                                title={comment}
                              >
                                &ldquo;{comment}&rdquo;
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-zinc-400 italic">(사유 입력 안 함)</span>
                        )}
                      </TableCell>
                      <TableCell className="py-5 align-top text-right pr-4 text-zinc-400">
                        <div className="flex items-center justify-end text-zinc-500 text-sm">
                          <Calendar className="w-3.5 h-3.5 mr-1.5" />
                          {new Date(msg.created_at).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-zinc-400 mt-0.5">
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

        <div className="border-t border-zinc-100 p-4 flex items-center justify-between bg-zinc-50/50 mt-auto">
          <span className="text-sm text-zinc-500">
            총 <span className="font-medium text-zinc-900">{total}</span>개의 데이터
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
              className="h-8 text-zinc-600 bg-white"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              이전
            </Button>
            <div className="flex items-center px-4 text-sm font-medium text-zinc-600">
              {page} / {totalPages}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || isLoading}
              className="h-8 text-zinc-600 bg-white"
            >
              다음
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
