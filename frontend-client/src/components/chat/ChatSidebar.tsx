import { Search, PenSquare, Bolt, User, Bot, Sparkles } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

import { ChatSessionListResponse } from "@/types/api";

export function ChatSidebar({ className }: { className?: string }) {
  const { data } = useQuery<ChatSessionListResponse>({
    queryKey: ['chats'],
    queryFn: async () => {
      const response = await api.get('/chats');
      return response.data;
    },
  });

  const sessions = data?.sessions || [];

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
        <div className="flex items-center justify-between mb-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-linear-to-br from-amber-500 to-amber-600 flex items-center justify-center shrink-0">
              <Bolt className="w-4 h-4 text-black" fill="currentColor" />
            </div>
            <span className="font-bold text-lg text-zinc-900 tracking-tight">AI Chat Hub</span>
          </Link>
          <Link href="/" passHref>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-amber-600 hover:bg-amber-50 rounded-lg">
              <PenSquare className="w-4 h-4" />
            </Button>
          </Link>
        </div>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input 
            type="text" 
            placeholder="대화 검색..." 
            className="w-full h-10 bg-white border border-zinc-200 rounded-lg pl-9 pr-4 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-amber-400 shadow-sm transition-colors"
          />
        </div>
      </div>

      {/* Chat History List */}
      <ScrollArea className="flex-1 p-4">
        <h3 className="text-xs font-semibold text-zinc-500 mb-3 uppercase tracking-wider">지난 대화</h3>
        <div className="flex flex-col gap-2">
          {sessions.map((chat) => {
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
