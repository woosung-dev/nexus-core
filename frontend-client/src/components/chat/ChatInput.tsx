import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { ArrowUp, CornerDownLeft, Loader2 } from "lucide-react";
import { useChatStream } from "@/hooks/useChatStream";
import { motion, AnimatePresence } from "framer-motion";

export function ChatInput({ sessionId, botId }: { sessionId?: string; botId?: string }) {
  const [input, setInput] = useState("");
  const { sendMessage, isStreaming } = useChatStream({ sessionId });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 메시지 전송 후 높이 초기화
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "inherit";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input, botId ? parseInt(botId, 10) : undefined);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      if (window.innerWidth > 768) { // 데스크탑에서만 엔터로 전송
        e.preventDefault();
        handleSend();
      }
    }
  };

  const isEmpty = !input.trim();

  return (
    <div className="shrink-0 bg-white/80 backdrop-blur-xl border-t border-amber-100/30 pb-8 pt-4 px-4 sm:px-6 relative z-20">
      <div className="max-w-3xl mx-auto">
        <div className={`relative flex items-end gap-2 bg-white border transition-all duration-300 rounded-[32px] p-1.5 shadow-lg shadow-amber-500/5 ${
          isEmpty ? "border-zinc-200 shadow-zinc-200/5" : "border-amber-400 ring-4 ring-amber-500/5 shadow-amber-500/10"
        }`}>
          <textarea 
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="AI에게 무엇이든 물어보세요..." 
            className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none text-[15px] text-zinc-900 placeholder:text-zinc-400 py-3 pl-4 pr-4 resize-none max-h-[200px] leading-relaxed scrollbar-hide overflow-y-auto"
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
              disabled={isEmpty || isStreaming}
              className={`w-10 h-10 shrink-0 flex items-center justify-center rounded-2xl transition-all duration-300 ${
                isStreaming
                  ? "bg-amber-50 text-amber-500 cursor-not-allowed"
                  : isEmpty
                    ? "bg-zinc-50 text-zinc-300 grayscale cursor-not-allowed"
                    : "bg-linear-to-br from-amber-400 to-amber-500 text-white shadow-lg shadow-amber-100 hover:scale-105 active:scale-95"
              }`}
            >
              {isStreaming ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <ArrowUp className="w-6 h-6 transition-transform duration-300" />
              )}
            </button>
          </div>
        </div>
        
        <p className="mt-3 text-[10px] text-center text-zinc-400 font-bold tracking-tight">
            Nexus Core는 실수를 할 수 있습니다. 중요한 정보를 확인하세요.
        </p>
      </div>
    </div>
  );
}

