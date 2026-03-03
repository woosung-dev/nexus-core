"use client";

import { useState } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Sparkles } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function ChatLayout({ sessionId, botId }: { sessionId?: string; botId?: string }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex bg-slate-50 h-dvh overflow-hidden selection:bg-amber-200">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block h-full">
        <ChatSidebar />
      </div>

      {/* Mobile Sidebar (Sheet) */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="p-0 border-r border-zinc-200 w-80 bg-slate-50">
          <SheetTitle className="sr-only">채팅 메뉴</SheetTitle>
          <ChatSidebar className="w-full border-r-0" />
        </SheetContent>
      </Sheet>

      {/* Main Chat Layout */}
      <main className="flex-1 flex flex-col h-full relative z-10 w-full min-w-0">
        <ChatHeader onMenuClick={() => setSidebarOpen(true)} sessionId={sessionId} botId={botId} />
        {!sessionId && !botId ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-linear-to-b from-sky-50/50 via-white to-white relative">
            <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.05),transparent_70%)] pointer-events-none" />
            
            <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center mb-6 border border-amber-100 shadow-xl backdrop-blur-xl relative z-10">
              <Sparkles className="w-8 h-8 text-amber-500 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold text-zinc-900 mb-3 relative z-10">대화할 전문 챗봇을 선택해주세요</h2>
            <p className="text-sm text-zinc-500 max-w-sm mb-8 relative z-10">
              좌측 사이드바에서 기존 대화를 이어나가거나<br/>홈 화면에서 새로운 챗봇을 선택하여 대화를 시작해보세요.
            </p>
            <Link href="/" passHref className="relative z-10">
              <Button className="bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl px-8 h-12 shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-colors">
                챗봇 골라보기
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <ChatArea sessionId={sessionId} />
            <ChatInput sessionId={sessionId} botId={botId} />
          </>
        )}
      </main>
    </div>
  );
}
