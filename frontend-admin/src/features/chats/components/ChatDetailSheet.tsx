import { useEffect, useRef } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Bot, User, Clock, ThumbsUp, ThumbsDown } from "lucide-react";
import { useChatMessages } from "../hooks";

interface ChatDetailSheetProps {
  sessionId: number | null;
  onClose: () => void;
}

export function ChatDetailSheet({ sessionId, onClose }: ChatDetailSheetProps) {
  const { data: messages, isLoading, isError } = useChatMessages(sessionId);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messages && scrollRef.current) {
      // 피드백이 있는 첫 번째 메시지 찾기
      const firstFeedbackMsg = messages.find((m) => m.feedback);
      
      if (firstFeedbackMsg) {
        // 약간의 지연 후 스크롤 (렌더링 보장)
        setTimeout(() => {
          const el = document.getElementById(`msg-${firstFeedbackMsg.id}`);
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }, 100);
      } else {
        // 피드백이 없으면 맨 하단으로 스크롤
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }
  }, [messages]);

  return (
    <Sheet open={sessionId !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-[540px] p-0 flex flex-col h-full border-l border-zinc-200 shadow-xl overflow-hidden bg-white">
        <SheetHeader className="p-4 sm:p-6 border-b border-zinc-100 flex-none space-y-1">
          <SheetTitle className="text-lg sm:text-xl font-bold text-zinc-900 tracking-tight flex items-center gap-2">
            대화 상세 기록
            {sessionId && <span className="text-xs sm:text-sm font-medium text-amber-600 bg-amber-50 px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full">#{sessionId}</span>}
          </SheetTitle>
          <SheetDescription className="text-zinc-500 text-xs sm:text-sm pl-1">
            해당 세션에서 나눈 전체 대화 내역입니다.
          </SheetDescription>
        </SheetHeader>
        
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 sm:p-6 bg-zinc-50/50 space-y-4 sm:space-y-6 scroll-smooth">
          {!sessionId ? null : isLoading ? (
            <div className="space-y-6">
              <div className="flex w-full gap-3 justify-end">
                <div className="flex flex-col gap-1.5 items-end">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-12 w-48 rounded-2xl rounded-tr-sm" />
                </div>
                <Skeleton className="w-8 h-8 rounded-full shrink-0" />
              </div>
              <div className="flex w-full gap-3 justify-start">
                <Skeleton className="w-8 h-8 rounded-full shrink-0" />
                <div className="flex flex-col gap-1.5 items-start">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-16 w-64 rounded-2xl rounded-tl-sm" />
                  <Skeleton className="h-12 w-56 rounded-2xl rounded-tl-sm mt-1" />
                </div>
              </div>
            </div>
          ) : isError ? (
            <div className="text-center text-red-500 mt-10">
              데이터를 불러오는 데 실패했습니다.
            </div>
          ) : messages?.length === 0 ? (
            <div className="text-center text-zinc-500 mt-10">
              대화 내역이 없습니다.
            </div>
          ) : (
            messages?.map((msg) => {
              const isUser = msg.role === "user";
              const isSystem = msg.role === "system";

              if (isSystem) {
                return (
                  <div key={msg.id} className="flex justify-center my-4">
                    <span className="bg-zinc-100 text-zinc-500 text-xs px-3 py-1.5 rounded-full border border-zinc-200">
                      시스템: {msg.content}
                    </span>
                  </div>
                );
              }

              return (
                <div id={`msg-${msg.id}`} key={msg.id} className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center shrink-0 border border-amber-200">
                      <Bot className="w-4 h-4 text-amber-600" />
                    </div>
                  )}

                  <div className={`flex flex-col gap-1.5 max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
                    <div className="flex items-baseline gap-2 px-1">
                      <span className="text-sm font-medium text-zinc-700">
                        {isUser ? "사용자" : "챗봇"}
                      </span>
                      <span className="text-[11px] text-zinc-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <div className="flex items-end gap-2">
                      <div
                        className={`px-4 py-2.5 rounded-2xl text-[15px] leading-relaxed wrap-break-word whitespace-pre-wrap ${
                          isUser
                            ? "bg-zinc-900 text-white rounded-tr-sm shadow-md"
                            : "bg-white border border-zinc-200 text-zinc-800 shadow-sm rounded-tl-sm"
                        } ${msg.feedback ? "ring-2 ring-offset-1 " + (msg.feedback === "up" ? "ring-blue-400" : "ring-red-400") : ""}`}
                      >
                        {msg.content}
                      </div>
                      
                      {msg.feedback && (
                        <div 
                          className={`flex items-center justify-center shrink-0 w-7 h-7 rounded-full border shadow-sm ${
                            msg.feedback === "up" 
                              ? "bg-blue-50 border-blue-200 text-blue-600" 
                              : "bg-red-50 border-red-200 text-red-600"
                          }`}
                        >
                          {msg.feedback === "up" ? <ThumbsUp className="w-3.5 h-3.5 fill-blue-600/20" /> : <ThumbsDown className="w-3.5 h-3.5 fill-red-600/20" />}
                        </div>
                      )}
                    </div>
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center shrink-0 border border-zinc-200 shadow-sm">
                      <User className="w-4 h-4 text-zinc-600" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
