"use client";

import { useMemo, useState } from "react";
import { Search, User, Bot, Sparkles, X, SquarePen } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useChat } from "@/app/(protected)/chat/ChatProvider";

import { ChatSessionListResponse } from "@/types/api";

export function ChatSidebar({ className }: { className?: string }) {
  // 현재 챗봇 컨텍스트(/chat/new/{bot} 의 urlBotId, 또는 /chat/{sid} 세션의 bot_id)가 있으면
  // 같은 봇의 새 채팅으로, 없으면 봇 픽커(홈)로 라우팅.
  const { botId, sessionId } = useChat();

  const { data } = useQuery<ChatSessionListResponse>({
    queryKey: ['chats'],
    queryFn: async () => {
      const response = await api.get('/chats');
      return response.data;
    },
  });

  const currentBotId = useMemo(() => {
    if (botId) return botId;
    if (!sessionId) return null;
    const sidNum = Number(sessionId);
    const found = data?.sessions.find((s) => s.id === sidNum);
    return found?.bot_id ? String(found.bot_id) : null;
  }, [botId, sessionId, data?.sessions]);

  const newChatHref = currentBotId ? `/chat/new/${currentBotId}` : "/";

  // 사이드바 검색 — 사용자가 화면에서 보는 'title'(첫 사용자 메시지로 저장된 값) 기준 클라이언트 필터.
  // 보조로 봇 이름도 매칭 — '축복 상담 AI' 같은 봇 이름으로도 찾을 수 있게.
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const list = data?.sessions ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((s) => {
      const title = (s.title || "").toLowerCase();
      const botName = (s.bot?.name || "").toLowerCase();
      return title.includes(q) || botName.includes(q);
    });
  }, [query, data?.sessions]);
  const isSearching = query.trim().length > 0;

  const getFullImageUrl = (path?: string | null) => {
    if (!path) return undefined;
    if (path.startsWith('http')) return path;
    const backendBase = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8080';
    return `${backendBase}${path}`;
  };

  return (
    <aside className={`bg-slate-50 flex flex-col h-full border-r border-zinc-200 w-80 shrink-0 ${className}`}>
      {/* Sidebar Header */}
      <div className="p-4 border-b border-zinc-200 shrink-0">
        <div className="flex items-center mb-4">
          <Link href="/" className="group flex items-center space-x-2">
            <Image
              src="/nexus-logo.png"
              alt="Nexus"
              width={36}
              height={36}
              priority
              className="rounded-xl"
            />
            <span className="font-bold text-lg text-zinc-900 tracking-tight group-hover:text-amber-600 transition-colors">
              Nexus
            </span>
          </Link>
        </div>

        <Link
          href={newChatHref}
          className="flex items-center gap-2 h-10 mb-3 px-3 bg-white border border-zinc-200 rounded-lg hover:border-amber-300 hover:bg-amber-50/40 hover:shadow-sm transition-all group"
        >
          <SquarePen className="w-4 h-4 text-amber-500 shrink-0" />
          <span className="text-sm font-medium text-zinc-800 group-hover:text-amber-600 transition-colors">
            새 채팅
          </span>
        </Link>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="대화 검색..."
            className="w-full h-10 bg-white border border-zinc-200 rounded-lg pl-9 pr-9 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-amber-400 shadow-sm transition-colors"
          />
          {isSearching && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="검색어 지우기"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Chat History List */}
      <ScrollArea className="flex-1 p-4">
        <h3 className="text-xs font-semibold text-zinc-500 mb-3 uppercase tracking-wider">
          {isSearching ? `검색 결과 (${filtered.length})` : "지난 대화"}
        </h3>
        {isSearching && filtered.length === 0 && (
          <p className="text-xs text-zinc-400 px-1 py-4">
            “{query}”에 해당하는 대화가 없습니다.
          </p>
        )}
        <div className="flex flex-col gap-2">
          {filtered.map((chat) => {
            const formattedDate = new Date(chat.updated_at).toLocaleDateString();
            const imageUrl = chat.bot?.image_url ? getFullImageUrl(chat.bot.image_url) : undefined;
            return (
              <Link 
                href={`/chat/${chat.id}`} 
                key={chat.id} 
                className="text-left bg-white/60 hover:bg-white p-3 rounded-xl transition-all border border-transparent hover:border-amber-200 hover:shadow-sm shadow-zinc-100 group block"
              >
                <div className="flex items-center gap-3 mb-1">
                  {/* Bot Avatar */}
                  <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 border border-zinc-100 bg-white relative overflow-hidden shadow-sm">
                    {imageUrl ? (
                      <Image 
                        src={imageUrl} 
                        alt={chat.bot?.name || "Bot"} 
                        fill 
                        unoptimized
                        className="object-cover"
                      />
                    ) : (
                      <Bot className="w-3.5 h-3.5 text-amber-500" />
                    )}
                  </div>
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="font-semibold text-sm text-zinc-800 group-hover:text-amber-600 transition-colors truncate">
                      {chat.title || "새로운 대화"}
                    </span>
                    <div className="flex items-center justify-between text-[11px] mt-0.5">
                      <span className="text-zinc-500 flex items-center gap-1.5 truncate">
                        {chat.bot ? (
                          <>
                            <span className="text-amber-500/80 truncate">{chat.bot.name}</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3 text-amber-500/50" />
                            <span>일반 AI</span>
                          </>
                        )}
                      </span>
                      <span className="text-zinc-500 shrink-0 ml-2" suppressHydrationWarning>{formattedDate}</span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </ScrollArea>

      {/* Bottom Profile Link */}
      <div className="p-4 border-t border-zinc-200 shrink-0">
        <Link href="/mypage" className="flex items-center gap-3 p-3 bg-white/60 hover:bg-white rounded-xl transition-all border border-transparent hover:border-amber-200 hover:shadow-sm shadow-zinc-100">
          {/* Default User Avatar */}
          <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 border border-zinc-100 bg-white overflow-hidden shadow-sm">
            <User className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-zinc-900">마이페이지</span>
            <span className="text-xs text-zinc-500">설정 및 정보</span>
          </div>
        </Link>
      </div>
    </aside>
  );
}
