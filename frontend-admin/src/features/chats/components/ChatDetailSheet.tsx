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
import { MessageCitations } from "./MessageCitations";
import { MessageFollowups } from "./MessageFollowups";

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
      <SheetContent className="w-full sm:max-w-[540px] p-0 flex flex-col h-full overflow-hidden">
        <SheetHeader className="p-4 sm:p-6 border-b flex-none space-y-1">
          <SheetTitle className="text-lg font-semibold tracking-tight flex items-center gap-2">
            대화 상세 기록
            {sessionId && <span className="rounded-full border px-2 py-0.5 text-xs font-medium tabular-nums">#{sessionId}</span>}
          </SheetTitle>
          <SheetDescription className="pl-1 text-sm text-muted-foreground">
            해당 세션에서 나눈 전체 대화 내역입니다.
          </SheetDescription>
        </SheetHeader>
        
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 sm:p-6 bg-muted/30 space-y-4 sm:space-y-6 scroll-smooth">
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
            <div role="alert" className="mt-10 text-center text-sm text-destructive">
              데이터를 불러오는 데 실패했습니다.
            </div>
          ) : messages?.length === 0 ? (
            <div className="mt-10 text-center text-sm text-muted-foreground">
              대화 내역이 없습니다.
            </div>
          ) : (
            messages?.map((msg) => {
              const isUser = msg.role === "user";
              const isSystem = msg.role === "system";

              if (isSystem) {
                return (
                  <div key={msg.id} className="flex justify-center my-4">
                    <span className="rounded-full border bg-muted px-3 py-1.5 text-xs text-muted-foreground">
                      시스템: {msg.content}
                    </span>
                  </div>
                );
              }

              return (
                <div id={`msg-${msg.id}`} key={msg.id} className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-muted">
                      <Bot className="size-4 text-muted-foreground" aria-hidden />
                    </div>
                  )}

                  <div className={`flex flex-col gap-1.5 max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
                    <div className="flex items-baseline gap-2 px-1">
                      <span className="text-sm font-medium">
                        {isUser ? "사용자" : "챗봇"}
                      </span>
                      <span className="flex items-center gap-1 text-2xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <div className="flex items-end gap-2">
                      <div
                        className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed wrap-break-word whitespace-pre-wrap ${
                          isUser
                            ? "bg-primary text-primary-foreground rounded-tr-sm"
                            : "bg-card border rounded-tl-sm"
                        } ${msg.feedback ? "ring-2 ring-offset-1 " + (msg.feedback === "up" ? "ring-primary/40" : "ring-destructive/50") : ""}`}
                      >
                        {msg.content}
                      </div>
                      
                      {msg.feedback && (
                        <div 
                          className={`flex items-center justify-center shrink-0 w-7 h-7 rounded-full border shadow-sm ${
                            msg.feedback === "up" 
                              ? "bg-muted" 
                              : "bg-destructive/10 border-destructive/30 text-destructive"
                          }`}
                        >
                          {msg.feedback === "up" ? <ThumbsUp className="size-3.5" aria-hidden /> : <ThumbsDown className="size-3.5" aria-hidden />}
                        </div>
                      )}
                    </div>

                    {!isUser && (
                      <>
                        <MessageCitations citations={msg.citations} />
                        <MessageFollowups items={msg.followups} />
                        {(!msg.citations || msg.citations.length === 0) &&
                          (!msg.followups || msg.followups.length === 0) && (
                            <p className="mt-1 pl-1 text-2xs text-muted-foreground">인용 기록 없음</p>
                          )}
                      </>
                    )}
                  </div>

                  {isUser && (
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-muted">
                      <User className="size-4 text-muted-foreground" aria-hidden />
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
