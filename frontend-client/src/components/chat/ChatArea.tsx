import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Sparkles, Loader2, ThumbsUp, ThumbsDown, Copy, Check, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import { useChatStore } from "@/store/useChatStore";
import api from "@/lib/api";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";

import { FeedbackType, MessageResponse } from "@/types/api";
import { FeedbackReasonForm } from "./FeedbackReasonForm";

type FeedbackState = {
  type: FeedbackType | null;
  reasons: string[];
  comment: string;
};

export function ChatArea({ sessionId }: { sessionId?: string }) {
  const { isStreaming, streamingText } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  // ChatGPT/Claude 스타일 스크롤 — 사용자 메시지를 viewport 최상단으로 보내고, 응답이 그 아래로 들어오게 한다.
  const prevIsStreamingRef = useRef(false);
  const initializedSessionRef = useRef<string | null>(null);

  const getViewport = () =>
    scrollRef.current?.querySelector<HTMLElement>('[data-radix-scroll-area-viewport]') ?? null;

  // 피드백 및 복사 기능 상태
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<number, FeedbackState>>({});
  // 사유 모달이 어떤 type 으로 열려있는지 (null = 닫힘)
  const [openModalFor, setOpenModalFor] = useState<Record<number, FeedbackType | null>>({});

  const handleCopy = (id: number, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageId(id);
    setTimeout(() => setCopiedMessageId(null), 2000);
  };

  const patchFeedback = async (
    id: number,
    type: FeedbackType | null,
    reasons: string[],
    comment: string,
  ) => {
    try {
      await api.patch(`/chats/messages/${id}`, {
        feedback: type,
        feedback_reasons: type ? reasons : [],
        feedback_comment: type ? (comment || null) : null,
      });
    } catch (error) {
      console.error("Failed to update feedback:", error);
    }
  };

  // 👍/👎 버튼 클릭. 모달 토글 + 활성 피드백 클리어 두 가지 의미를 동시에 처리.
  const handleFeedbackButton = (id: number, type: FeedbackType) => {
    const currentOpen = openModalFor[id] ?? null;
    const savedType = feedbackMap[id]?.type ?? null;

    if (currentOpen) {
      // 모달이 열려있는 상태에서 같은 버튼 → 취소(닫기), 다른 버튼 → 다른 타입으로 모달 전환
      setOpenModalFor((prev) => ({ ...prev, [id]: currentOpen === type ? null : type }));
      return;
    }

    if (savedType === type) {
      // 활성 상태 버튼 다시 누름 → 클리어 (단일 PATCH)
      setFeedbackMap((prev) => ({ ...prev, [id]: { type: null, reasons: [], comment: "" } }));
      void patchFeedback(id, null, [], "");
      return;
    }

    // 비활성 상태에서 새로 누름 → 모달 열기 (PATCH 는 저장/건너뛰기 시 1회)
    setOpenModalFor((prev) => ({ ...prev, [id]: type }));
  };

  // 모달의 저장/건너뛰기에서 호출 — 단일 PATCH 로 feedback + reasons + comment 한 번에 커밋
  const handleReasonSubmit = (id: number, reasons: string[], comment: string) => {
    const type = openModalFor[id];
    if (!type) return;

    setFeedbackMap((prev) => ({ ...prev, [id]: { type, reasons, comment } }));
    setOpenModalFor((prev) => ({ ...prev, [id]: null }));

    void patchFeedback(id, type, reasons, comment);
  };

  const { data: messages = [] } = useQuery<MessageResponse[]>({
    queryKey: ['messages', sessionId],
    queryFn: async () => {
      const response = await api.get(`/chats/${sessionId}/messages`);
      return response.data;
    },
    enabled: !!sessionId,
  });

  // 서버에서 받은 기존 피드백 상태를 로컬 맵으로 하이드레이션 (기존 사용자가 다시 열었을 때 기록 보존)
  useEffect(() => {
    if (messages.length === 0) return;
    setFeedbackMap((prev) => {
      const next = { ...prev };
      messages.forEach((msg) => {
        if (next[msg.id]) return; // 이미 로컬에 있는 건 건드리지 않음 (사용자 토글 보존)
        if (msg.feedback === "up" || msg.feedback === "down") {
          next[msg.id] = {
            type: msg.feedback,
            reasons: msg.feedback_reasons ?? [],
            comment: msg.feedback_comment ?? "",
          };
        }
      });
      return next;
    });
  }, [messages]);

  // 스크롤 위치 감지
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const bottomThreshold = 50;
    const isBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + bottomThreshold;
    setIsAtBottom(isBottom);
  };

  // 1) 기존 세션 첫 진입 시 즉시 최하단으로 점프 (대화 히스토리 끝부분 노출)
  useEffect(() => {
    if (!sessionId || messages.length === 0) return;
    if (initializedSessionRef.current === sessionId) return;
    const sc = getViewport();
    if (!sc) return;
    sc.scrollTop = sc.scrollHeight;
    initializedSessionRef.current = sessionId;
  }, [sessionId, messages.length]);

  // 2) 사용자 전송 순간(isStreaming false → true) 마지막 user 메시지를 viewport 최상단으로 스크롤
  useEffect(() => {
    const wasStreaming = prevIsStreamingRef.current;
    prevIsStreamingRef.current = isStreaming;
    if (wasStreaming || !isStreaming) return;

    const sc = getViewport();
    if (!sc) return;
    // motion.div 의 initial 상태가 layout 에 반영된 다음 프레임에 스크롤
    requestAnimationFrame(() => {
      const userBubbles = sc.querySelectorAll<HTMLElement>('[data-msg-role="user"]');
      const lastUser = userBubbles[userBubbles.length - 1];
      if (!lastUser) return;
      const containerRect = sc.getBoundingClientRect();
      const bubbleRect = lastUser.getBoundingClientRect();
      const targetTop = sc.scrollTop + (bubbleRect.top - containerRect.top) - 16; // 상단 패딩 16px
      sc.scrollTo({ top: targetTop, behavior: "smooth" });
      // 스트리밍 단계에서 자동 follow 가 작동하도록 anchor 갱신
      setIsAtBottom(true);
    });
  }, [isStreaming]);

  // 3) 스트리밍 중 텍스트가 늘어나면 따라 내려가기 (사용자가 위로 스크롤하면 멈춤)
  useEffect(() => {
    if (!isStreaming || !isAtBottom) return;
    const sc = getViewport();
    if (!sc) return;
    sc.scrollTo({ top: sc.scrollHeight, behavior: "smooth" });
  }, [streamingText, isStreaming, isAtBottom]);

  return (
    <ScrollArea 
      ref={scrollRef} 
      className="flex-1 min-h-0 bg-linear-to-b from-sky-50/50 via-white to-white relative"
      onScroll={handleScroll}
    >
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.05),transparent_70%)] pointer-events-none" />
      
      <div className="w-full max-w-3xl mx-auto py-12 px-4 sm:px-6 flex flex-col relative z-10">
        <LayoutGroup>
          {!sessionId && messages.length === 0 && !isStreaming && (
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
                    data-msg-role={msg.role}
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
                              {(() => {
                                const fb = feedbackMap[msg.id];
                                const openType = openModalFor[msg.id] ?? null;
                                // 활성 표시: 저장된 피드백 OR 모달이 그 타입으로 열려있을 때
                                const isUp = fb?.type === "up" || openType === "up";
                                const isDown = fb?.type === "down" || openType === "down";
                                return (
                                  <>
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
                                        onClick={() => handleFeedbackButton(msg.id, 'up')}
                                        className={`p-1.5 rounded-md transition-colors ${
                                          isUp
                                            ? 'text-amber-500 bg-amber-50'
                                            : 'text-zinc-400 hover:text-amber-500 hover:bg-amber-50'
                                        }`}
                                        title="좋아요"
                                      >
                                        <ThumbsUp className={`w-4 h-4 ${isUp ? 'fill-amber-500/20' : ''}`} />
                                      </button>
                                      <button
                                        onClick={() => handleFeedbackButton(msg.id, 'down')}
                                        className={`p-1.5 rounded-md transition-colors ${
                                          isDown
                                            ? 'text-red-500 bg-red-50'
                                            : 'text-zinc-400 hover:text-red-500 hover:bg-red-50'
                                        }`}
                                        title="싫어요"
                                      >
                                        <ThumbsDown className={`w-4 h-4 ${isDown ? 'fill-red-500/20' : ''}`} />
                                      </button>
                                    </div>
                                    <AnimatePresence>
                                      {openType && (
                                        <FeedbackReasonForm
                                          key={`form-${msg.id}-${openType}`}
                                          type={openType}
                                          onSubmit={(reasons, comment) =>
                                            handleReasonSubmit(msg.id, reasons, comment)
                                          }
                                        />
                                      )}
                                    </AnimatePresence>
                                  </>
                                );
                              })()}
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
          {/* 짧은 대화에서도 사용자 메시지를 viewport 최상단까지 스크롤할 수 있도록 viewport 만큼의 여유 공간 확보. */}
          {messages.length > 0 && <div aria-hidden className="shrink-0 h-[60dvh]" />}
        </LayoutGroup>
      </div>
    </ScrollArea>
  );
}


