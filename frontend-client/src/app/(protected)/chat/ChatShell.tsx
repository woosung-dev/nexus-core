// 채팅 쉘 — Provider 의 phase 에 따라 두 가지 레이아웃을 전환한다.
// (a) 빈/새 채팅: 입력칸이 수직 중앙에 배치 (Gemini 의 /app 초기 상태)
// (b) 세션 진행: 메시지 위, 입력칸은 하단
// 두 모드는 framer-motion `layoutId="chat-composer"` 로 부드럽게 모핑된다.
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";

import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useChat } from "./ChatProvider";

export function ChatShell({ children }: { children?: React.ReactNode }) {
  const { phase, sessionId, botId, statusLabel } = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // 입력칸을 중앙에 배치하는 모드 (= 메시지 0 + idle)
  const isCentered = phase === "new";
  // 메시지 영역을 노출하는 모드 (세션 진행 중 또는 첫 응답을 기다리는 중)
  const showThread =
    phase === "session" ||
    phase === "submitting" ||
    phase === "searching" ||
    phase === "streaming";

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

        {/* phase 가 empty 이면 children (catch-all 의 empty UI) 를 그대로 노출 */}
        {phase === "empty" && children}

        {/* 새 채팅: 입력칸 중앙 정렬 */}
        <AnimatePresence mode="wait">
          {isCentered && (
            <motion.div
              key="centered"
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

        {/* 세션 진행: 메시지 + 하단 입력 */}
        {showThread && (
          <>
            <div className="flex-1 min-h-0 relative">
              {sessionId ? (
                <ChatArea sessionId={sessionId} />
              ) : (
                <div className="flex-1" />
              )}
              {(phase === "submitting" || phase === "searching") && statusLabel && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 bg-white/90 backdrop-blur rounded-full border border-zinc-200 shadow-sm text-xs text-zinc-600"
                >
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500" />
                  <span className="font-medium">{statusLabel}</span>
                </motion.div>
              )}
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
