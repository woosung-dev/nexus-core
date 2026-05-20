"use client";

// 채팅 공유 셸. sessionId 가 있을 때만 ChatArea/ChatInput 을 렌더. 나머지 상태(빈 /chat, 세션 생성
// 중인 /chat/new/[bot_id])는 각각의 page 가 children 으로 자기 UI 를 보낸다.
import { useState } from "react";
import { useParams } from "next/navigation";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

export function ChatLayout({ children }: { children?: React.ReactNode }) {
  // /chat/[session_id] → { session_id }, /chat/new/[bot_id] → { bot_id }, /chat → {}
  const params = useParams<{ session_id?: string; bot_id?: string }>();
  const sessionId = params?.session_id;
  const botId = params?.bot_id;
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
        <ChatHeader onMenuClick={() => setSidebarOpen(true)} sessionId={sessionId} botId={botId} />
        {sessionId ? (
          <>
            <ChatArea sessionId={sessionId} />
            <ChatInput sessionId={sessionId} />
          </>
        ) : (
          // sessionId 없을 때(/chat 또는 /chat/new/[bot_id]) page 가 자체 UI 를 children 으로 제공
          children
        )}
      </main>
    </div>
  );
}
