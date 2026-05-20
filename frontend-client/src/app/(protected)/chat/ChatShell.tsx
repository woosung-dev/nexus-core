// 채팅 쉘 — Provider 의 phase 에 따라 두 가지 레이아웃을 전환한다.
// composer: 입력칸이 수직 중앙 (Gemini /app 초기 상태)
// thread:   메시지 영역 + 하단 입력칸 (= 사용자가 submit 한 순간부터 응답 도착까지 동일)
// empty:    children (catch-all 이 제공하는 안내 UI) 표시
// 두 모드의 composer 는 framer-motion `layoutId="chat-composer"` 로 부드럽게 모핑된다.
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

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

        {phase === "empty" && children}

        <AnimatePresence mode="wait">
          {phase === "composer" && (
            <motion.div
              key="composer"
              className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <motion.h1
                className="text-2xl sm:text-3xl font-medium text-zinc-700 mb-8 text-center"
                initial={{ y: 8, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.3, delay: 0.1 }}
              >
                무엇이든 편하게 물어보세요
              </motion.h1>
              <motion.div
                layoutId="chat-composer"
                className="w-full max-w-3xl"
                transition={{ type: "spring", stiffness: 240, damping: 30 }}
              >
                <ChatComposer />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {phase === "thread" && (
          <>
            <div className="flex-1 min-h-0">
              <ChatArea sessionId={sessionId ?? undefined} />
            </div>
            <motion.div
              layoutId="chat-composer"
              transition={{ type: "spring", stiffness: 240, damping: 30 }}
            >
              <ChatComposer />
            </motion.div>
          </>
        )}
      </main>
    </div>
  );
}
