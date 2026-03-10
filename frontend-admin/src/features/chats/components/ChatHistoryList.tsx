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
import { Button } from "@/components/ui/button";
import { MessageSquare, Calendar, ChevronLeft, ChevronRight, ThumbsUp, ThumbsDown } from "lucide-react";

interface ChatHistoryListProps {
  items: ChatSession[];
  isLoading: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onRowClick?: (sessionId: number) => void;
}

export function ChatHistoryList({ items, isLoading, total, page, pageSize, onPageChange, onRowClick }: ChatHistoryListProps) {
  const totalPages = Math.ceil(total / pageSize) || 1;

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 w-full animate-pulse bg-zinc-100/80 rounded-xl" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white border border-zinc-100 rounded-xl p-12 text-center text-zinc-500 shadow-sm">
        <MessageSquare className="w-12 h-12 mx-auto mb-4 text-zinc-300 opacity-50" />
        <p>조건에 맞는 대화 기록이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-white border border-zinc-100 rounded-xl shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-zinc-50/50">
            <TableRow>
              <TableHead className="w-[80px] font-semibold text-zinc-600 text-center">ID</TableHead>
              <TableHead className="w-[150px] font-semibold text-zinc-600">봇 (Bot)</TableHead>
              <TableHead className="w-[200px] font-semibold text-zinc-600">사용자 (User)</TableHead>
              <TableHead className="font-semibold text-zinc-600">제목</TableHead>
              <TableHead className="w-[140px] font-semibold text-zinc-600 text-center">반응</TableHead>
              <TableHead className="w-[140px] font-semibold text-zinc-600 text-right pr-4">일시</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((session) => (
              <TableRow 
                key={session.id} 
                className="hover:bg-zinc-50 transition-colors cursor-pointer"
                onClick={() => onRowClick?.(session.id)}
              >
                <TableCell className="font-medium text-zinc-900 text-center">#{session.id}</TableCell>
                <TableCell>
                  <span className="font-medium text-amber-600">{session.bot_name || "알 수 없음"}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-zinc-600">{session.user_email || "익명"}</span>
                </TableCell>
                <TableCell className="text-zinc-700">{session.title}</TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    {session.like_count ? (
                      <span className="flex items-center text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
                        <ThumbsUp className="w-3 h-3 mr-1" /> {session.like_count}
                      </span>
                    ) : null}
                    {session.dislike_count ? (
                      <span className="flex items-center text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-100">
                        <ThumbsDown className="w-3 h-3 mr-1" /> {session.dislike_count}
                      </span>
                    ) : null}
                    {!session.like_count && !session.dislike_count && (
                      <span className="text-zinc-300 text-xs">-</span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right pr-4">
                  <div className="flex items-center justify-end text-zinc-500 text-sm">
                    <Calendar className="w-3.5 h-3.5 mr-1.5" />
                    {new Date(session.created_at).toLocaleDateString()}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between px-2">
        <p className="text-sm text-zinc-500">
          총 <span className="font-medium text-zinc-900">{total}</span>개의 기록 중 {(page - 1) * pageSize + (total > 0 ? 1 : 0)}-{Math.min(page * pageSize, total)}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            이전
          </Button>
          <span className="text-sm text-zinc-600 font-medium px-2">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            다음
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
