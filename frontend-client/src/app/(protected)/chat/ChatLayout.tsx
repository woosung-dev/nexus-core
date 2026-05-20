"use client";

// 채팅 공유 셸. activeSessionId 가 있을 때만 ChatArea/ChatInput 을 렌더.
// sessionId 출처는 useParams 가 아니라 useChatStore.activeSessionId — Gemini 스타일 in-place URL
// 전환(history.replaceState) 후에도 ChatLayout 이 마운트 된 채 즉시 채팅 UI 로 전환 가능하게 하기 위함.
// catch-all page.tsx 가 URL → store 를 동기화하고, 본 레이아웃은 store 만 구독한다.
import { useState } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useChatStore } from "@/store/useChatStore";

export function ChatLayout({ children }: { children?: React.ReactNode }) {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex bg-slate-50 h-dvh overflow-hidden selection:bg-amber-200">
      <div className="hidden lg:block h-full">
        <ChatSidebar />
      </div>

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="p-0 border-r border-zinc-200 w-80 bg-slate-50">
          <SheetTitle className="sr-only">채팅 메뉴</SheetTitle>
          <ChatSidebar className="w-full border-r-0" />
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col h-full relative z-10 w-full min-w-0">
        <ChatHeader onMenuClick={() => setSidebarOpen(true)} sessionId={activeSessionId ?? undefined} />
        {activeSessionId ? (
          <>
            <ChatArea sessionId={activeSessionId} />
            <ChatInput sessionId={activeSessionId} />
          </>
        ) : (
          // activeSessionId 가 비어있을 때(빈 상태 또는 신규 세션 생성 중) catch-all page 가 children 으로 제공한 UI 표시
          children
        )}
      </main>
    </div>
  );
}
