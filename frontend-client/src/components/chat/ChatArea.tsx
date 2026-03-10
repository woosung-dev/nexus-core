import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, User, Sparkles, Loader2, ThumbsUp, ThumbsDown, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import { useChatStore } from "@/store/useChatStore";
import api from "@/lib/api";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";

import { MessageResponse } from "@/types/api";

export function ChatArea({ sessionId }: { sessionId?: string }) {
  const { isStreaming, streamingText, optimisticUserMessage } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // 피드백 및 복사 기능 상태
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [feedbacks, setFeedbacks] = useState<Record<number, 'up' | 'down' | undefined>>({});

  const handleCopy = (id: number, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageId(id);
    setTimeout(() => setCopiedMessageId(null), 2000);
  };

  const handleFeedback = async (id: number, type: 'up' | 'down') => {
    const newFeedback = feedbacks[id] === type ? null : type;
    
    // 로컬 상태 즉시 반영 (Optimistic Update)
    setFeedbacks(prev => ({
      ...prev,
      [id]: newFeedback ?? undefined
    }));

    try {
      await api.patch(`/chats/messages/${id}`, {
        feedback: newFeedback
      });
    } catch (error) {
      console.error("Failed to update feedback:", error);
      // 에러 시 롤백 (선택 사항, 여기서는 단순 로깅)
    }
  };

  const { data: messages = [] } = useQuery<MessageResponse[]>({
    queryKey: ['messages', sessionId],
    queryFn: async () => {
      const response = await api.get(`/chats/${sessionId}/messages`);
      return response.data;
    },
    enabled: !!sessionId,
  });

  // 스크롤 위치 감지
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const bottomThreshold = 50;
    const isBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + bottomThreshold;
    setIsAtBottom(isBottom);
  };

  useEffect(() => {
    if (scrollRef.current && isAtBottom) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: "smooth"
        });
      }
    }
  }, [messages.length, streamingText, optimisticUserMessage, isAtBottom]);

  return (
    <ScrollArea 
      ref={scrollRef} 
      className="flex-1 min-h-0 bg-linear-to-b from-sky-50/50 via-white to-white relative"
      onScroll={handleScroll}
    >
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.05),transparent_70%)] pointer-events-none" />
      
      <div className="w-full max-w-3xl mx-auto py-12 px-4 sm:px-6 flex flex-col relative z-10">
        <LayoutGroup>
          {!sessionId && messages.length === 0 && !optimisticUserMessage && !isStreaming && (
            <motion.div 
              layout
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex-1 flex flex-col items-center justify-center min-h-[60vh] text-center"
            >
              <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center border border-amber-100 mb-6 shadow-xl backdrop-blur-xl">
                <Sparkles className="w-8 h-8 text-amber-500 animate-pulse" />
              </div>
              <h3 className="text-xl font-bold text-zinc-800 mb-2">무엇을 도와드릴까요?</h3>
              <p className="text-zinc-500 text-sm max-w-[280px]">식구님의 고민을 하늘의 지혜로 함께 풀어드립니다.</p>
            </motion.div>
          )}

          <div className="flex flex-col gap-10">
            <AnimatePresence mode="popLayout" initial={false}>
              {messages.map((msg, idx) => {
                const isUser = msg.role === "user";
                const formattedTime = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                return (
                  <motion.div
                    key={msg.id || `msg-${idx}`}
                    layout
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className={`flex w-full group ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`flex gap-4 max-w-[92%] sm:max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                      {/* Avatar */}
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-1 shadow-lg border transition-transform duration-300 group-hover:scale-110 ${
                        isUser 
                          ? "bg-linear-to-br from-amber-400 to-amber-500 border-amber-300 text-white" 
                          : "bg-white border-zinc-100 text-amber-500"
                      }`}>
                        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5 font-bold" />}
                      </div>

                      {/* Content Area */}
                      <div className={`flex flex-col gap-2 min-w-0 ${isUser ? "items-end" : "items-start"}`}>
                        <div className={`relative px-5 py-3.5 rounded-[20px] text-[15px] leading-relaxed shadow-sm border transition-all duration-300 ${
                          isUser 
                            ? "bg-linear-to-br from-amber-400 to-amber-500 border-amber-300 text-white rounded-tr-sm shadow-amber-200/50" 
                            : "bg-white border-zinc-100 text-zinc-800 rounded-tl-sm hover:border-amber-200"
                        }`}>
                          {isUser ? (
                            <span className="whitespace-pre-wrap font-medium">{msg.content}</span>
                          ) : (
                            <div className="flex flex-col">
                              <div className="prose prose-zinc max-w-none prose-p:leading-relaxed prose-pre:bg-zinc-50 prose-pre:border prose-pre:zinc-100 prose-code:text-amber-600 prose-headings:text-zinc-900 prose-a:text-amber-500">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                  {msg.content}
                                </ReactMarkdown>
                              </div>
                              {/* Action Bar */}
                              <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-zinc-100">
                                <button
                                  onClick={() => handleCopy(msg.id, msg.content)}
                                  className="p-1.5 text-zinc-400 hover:text-amber-500 hover:bg-amber-50 rounded-md transition-colors"
                                  title="복사하기"
                                >
                                  {copiedMessageId === msg.id ? (
                                    <Check className="w-4 h-4 text-emerald-500" />
                                  ) : (
                                    <Copy className="w-4 h-4" />
                                  )}
                                </button>
                                <div className="h-4 w-px bg-zinc-200 mx-1" />
                                <button
                                  onClick={() => handleFeedback(msg.id, 'up')}
                                  className={`p-1.5 rounded-md transition-colors ${
                                    feedbacks[msg.id] === 'up' 
                                      ? 'text-amber-500 bg-amber-50' 
                                      : 'text-zinc-400 hover:text-amber-500 hover:bg-amber-50'
                                  }`}
                                  title="좋아요"
                                >
                                  <ThumbsUp className={`w-4 h-4 ${feedbacks[msg.id] === 'up' ? 'fill-amber-500/20' : ''}`} />
                                </button>
                                <button
                                  onClick={() => handleFeedback(msg.id, 'down')}
                                  className={`p-1.5 rounded-md transition-colors ${
                                    feedbacks[msg.id] === 'down' 
                                      ? 'text-red-500 bg-red-50' 
                                      : 'text-zinc-400 hover:text-red-500 hover:bg-red-50'
                                  }`}
                                  title="싫어요"
                                >
                                  <ThumbsDown className={`w-4 h-4 ${feedbacks[msg.id] === 'down' ? 'fill-red-500/20' : ''}`} />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 px-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-tight">
                            {isUser ? "You" : "Nexus Bot"}
                          </span>
                          <span className="text-[10px] text-zinc-300">•</span>
                          <span className="text-[10px] font-medium text-zinc-400">
                             {formattedTime}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}

              {/* Optimistic User Message - 질문이 위로 올라가는 효과의 주인공 */}
              {optimisticUserMessage && (
                <motion.div
                  key="optimistic-user"
                  layout
                  initial={{ opacity: 0, y: 100, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ 
                    type: "spring",
                    stiffness: 200,
                    damping: 20
                  }}
                  className="flex w-full justify-end"
                >
                  <div className="flex gap-4 max-w-[92%] sm:max-w-[85%] flex-row-reverse">
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-1 shadow-lg bg-linear-to-br from-amber-400 to-amber-500 border border-amber-300 text-white">
                      <User className="w-5 h-5" />
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="px-5 py-3.5 rounded-[20px] bg-linear-to-br from-amber-400 to-amber-500 border border-amber-300 text-white rounded-tr-sm shadow-sm shadow-amber-200/50 whitespace-pre-wrap text-[15px] leading-relaxed font-medium">
                        {optimisticUserMessage}
                      </div>
                      <span className="text-[10px] text-zinc-400 font-bold tracking-tight uppercase px-1">Sending...</span>
                    </div>
                  </div>
                </motion.div>
              )}


              {/* Streaming/Loading Bot Presence - 질문 바로 아래에서 대기 중인 모습 */}
              {isStreaming && (
                <motion.div
                  key="bot-loading"
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="flex w-full justify-start"
                >
                  <div className="flex gap-4 max-w-[92%] sm:max-w-[85%] flex-row">
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-1 shadow-lg bg-white border border-zinc-100 text-amber-500 relative">
                      <Bot className="w-5 h-5" />
                      <div className="absolute -inset-1 bg-amber-500/5 rounded-xl animate-pulse -z-10" />
                    </div>
                    <div className="flex flex-col gap-2.5 min-w-0 w-full">
                      <div className="px-5 py-3.5 rounded-[20px] bg-white border border-zinc-100 text-zinc-800 rounded-tl-sm backdrop-blur-xl shadow-sm min-h-[58px] flex items-center">
                        {streamingText ? (
                          <div className="prose prose-zinc max-w-none prose-p:leading-relaxed prose-code:text-amber-600 prose-a:text-amber-500 w-full">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {streamingText}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="flex items-center gap-3 text-zinc-400 italic text-[14px]">
                            <Loader2 className="w-4 h-4 animate-spin text-amber-500" />
                            <span>Nexus Core가 생각 중입니다...</span>
                          </div>
                        )}
                      </div>
                      {!streamingText && (
                        <div className="flex gap-2.5 px-1 items-center">
                           <div className="h-1 w-10 bg-zinc-100 rounded-full overflow-hidden">
                              <div className="h-full bg-amber-400/60 w-1/2 animate-[shimmer_1.5s_infinite]" />
                           </div>
                           <span className="text-[10px] text-zinc-400 font-bold tracking-tight uppercase">Analyzing context</span>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </LayoutGroup>
      </div>
    </ScrollArea>
  );
}


