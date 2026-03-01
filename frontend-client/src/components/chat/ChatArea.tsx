import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import { useChatStore } from "@/store/useChatStore";
import api from "@/lib/api";

import { MessageResponse } from "@/types/api";

export function ChatArea({ sessionId }: { sessionId?: string }) {
  const { isStreaming, streamingText, optimisticUserMessage } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // sessionId가 있을 때만 메시지를 가져옵니다.
  const { data: messages = [] } = useQuery<MessageResponse[]>({
    queryKey: ['messages', sessionId],
    queryFn: async () => {
      const response = await api.get(`/chats/${sessionId}/messages`);
      return response.data;
    },
    enabled: !!sessionId,
  });

  // 메시지가 추가되거나 스트리밍 중일 때 하단으로 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: "smooth"
        });
      }
    }
  }, [messages.length, streamingText, optimisticUserMessage]);

  return (
    <ScrollArea ref={scrollRef} className="flex-1 min-h-0 px-4 sm:px-8 bg-black relative">
      {/* Background Ambience */}
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-500/5 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="w-full max-w-4xl mx-auto py-8 flex flex-col gap-8 relative z-10">
        {!sessionId && messages.length === 0 && !optimisticUserMessage && !isStreaming && (
          <div className="flex-1 flex items-center justify-center min-h-[50vh]">
             <p className="text-zinc-500 animate-in fade-in duration-500">새로운 대화를 시작해보세요.</p>
          </div>
        )}

        {/* Real Messages Rendering */}
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";
          const formattedTime = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          return (
            <div key={msg.id || idx} className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
              <div className={`flex gap-4 max-w-[85%] sm:max-w-[75%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm ${
                  isUser 
                    ? "bg-linear-to-br from-amber-400 to-amber-600 ring-2 ring-amber-500/20" 
                    : "bg-zinc-900 border border-zinc-800"
                }`}>
                  {isUser ? (
                    <User className="w-4 h-4 text-black/80" />
                  ) : (
                    <Bot className="w-4 h-4 text-amber-500" />
                  )}
                </div>

                {/* Bubble Config */}
                <div className="flex flex-col gap-2 min-w-0">
                  <div className={`px-5 py-4 rounded-2xl text-[15px] leading-relaxed wrap-break-word shadow-sm ${
                    isUser 
                      ? "bg-linear-to-br from-amber-500 to-amber-600 text-black rounded-tr-sm whitespace-pre-wrap" 
                      : "bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tl-sm ring-1 ring-white/5"
                  }`}>
                    {isUser ? (
                      msg.content
                    ) : (
                      <div className="prose prose-invert prose-zinc max-w-none prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-zinc-800 prose-headings:text-zinc-100 prose-a:text-amber-500 hover:prose-a:text-amber-400">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                  <span className={`text-[11px] text-zinc-500 px-1 ${isUser ? "text-right" : "text-left"}`}>
                     {formattedTime}
                  </span>
                </div>

              </div>
            </div>
          );
        })}

        {/* Optimistic User Message */}
        {optimisticUserMessage && (
          <div className="flex w-full justify-end">
            <div className="flex gap-4 max-w-[85%] sm:max-w-[75%] flex-row-reverse">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm bg-linear-to-br from-amber-400 to-amber-600 ring-2 ring-amber-500/20">
                <User className="w-4 h-4 text-black/80" />
              </div>
              <div className="flex flex-col gap-2 min-w-0">
                <div className="px-5 py-4 rounded-2xl whitespace-pre-wrap text-[15px] leading-relaxed wrap-break-word shadow-sm bg-linear-to-br from-amber-500 to-amber-600 text-black rounded-tr-sm">
                  {optimisticUserMessage}
                </div>
                <span className="text-[11px] text-zinc-500 px-1 text-right">
                   방금 전
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Temporary Streaming Message Bubble */}
        {isStreaming && (
          <div className="flex w-full justify-start">
            <div className="flex gap-4 max-w-[85%] sm:max-w-[75%] flex-row">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm bg-zinc-900 border border-zinc-800">
                <Bot className="w-4 h-4 text-amber-500" />
              </div>
              <div className="flex flex-col gap-2 min-w-0">
                <div className={`px-5 py-4 rounded-2xl text-[15px] leading-relaxed wrap-break-word shadow-sm bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tl-sm ring-1 ring-white/5 ${!streamingText ? "whitespace-pre-wrap" : ""}`}>
                  {streamingText ? (
                    <div className="prose prose-invert prose-zinc max-w-none prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-zinc-800 prose-headings:text-zinc-100 prose-a:text-amber-500 hover:prose-a:text-amber-400">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamingText}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <span className="animate-pulse">...</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
