"use client";

import { useState } from "react";
import { ChatHistoryFilter } from "@/features/chats/components/ChatHistoryFilter";
import { ChatHistoryList } from "@/features/chats/components/ChatHistoryList";
import { ChatDetailSheet } from "@/features/chats/components/ChatDetailSheet";
import { FeedbackMessageList } from "@/features/chats/components/FeedbackMessageList";
import { ChatFilter } from "@/features/chats/schemas";
import { useChatSessions } from "@/features/chats/hooks";
import { MessageSquareShare } from "lucide-react";
import { ErrorState } from "@/components/common/error-state";
import { PageHeader } from "@/components/common/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ChatsPage() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [filters, setFilters] = useState<ChatFilter>({
    page: 1,
    pageSize: 10,
  });

  const [activeTab, setActiveTab] = useState<"session" | "feedback">("session");
  const [feedbackSessionFilter, setFeedbackSessionFilter] = useState<{
    id: number;
    title: string;
  } | null>(null);

  // [3단계] 수동 fetch → React Query 훅으로 교체 (Thin Component 복원)
  // isError 를 안 받으면 서버가 죽어도 「기록이 없습니다」로 보인다.
  const { data, isLoading, isError, error, refetch } = useChatSessions(filters);
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

  const handleViewFeedback = (sessionId: number, sessionTitle: string) => {
    setFeedbackSessionFilter({ id: sessionId, title: sessionTitle });
    setActiveTab("feedback");
  };

  return (
    <div className="flex-1 space-y-6">
      <PageHeader
        title="대화 기록"
        description="사용자와 챗봇 간의 모든 대화 기록을 모니터링합니다."
      />

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as "session" | "feedback")}
        className="space-y-6"
      >
        <TabsList className="w-full max-w-[400px]">
          <TabsTrigger value="session" className="flex-1">
            전체 대화 세션
          </TabsTrigger>
          <TabsTrigger value="feedback" className="flex-1">
            <MessageSquareShare className="size-4" aria-hidden />
            피드백 포커스
          </TabsTrigger>
        </TabsList>

        <TabsContent value="session" className="m-0 space-y-6">
          <ChatHistoryFilter onFilterChange={handleFilterChange} />

          {isError ? (
            <ErrorState
              title="대화 기록을 불러오지 못했습니다"
              error={error}
              onRetry={() => refetch()}
            />
          ) : (
            <ChatHistoryList
              items={sessions}
              isLoading={isLoading}
              total={total}
              page={filters.page || 1}
              pageSize={filters.pageSize || 10}
              onPageChange={handlePageChange}
              onRowClick={setSelectedSessionId}
              onViewFeedback={handleViewFeedback}
            />
          )}
        </TabsContent>

        <TabsContent value="feedback" className="m-0">
          <FeedbackMessageList
            onRowClick={setSelectedSessionId}
            sessionIdFilter={feedbackSessionFilter?.id ?? null}
            sessionTitleFilter={feedbackSessionFilter?.title ?? null}
            onClearSessionFilter={() => setFeedbackSessionFilter(null)}
          />
        </TabsContent>
      </Tabs>

      <ChatDetailSheet
        sessionId={selectedSessionId}
        onClose={() => setSelectedSessionId(null)}
      />
    </div>
  );
}
