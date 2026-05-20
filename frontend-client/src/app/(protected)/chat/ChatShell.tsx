// 채팅 쉘 — 두 가지 상태만 처리한다:
//   empty: catch-all 의 children (안내 화면)
//   thread: ChatArea + 하단 ChatComposer
// /chat/new/{bot} 도 thread 의 빈 메시지 상태로 표현되어 입력칸이 처음부터 하단에 고정됨.
// (중앙→하단 모핑은 사용자가 어색하다고 해서 제거 — 이게 ChatGPT/Claude 의 표준 패턴이기도 함)
"use client";

import { useState } from "react";

import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useChat } from "./ChatProvider";

export function ChatShell({ children }: { children?: React.ReactNode }) {
  const { phase, sessionId, botId } = useChat();
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
        <ChatHeader
          onMenuClick={() => setSidebarOpen(true)}
          sessionId={sessionId ?? undefined}
          botId={botId ?? undefined}
        />

        {phase === "empty" ? (
          children
        ) : (
          <>
            <ChatArea sessionId={sessionId ?? undefined} />
            <ChatComposer />
          </>
        )}
      </main>
    </div>
  );
}
