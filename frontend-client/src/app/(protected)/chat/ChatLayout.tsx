"use client";

// 채팅 공유 셸 — sessionId 의 단일 진실원은 URL (useParams). store 는 오직 `/chat/new/{botId}` 에서
// POST 응답 직후 history.replaceState 로 URL 만 바꾼 짧은 윈도우 동안의 fallback 으로만 쓰인다.
// 이렇게 URL-first 우선순위를 유지하면 (a) 직접 URL 진입 시 첫 paint 깜빡임 없음, (b) 사이드바
// Link 클릭 시 stale store 가 한 프레임 비춰지지 않음 — 동시에 history API 직후의 짧은 윈도우는
// store override 로 자연스럽게 메꿔진다.
import { useState } from "react";
import { useParams } from "next/navigation";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useChatStore } from "@/store/useChatStore";

function parseSlug(slug: string[] | undefined) {
  const segments = slug ?? [];
  if (segments.length === 1 && /^\d+$/.test(segments[0])) {
    return { urlSessionId: segments[0], newFlowBotId: null as string | null };
  }
  if (segments.length === 2 && segments[0] === "new") {
    return { urlSessionId: null, newFlowBotId: segments[1] };
  }
  return { urlSessionId: null, newFlowBotId: null };
}

export function ChatLayout({ children }: { children?: React.ReactNode }) {
  const params = useParams<{ slug?: string[] }>();
  const { urlSessionId, newFlowBotId } = parseSlug(params?.slug);
  const newFlowSession = useChatStore((s) => s.newFlowSession);

  // 우선순위:
  // ① URL 이 /chat/{id} → URL 이 답
  // ② URL 이 /chat/new/{botId} AND store 가 같은 botId 의 sessionId 를 갖고 있음 → store override
  // ③ 그 외 → null (empty 상태 또는 new flow 의 Loader 단계)
  const activeSessionId: string | null =
    urlSessionId ??
    (newFlowBotId &&
    newFlowSession?.botId === newFlowBotId &&
    newFlowSession.sessionId
      ? newFlowSession.sessionId
      : null);

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
          sessionId={activeSessionId ?? undefined}
          botId={newFlowBotId ?? undefined}
        />
        {activeSessionId ? (
          <>
            <ChatArea sessionId={activeSessionId} />
            <ChatInput sessionId={activeSessionId} />
          </>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
