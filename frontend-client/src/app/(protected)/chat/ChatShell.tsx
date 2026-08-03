// 채팅 쉘 — 두 가지 상태만 처리한다:
//   empty: catch-all 의 children (안내 화면)
//   thread: ChatArea + 하단 ChatComposer
// /chat/new/{bot} 도 thread 의 빈 메시지 상태로 표현되어 입력칸이 처음부터 하단에 고정됨.
// (중앙→하단 모핑은 사용자가 어색하다고 해서 제거 — 이게 ChatGPT/Claude 의 표준 패턴이기도 함)
"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { ClarificationPrototype } from "@/components/chat/ClarificationPrototype";
import { ClarificationCard } from "@/components/chat/ClarificationCard";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useChat } from "./ChatProvider";

export function ChatShell({ children }: { children?: React.ReactNode }) {
  const { phase, sessionId, botId } = useChat();
  const searchParams = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const showClarificationPrototype =
    process.env.NODE_ENV !== "production" &&
    searchParams.get("clarify-prototype") === "1" &&
    Boolean(botId);

  // 익명 테스트 경로는 대화 이력/봇 헤더 API를 호출하지 않는다.
  // 일반 인증 흐름과 실제 채팅 API는 이 분기 밖에서 그대로 보호된다.
  if (showClarificationPrototype) {
    return (
      <div className="flex h-dvh overflow-hidden bg-slate-50">
        <main className="flex min-w-0 flex-1 flex-col">
          <ClarificationPrototype botId={botId} />
        </main>
      </div>
    );
  }

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
            <ClarificationCard />
            <ChatComposer />
          </>
        )}
      </main>
    </div>
  );
}
