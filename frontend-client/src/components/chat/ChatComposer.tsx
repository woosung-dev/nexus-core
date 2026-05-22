// 입력 + 전송 컴포넌트. 세션 유무는 useChat() 의 sendMessage 가 알아서 처리한다.
// (sessionId 없을 때 sendMessage 가 submit 시점에 POST /chats → history.replaceState 까지 수행.)
"use client";

import { KeyboardEvent, useEffect, useRef } from "react";
import { ArrowUp, CornerDownLeft, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useChat } from "@/app/(protected)/chat/ChatProvider";
import { useChatStore } from "@/store/useChatStore";

export function ChatComposer() {
  const { awaiting, sendMessage } = useChat();
  // 입력값은 store로 끌어올린 controlled state. FollowupPills 클릭이 store만 set하면
  // 이쪽이 자동 반영되어 입력창에 prefill 된다.
  const input = useChatStore((s) => s.composerDraft);
  const setInput = useChatStore((s) => s.setComposerDraft);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const busy = awaiting;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "inherit";
      const sh = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(sh, 200)}px`;
    }
  }, [input]);

  // store에 외부에서 값이 채워지면(=follow-up 클릭) 자동으로 textarea에 포커스.
  useEffect(() => {
    if (input && document.activeElement !== textareaRef.current) {
      textareaRef.current?.focus();
      // 커서를 텍스트 끝으로
      const len = textareaRef.current?.value.length ?? 0;
      textareaRef.current?.setSelectionRange(len, len);
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || busy) return;
    setInput("");
    void sendMessage(trimmed);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === "Enter" && !e.shiftKey && window.innerWidth > 768) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = !input.trim();

  return (
    <div className="shrink-0 bg-white/80 backdrop-blur-xl border-t border-amber-100/30 pb-6 pt-4 px-4 sm:px-6 relative z-20">
      <div className="max-w-3xl mx-auto">
        <div
          className={`relative flex items-end gap-2 bg-white border transition-all duration-300 rounded-[32px] p-1.5 shadow-lg ${
            isEmpty
              ? "border-zinc-200 shadow-zinc-200/10"
              : "border-amber-400 ring-4 ring-amber-500/5 shadow-amber-500/10"
          }`}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="AI에게 무엇이든 물어보세요..."
            disabled={busy}
            className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none text-[15px] text-zinc-900 placeholder:text-zinc-400 py-3 pl-4 pr-4 resize-none max-h-[200px] leading-relaxed scrollbar-hide overflow-y-auto disabled:opacity-60"
          />

          <div className="flex items-center gap-2 pr-1 pb-1">
            <AnimatePresence>
              {!isEmpty && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="hidden md:flex items-center gap-1.5 px-2 py-1 bg-zinc-50 rounded-lg text-[10px] text-zinc-400 border border-zinc-100"
                >
                  <CornerDownLeft className="w-3 h-3" />
                  <span>Enter</span>
                </motion.div>
              )}
            </AnimatePresence>

            <button
              onClick={handleSend}
              disabled={isEmpty || busy}
              className={`w-10 h-10 shrink-0 flex items-center justify-center rounded-2xl transition-all duration-300 ${
                busy
                  ? "bg-amber-50 text-amber-500 cursor-not-allowed"
                  : isEmpty
                    ? "bg-zinc-50 text-zinc-300 grayscale cursor-not-allowed"
                    : "bg-linear-to-br from-amber-400 to-amber-500 text-white shadow-lg shadow-amber-100 hover:scale-105 active:scale-95"
              }`}
            >
              {busy ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <ArrowUp className="w-6 h-6 transition-transform duration-300" />
              )}
            </button>
          </div>
        </div>
        <p className="mt-2 text-[10px] text-center text-zinc-400 font-bold tracking-tight">
          Nexus는 실수를 할 수 있습니다. 중요한 정보를 확인하세요.
        </p>
      </div>
    </div>
  );
}
