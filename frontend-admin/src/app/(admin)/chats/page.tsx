"use client";

import { useState } from "react";
import { ChatHistoryFilter } from "@/features/chats/components/ChatHistoryFilter";
import { ChatHistoryList } from "@/features/chats/components/ChatHistoryList";
import { ChatDetailSheet } from "@/features/chats/components/ChatDetailSheet";
import { FeedbackMessageList } from "@/features/chats/components/FeedbackMessageList";
import { ChatFilter } from "@/features/chats/schemas";
import { useChatSessions } from "@/features/chats/hooks";
import { MessageSquare, MessageSquareShare } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ChatsPage() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [filters, setFilters] = useState<ChatFilter>({
    page: 1,
    pageSize: 10,
  });

  // [3단계] 수동 fetch → React Query 훅으로 교체 (Thin Component 복원)
  const { data, isLoading } = useChatSessions(filters);
  const sessions = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleFilterChange = (newFilters: ChatFilter) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: newFilters.page ?? 1,
    }));
  };

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  return (
    <div className="flex-1 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-zinc-900 flex items-center gap-2">
            <MessageSquare className="w-8 h-8 text-amber-500" />
            대화 기록
          </h2>
          <p className="text-zinc-500 mt-1">사용자와 챗봇 간의 모든 대화 기록을 모니터링합니다.</p>
        </div>
      </div>

      <Tabs defaultValue="session" className="space-y-6">
        <TabsList className="bg-white border border-zinc-200 p-1 w-full max-w-[400px]">
          <TabsTrigger value="session" className="flex-1 data-[state=active]:bg-zinc-100 data-[state=active]:text-zinc-900 rounded-sm">
            전체 대화 세션
          </TabsTrigger>
          <TabsTrigger value="feedback" className="flex-1 data-[state=active]:bg-zinc-100 data-[state=active]:text-amber-600 rounded-sm">
            <MessageSquareShare className="w-4 h-4 mr-2" />
            피드백 포커스
          </TabsTrigger>
        </TabsList>

        <TabsContent value="session" className="m-0 space-y-6">
          <ChatHistoryFilter onFilterChange={handleFilterChange} />

          <ChatHistoryList
            items={sessions}
            isLoading={isLoading}
            total={total}
            page={filters.page || 1}
            pageSize={filters.pageSize || 10}
            onPageChange={handlePageChange}
            onRowClick={setSelectedSessionId}
          />
        </TabsContent>

        <TabsContent value="feedback" className="m-0">
          <FeedbackMessageList onRowClick={setSelectedSessionId} />
        </TabsContent>
      </Tabs>

      <ChatDetailSheet
        sessionId={selectedSessionId}
        onClose={() => setSelectedSessionId(null)}
      />
    </div>
  );
}

