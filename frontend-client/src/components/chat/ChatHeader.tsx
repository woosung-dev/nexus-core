import { Menu, MoreVertical, Bot, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import { ChatSessionListResponse, BotListResponse } from "@/types/api";
import api from "@/lib/api";

interface ChatHeaderProps {
  onMenuClick?: () => void;
  sessionId?: string;
  botId?: string;
}

export function ChatHeader({ onMenuClick, sessionId, botId }: ChatHeaderProps) {
  // Try to find bot info from active session
  const { data: chatData } = useQuery<ChatSessionListResponse>({
    queryKey: ['chats'],
    queryFn: async () => {
      const response = await api.get('/chats');
      return response.data;
    },
  });
  const activeSession = chatData?.sessions.find((s) => s.id.toString() === sessionId);
  
  // Try to find bot info from bots cache if it's a new chat (no active session yet)
  const { data: botList } = useQuery<BotListResponse>({
    queryKey: ['bots'],
    queryFn: async () => {
      const response = await api.get('/bots');
      return response.data;
    },
  });
  
  let currentBot = activeSession?.bot;
  if (!currentBot && botId) {
    currentBot = botList?.bots?.find((b) => b.id.toString() === botId);
  }

  const getFullImageUrl = (path?: string | null) => {
    if (!path) return undefined;
    if (path.startsWith('http')) return path;
    const backendBase = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8080';
    return `${backendBase}${path}`;
  };

  const displayName = currentBot?.name || "일반 AI";
  const displayCategory = (currentBot?.tags?.[0]) || "범용";
  const imageUrl = getFullImageUrl(currentBot?.image_url);

  return (
    <header className="h-[76px] shrink-0 border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 sticky top-0 z-20">
      <div className="flex items-center gap-4">
        {/* Mobile Menu Trigger */}
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={onMenuClick}
          className="lg:hidden text-zinc-400 hover:text-white hover:bg-zinc-800 -ml-2"
        >
          <Menu className="w-5 h-5" />
        </Button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0 overflow-hidden relative">
            {imageUrl ? (
              <Image 
                src={imageUrl} 
                alt={displayName} 
                fill 
                unoptimized
                className="object-cover"
              />
            ) : (
              <>
                <div className="absolute inset-0 bg-amber-500/10" />
                {currentBot ? <Bot className="w-5 h-5 text-amber-500 relative z-10" /> : <Sparkles className="w-5 h-5 text-amber-500 relative z-10" />}
              </>
            )}
          </div>
          <div className="flex flex-col">
            <h2 className="text-base font-bold text-white leading-tight">{displayName}</h2>
            <span className="text-xs text-zinc-400">{displayCategory}</span>
          </div>
        </div>
      </div>

      <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-full">
        <MoreVertical className="w-5 h-5" />
      </Button>
    </header>
  );
}
